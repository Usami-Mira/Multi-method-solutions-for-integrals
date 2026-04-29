import sys

# Read pipeline.py
with open("src/calc_solver/orchestrator/pipeline.py", "r", encoding="utf-8", newline="") as f:
    lines = f.readlines()

# Find solve_one boundaries
start = end = None
for i, line in enumerate(lines):
    if "async def solve_one(self, problem: Problem)" in line:
        start = i
    if start is not None and i > start:
        stripped = line.lstrip()
        if stripped and not stripped.startswith("#"):
            indent = len(line) - len(stripped)
            if indent <= 4 and (stripped.startswith("async def ") or stripped.startswith("def ") or stripped.startswith("class ")):
                end = i
                break

if start is None or end is None:
    print("ERROR: Could not find solve_one method")
    sys.exit(1)

print(f"Found solve_one: lines {start+1} to {end}")

# New method content
new_method = """    async def solve_one(self, problem: Problem) -> EvalResult:
        \"\"\"
        Outer loop: Planner -> [Strategy-level: Builder + Evaluator with retry] -> Select best.
        Each strategy has independent retry loop. If any succeeds, return early.
        If all fail, replan up to max_outer_loops times.
        \"\"\"
        all_solutions: list[Solution] = []
        failed_strategies: list[Strategy] = []
        result: Optional[EvalResult] = None

        for loop_idx in range(self.max_outer_loops):
            try:
                strategies = await self.planner.plan(
                    problem, K=self.K,
                    failed_strategies=failed_strategies if loop_idx > 0 else None,
                )
            except Exception as e:
                if self.logger:
                    self.logger.error("planner_failed", problem_id=problem.problem_id, error=str(e))
                break
            if not strategies:
                break

            async def _solve_strategy(strategy: Strategy) -> Optional[Solution]:
                \"\"\"Run one strategy with its own retry loop and evaluator.\"\"\"
                for retry in range(self.max_retries_per_strategy):
                    async with self.builder_sem:
                        try:
                            sol = await self.builder.build(problem, strategy)
                        except Exception as exc:
                            if self.logger:
                                self.logger.warning("strategy_build_failed", strategy_id=strategy.strategy_id, retry=retry+1, error=str(exc))
                            continue
                    if await self.evaluator.evaluate_single(problem, sol):
                        if self.logger:
                            self.logger.info("strategy_passed", strategy_id=strategy.strategy_id, retry=retry+1)
                        return sol
                    if self.logger:
                        self.logger.debug("strategy_failed_retry", strategy_id=strategy.strategy_id, retry=retry+1)
                if self.logger:
                    self.logger.warning("strategy_exhausted", strategy_id=strategy.strategy_id)
                return None

            successful = await asyncio.gather(*[_solve_strategy(s) for s in strategies])
            successful = [s for s in successful if s is not None]

            if successful:
                best = min(successful, key=lambda s: (not s.self_check_passed, len(s.steps)))
                result = EvalResult(
                    problem_id=problem.problem_id, chosen_strategy_id=best.strategy_id,
                    final_answer=best.final_answer, is_correct=True, confidence=0.9,
                    method_agreement=len(successful), candidates=[best],
                )
                result.loop_count = loop_idx + 1
                break

            if self.enable_replan_on_fail:
                failed_strategies.extend(strategies)
                all_solutions.extend([_failed_solution(s, Exception("eval_failed")) for s in strategies])

        if result is None:
            result = EvalResult(
                problem_id=problem.problem_id, is_correct=False, confidence=0.0,
                method_agreement=0, candidates=all_solutions, notes="pipeline: all strategies exhausted",
            )

        if self.logger:
            self.logger.log_pipeline(result.model_dump())
            self.logger.log_trace(problem.problem_id, {"problem": problem.model_dump(), "result": result.model_dump()})
        return result

"""

# Replace
new_lines = lines[:start] + [new_method] + lines[end:]

with open("src/calc_solver/orchestrator/pipeline.py", "w", encoding="utf-8", newline="") as f:
    f.writelines(new_lines)

print("Refactored solve_one successfully")