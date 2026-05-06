from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal, Optional

import numpy as np
import sympy as sp
from pydantic import BaseModel

from calc_solver.tools.latex_parser import best_parse

if TYPE_CHECKING:
    from calc_solver.llm.client import QwenClient


class VerifyResult(BaseModel):
    is_eq: bool
    level_used: Literal["L1", "L2", "L3", "L4", "L5", "fail"]
    confidence: float
    evidence: str


SIMPLIFIERS = [
    sp.simplify,
    lambda e: sp.trigsimp(e, method="fu"),
    sp.expand_trig,
    lambda e: sp.expand_log(e, force=True),
    sp.radsimp,
    sp.together,
    sp.cancel,
    sp.factor,
    sp.powsimp,
    lambda e: sp.logcombine(e, force=True),
    lambda e: sp.simplify(sp.expand(e)),
    lambda e: sp.nsimplify(e, rational=True),
]


def _try_zero(diff_expr: sp.Expr) -> bool:
    if diff_expr == 0:
        return True
    for f in SIMPLIFIERS:
        try:
            r = f(diff_expr)
            if r == 0 or (hasattr(r, "is_zero") and r.is_zero is True):
                return True
        except Exception:
            continue
    return False


class Verifier:
    def __init__(
        self,
        llm_client: Optional["QwenClient"] = None,
        n_samples: int = 30,
        llm_for_unsure: bool = True,
        logger: Optional["RunLogger"] = None,
    ):
        self.llm_client = llm_client
        self.n_samples = n_samples
        self.llm_for_unsure = llm_for_unsure
        self.logger = logger

    def is_equivalent(
        self,
        pred: str,
        gold: str,
        *,
        var: str = "x",
        answer_type: str = "expression",
        question: str = "",
    ) -> VerifyResult:
        # L1: string normalisation
        if self._l1(pred, gold):
            return VerifyResult(is_eq=True, level_used="L1", confidence=1.0, evidence="string_equal")

        pred_expr = best_parse(pred, var)
        gold_expr = best_parse(gold, var)

        if pred_expr is None or gold_expr is None:
            if self.logger:
                self.logger.info("verifier_parse_failed", pred=pred[:100], gold=gold[:100], var=var)
            if self.llm_client and self.llm_for_unsure:
                return self._l5(pred, gold, var, answer_type, question, 0, 0)
            return VerifyResult(is_eq=False, level_used="fail", confidence=0.0, evidence="parse_failed")

        # L2: symbolic simplification
        l2 = self._l2(pred_expr, gold_expr, answer_type)
        if l2 is not None:
            if self.logger:
                self.logger.info("verifier_L2", is_eq=l2, pred_expr=str(pred_expr)[:80], gold_expr=str(gold_expr)[:80])
            return VerifyResult(is_eq=l2, level_used="L2", confidence=0.95,
                                evidence="symbolic_simplify")

        # L3: type-specific
        l3 = self._l3(pred_expr, gold_expr, pred, gold, var, answer_type)
        if l3 is not None:
            if self.logger:
                self.logger.info("verifier_L3", is_eq=l3, answer_type=answer_type)
            return VerifyResult(is_eq=l3, level_used="L3", confidence=0.95,
                                evidence="type_specific")

        # L4: numerical sampling
        l4_result, pass_count, total_count = self._l4(pred_expr, gold_expr, var, answer_type)
        if l4_result is True:
            if self.logger:
                self.logger.info("verifier_L4", is_eq=True, pass_count=pass_count, total_count=total_count)
            return VerifyResult(is_eq=True, level_used="L4", confidence=0.9,
                                evidence=f"numerical_{pass_count}/{total_count}")
        if l4_result is False:
            if self.logger:
                self.logger.info("verifier_L4", is_eq=False, pass_count=pass_count, total_count=total_count)
            return VerifyResult(is_eq=False, level_used="L4", confidence=0.9,
                                evidence=f"numerical_{pass_count}/{total_count}")

        # L4 inconclusive -> maybe L5
        if self.llm_client and self.llm_for_unsure and pass_count >= total_count * 0.5:
            return self._l5(pred, gold, var, answer_type, question, pass_count, total_count)

        return VerifyResult(is_eq=False, level_used="L4", confidence=0.5,
                            evidence=f"inconclusive_{pass_count}/{total_count}")

    def _l1(self, pred: str, gold: str) -> bool:
        def norm(s: str) -> str:
            s = s.strip().replace(" ", "")
            s = s.rstrip(".;:,!?")  # Remove trailing punctuation
            s = s.replace(r"\dfrac", r"\frac").replace(r"\tfrac", r"\frac")
            s = re.sub(r"[\(\)\{\}]", lambda m: {"(": "[", ")": "]", "{": "[", "}": "]"}[m.group()], s)
            return s
        return norm(pred) == norm(gold)

    def _l2(self, pred: sp.Expr, gold: sp.Expr, answer_type: str) -> bool | None:
        """Returns True if proven equal, None if uncertain. Never returns False."""
        try:
            diff = pred - gold
            if _try_zero(diff):
                return True
        except Exception:
            pass
        return None

    def _l3(self, pred: sp.Expr, gold: sp.Expr, pred_str: str, gold_str: str,
             var: str, answer_type: str) -> bool | None:
        x = sp.Symbol(var)
        try:
            if answer_type == "expression":
                # For indefinite integrals: compare derivatives
                dp = sp.diff(pred, x)
                dg = sp.diff(gold, x)
                if _try_zero(dp - dg):
                    return True
            elif answer_type == "value":
                try:
                    pv = float(pred.evalf())
                    gv = float(gold.evalf())
                    return abs(pv - gv) < 1e-7
                except Exception:
                    pass
        except Exception:
            pass
        return None

    def _l4(self, pred: sp.Expr, gold: sp.Expr, var: str, answer_type: str,
            n_samples: Optional[int] = None) -> tuple[bool | None, int, int]:
        """Numerical sampling. Returns (result, pass_count, total_count)."""
        n = n_samples or self.n_samples
        x = sp.Symbol(var)
        pass_count = 0
        total_count = 0

        # Sample points avoiding singularities
        test_points = list(np.linspace(-10, 10, n)) + [0.1, 0.5, 1.5, 3.14, -2.71]
        for pt in test_points:
            try:
                pv = float(pred.subs(x, pt).evalf())
                gv = float(gold.subs(x, pt).evalf())
                total_count += 1
                if np.isfinite(pv) and np.isfinite(gv) and abs(pv - gv) < 1e-6:
                    pass_count += 1
            except Exception:
                continue

        if total_count == 0:
            return None, 0, 0
        if pass_count == total_count:
            return True, pass_count, total_count
        if pass_count == 0:
            return False, pass_count, total_count
        return None, pass_count, total_count  # Inconclusive

    def _l5(self, pred: str, gold: str, var: str, answer_type: str,
            question: str, pass_count: int, total_count: int) -> VerifyResult:
        """LLM arbitration for edge cases."""
        if not self.llm_client:
            return VerifyResult(is_eq=False, level_used="fail", confidence=0.0, evidence="no_llm_client")
        try:
            from calc_solver.llm.prompts import get, format_prompt
            try:
                system = get("equivalence_judge", "system")
            except (KeyError, TypeError):
                system = ""
            user = format_prompt(
                "equivalence_judge", "user_template",
                question=question,
                answer_type=answer_type,
                pred=pred,
                gold=gold,
                pass_rate=pass_count,
                total=total_count,
            )
            raw = self.llm_client.chat(
                [{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.0, json_mode=True, max_retries=1, agent_name="verifier"
            )
            import json
            # Robust JSON parsing for LLM response
            try:
                data = json.loads(raw)
                if not isinstance(data, dict):
                    # Try to extract dict from nested structure
                    if isinstance(data, list) and len(data) > 0:
                        data = data[0] if isinstance(data[0], dict) else {}
                    else:
                        data = {}
            except (json.JSONDecodeError, TypeError):
                data = {}
            # Safe key access with fallback
            is_eq = data.get("equivalent", data.get("is_eq", data.get("equal", False)))
            reason = str(data.get("reason", data.get("explanation", "")))[:100]
            if self.logger:
                self.logger.info("verifier_L5_success", is_eq=is_eq, reason=reason)
            return VerifyResult(is_eq=is_eq, level_used="L5", confidence=0.6, evidence=f"llm_judge: {reason}")
        except Exception as e:
            if self.logger:
                self.logger.info("verifier_L5_error", raw_response=(raw if 'raw' in locals() else None)[:200] if 'raw' in locals() else None, error=str(e))
            return VerifyResult(is_eq=False, level_used="fail", confidence=0.0, evidence=f"L5_error: {type(e).__name__}: {str(e)[:50]}")





