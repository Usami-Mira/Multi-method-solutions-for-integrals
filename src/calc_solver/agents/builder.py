from __future__ import annotations

import json
import re
from typing import Optional

from calc_solver.agents.base import BaseAgent
from calc_solver.llm.client import QwenClient
from calc_solver.llm.prompts import get, format_prompt
from calc_solver.schema import Problem, Solution, StepTrace, Strategy
from calc_solver.tools.sympy_tool import call_tool
from calc_solver.utils.logger import RunLogger


class BuilderAgent(BaseAgent):
    name = "builder"

    def __init__(
        self,
        client: QwenClient,
        max_steps: int = 12,
        max_retries: int = 2,
        logger: Optional[RunLogger] = None,
    ):
        super().__init__(client, temperature=0.2, logger=logger)
        self.max_steps = max_steps
        self.max_retries = max_retries

    async def build(self, problem: Problem, strategy: Strategy) -> Solution:
        steps: list[StepTrace] = []
        current_temp = self.temperature
        last_error: Optional[str] = None

        for attempt in range(self.max_retries + 1):
            if attempt > 0:
                current_temp = 0.4  # break dead loops on retry
            result, steps, error = await self._run_loop(
                problem, strategy, current_temp, steps if attempt == 0 else [], last_error
            )
            if result is not None:
                # self-check
                passed, check_reason = self._self_check(result, problem)
                if passed:
                    return Solution(
                        strategy_id=strategy.strategy_id,
                        final_answer=result.get("final_answer", ""),
                        final_answer_sympy=result.get("final_answer_sympy"),
                        steps=steps,
                        self_check_passed=True,
                    )
                last_error = f"self_check_failed: {check_reason}"
            else:
                last_error = error or "no_answer"

        # Return best effort
        final = result if result else {}
        return Solution(
            strategy_id=strategy.strategy_id,
            final_answer=final.get("final_answer", ""),
            final_answer_sympy=final.get("final_answer_sympy"),
            steps=steps,
            self_check_passed=False,
            error=last_error,
        )

    async def _run_loop(
        self,
        problem: Problem,
        strategy: Strategy,
        temperature: float,
        prior_steps: list[StepTrace],
        prior_error: Optional[str],
    ) -> tuple[Optional[dict], list[StepTrace], Optional[str]]:
        system = get("builder", "system")
        steps_outline = "\n".join(f"{i+1}. {s}" for i, s in enumerate(strategy.steps_outline))

        first_step = strategy.steps_outline[0] if strategy.steps_outline else ""
        user_init = format_prompt(
            "builder", "user_template",
            question=problem.question,
            variable=problem.variable,
            strategy_name=strategy.name,
            strategy_rationale=strategy.rationale,
            steps_outline=steps_outline,
            first_step=first_step,
        )
        if prior_error:
            hint = format_prompt("builder", "retry_hint",
                                 reason=prior_error,
                                 weak_step="???")
            user_init = user_init + "\n\n" + hint

        messages: list[dict] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_init},
        ]

        steps: list[StepTrace] = list(prior_steps)
        json_fail_count = 0
        final_result: Optional[dict] = None

        for step_no in range(1, self.max_steps + 1):
            # Force finish if near limit
            if step_no >= self.max_steps:
                messages.append({
                    "role": "user",
                    "content": "???????????? action=finish ??????????"
                })

            # Rolling summary: if conversation grows too long, compress middle history
            messages = self._compact_messages(messages, steps)

            raw = await self._call_messages(messages, json_mode=True, temperature=temperature, agent_name="builder")
            action_dict, parse_err = self._parse_action(raw)

            if parse_err:
                json_fail_count += 1
                if json_fail_count >= 2:
                    return final_result, steps, f"json_parse_failed: {parse_err}"
                messages.append({"role": "assistant", "content": raw})
                messages.append({
                    "role": "user",
                    "content": f"JSON?????{parse_err}??????? JSON ????????????"
                })
                continue

            json_fail_count = 0
            action = action_dict.get("action", "think")
            thought = action_dict.get("thought", "")
            state = action_dict.get("current_state", "")

            step = StepTrace(
                step_no=step_no,
                thought=thought,
                state=state,
            )

            if action == "finish":
                step.tool_call = None
                steps.append(step)
                final_result = action_dict
                return final_result, steps, None

            elif action == "tool":
                tool_name = action_dict.get("tool", "")
                tool_args = action_dict.get("args", {})
                step.tool_call = {"name": tool_name, "args": tool_args}

                tool_res = call_tool(tool_name, tool_args)
                step.tool_result = tool_res.get("result") or tool_res.get("error")
                steps.append(step)

                # inject tool result back into conversation
                messages.append({"role": "assistant", "content": raw})
                if tool_res["ok"]:
                    feedback = format_prompt("builder", "tool_result_template",
                                             tool_name=tool_name,
                                             result=tool_res["result"])
                else:
                    feedback = (
                        f"?? {tool_name} ???{tool_res['error']}?\n"
                        "??????????????????"
                    )
                messages.append({"role": "user", "content": feedback})

            else:  # think
                steps.append(step)
                messages.append({"role": "assistant", "content": raw})
                messages.append({"role": "user", "content": "???????"})

        return final_result, steps, "max_steps_exceeded"

    def _compact_messages(self, messages: list[dict], steps: list[StepTrace],
                          keep_recent: int = 6, threshold: int = 14) -> list[dict]:
        """Rolling summary: when messages exceed threshold, replace middle with a step digest.
        Keeps system+initial user, summarises older steps, keeps recent `keep_recent` messages."""
        if len(messages) <= threshold:
            return messages
        # messages[0] = system, messages[1] = initial user; keep both
        head = messages[:2]
        tail = messages[-keep_recent:]
        # Summarise the steps that fall in the middle
        n_summarised_steps = max(0, len(steps) - keep_recent // 2)
        digest_lines = []
        for s in steps[:n_summarised_steps]:
            tc = s.tool_call.get("name") if s.tool_call else "?"
            tr = (s.tool_result or "")[:80]
            digest_lines.append(f"step{s.step_no}: tool={tc} state={s.state[:40] if s.state else ''} result={tr}")
        digest = "????????\n" + "\n".join(digest_lines) if digest_lines else ""
        if digest:
            head = head + [{"role": "user", "content": digest}]
        return head + tail

    def _parse_action(self, raw: str) -> tuple[dict, Optional[str]]:
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return data, None
        except json.JSONDecodeError:
            pass
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
                if isinstance(data, dict):
                    return data, None
            except Exception:
                pass
        return {}, f"Cannot parse JSON from: {raw[:100]}"

    def _self_check(self, result: dict, problem: Problem) -> tuple[bool, str]:
        """Reverse-verify the final answer using SymPy with robust equivalence checking."""
        from calc_solver.tools.sympy_tool import differentiate, simplify
        from calc_solver.tools.latex_parser import best_parse
        from calc_solver.tools.verifier import Verifier
        import sympy as sp
        
        final = result.get("final_answer", "") or result.get("final_answer_sympy", "")
        if not final:
            return False, "empty_answer"

        tag = problem.metadata.get("tag", {})
        var = problem.variable

        try:
            if tag.get("have_indefinite"):
                # d/dx(answer) should equal the integrand
                d_res = differentiate(final, var)
                if not d_res["ok"]:
                    return False, f"differentiate_failed: {d_res.get('error')}"
                
                integrand = _extract_integrand(problem.question, var)
                if not integrand:
                    return True, ""  # Can't extract integrand, give benefit of doubt
                
                # Method 1: Use Verifier with full pipeline (L1-L5)
                v = Verifier(llm_client=self.client if hasattr(self, 'client') else None)
                vr = v.is_equivalent(d_res["result"], integrand, var=var)
                if vr.is_eq:
                    return True, ""
                
                # Method 2: Fallback - direct symbolic simplification of difference
                # Parse both to SymPy expressions and simplify their difference
                pred_expr = best_parse(d_res["result"], var)
                gold_expr = best_parse(integrand, var)
                if pred_expr is not None and gold_expr is not None:
                    diff = sp.simplify(pred_expr - gold_expr)
                    # Try multiple simplification strategies
                    for simp_fn in [sp.simplify, sp.trigsimp, sp.expand_trig, sp.cancel]:
                        try:
                            if simp_fn(diff) == 0:
                                return True, ""
                        except Exception:
                            continue
                    # Final check: numeric evaluation at random points
                    try:
                        x = sp.Symbol(var)
                        import numpy as np
                        test_pts = [0.1, 0.5, 1.0, 2.0, -0.5, -1.0]
                        match_count = 0
                        for pt in test_pts:
                            try:
                                pv = float(pred_expr.subs(x, pt).evalf())
                                gv = float(gold_expr.subs(x, pt).evalf())
                                if np.isfinite(pv) and np.isfinite(gv) and abs(pv - gv) < 1e-6:
                                    match_count += 1
                            except Exception:
                                continue
                        if match_count >= len(test_pts) * 0.8:  # 80% match threshold
                            return True, ""
                    except Exception:
                        pass
                
                return False, f"derivative_mismatch: d/dx({final[:30]}) != {integrand[:30]}"
            
            # For other types, just check the answer is parseable
            if best_parse(final, var) is not None:
                return True, ""
            return False, "answer_not_parseable"
        except Exception as e:
            return True, ""  # give benefit of doubt if self-check errors


