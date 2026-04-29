import re

with open("src/calc_solver/orchestrator/pipeline.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add max_retries_per_strategy parameter to __init__
old_init = "builder_concurrency_per_problem: int = 3,"
new_init = "builder_concurrency_per_problem: int = 3,\n        max_retries_per_strategy: int = 2,"
content = content.replace(old_init, new_init)

# 2. Add instance variable assignment
old_assign = "self.builder_sem = asyncio.Semaphore(problem_concurrency * builder_concurrency_per_problem)"
new_assign = "self.builder_sem = asyncio.Semaphore(problem_concurrency * builder_concurrency_per_problem)\n        self.max_retries_per_strategy = max_retries_per_strategy"
content = content.replace(old_assign, new_assign)

# 3. Replace the solve_one method body
# Find the solve_one method and replace its implementation
old_solve_one = """    async def solve_one(self, problem: Problem) -> EvalResult:
        """
        Outer loop: Planner -> K Builders (parallel) -> Evaluator.
        If Evaluator returns is_correct=False, replan and retry up to max_outer_loops times.
        """
        all_solutions: list[Solution] = []
        failed_strategies: list[Strategy] = []
        result: Optional[EvalResult] = None

        for loop_idx in range(self.max_outer_loops):
            # Plan
            try:
                strategies = await self.planner.plan(
                    problem,
                    K=self.K,
                    failed_strategies=failed_strategies if loop_idx > 0 else None,
                )
            except Exception as e:
                if self.logger:
                    self.logger.error("planner_failed", problem_id=problem.problem_id, error=str(e))
                break

            if not strategies:
                break

            # Build (parallel)
            async def _build(s: Strategy) -> Solution:
                async with self.builder_sem:
                    try:
                        return await self.builder.build(problem, s)
                    except Exception as exc:
                        return _failed_solution(s, exc)

            new_solutions = await asyncio.gather(*[_build(s) for s in strategies])
            all_solutions.extend(new_solutions)

            # Evaluate
            result = await self.evaluator.evaluate(problem, list(all_solutions))
            result.loop_count = loop_idx + 1

            if self.logger:
                self.logger.info(
                    "eval_loop",
                    problem_id=problem.problem_id,
                    loop=loop_idx + 1,
                    is_correct=result.is_correct,
                )

            if result.is_correct:
                break

            # Not correct: collect failed strategies for replan hint
            if self.enable_replan_on_fail:
                failed_strategies.extend(strategies)

        if result is None:
            result = EvalResult(
                problem_id=problem.problem_id,
                is_correct=False,
                confidence=0.0,
                method_agreement=0,
                candidates=all_solutions,
                notes="pipeline: no result produced",
            )

        if self.logger:
            self.logger.log_pipeline(result.model_dump())
            self.logger.log_trace(problem.problem_id, {
                "problem": problem.model_dump(),
                "result": result.model_dump(),
            })

        return result"""

new_solve_one = """    async def solve_one(self, problem: Problem) -> EvalResult:
        """
        Outer loop: Planner -> [Strategy-level: Builder + Evaluator with retry] -> Select best.
        Each strategy has independent retry loop. If any succeeds, return early.
        If all fail, replan up to max_outer_loops times.
        """
        all_solutions: list[Solution] = []
        failed_strategies: list[Strategy] = []
        result: Optional[EvalResult] = None

        for loop_idx in range(self.max_outer_loops):
            # Plan
            try:
                strategies = await self.planner.plan(
                    problem,
                    K=self.K,
                    failed_strategies=failed_strategies if loop_idx > 0 else None,
                )
            except Exception as e:
                if self.logger:
                    self.logger.error("planner_failed", problem_id=problem.problem_id, error=str(e))
                break

            if not strategies:
                break

            # Strategy-level parallel execution with independent retry
            async def _solve_strategy(strategy: Strategy) -> Optional[Solution]:
                """Run one strategy with its own retry loop and evaluator."""
                for retry in range(self.max_retries_per_strategy):
                    async with self.builder_sem:
                        try:
                            sol = await self.builder.build(problem, strategy)
                        except Exception as exc:
                            if self.logger:
                                self.logger.warning(
                                    "strategy_build_failed",
                                    strategy_id=strategy.strategy_id,
                                    retry=retry + 1,
                                    error=str(exc),
                                )
                            continue
                    # Evaluate this single candidate
                    if await self.evaluator.evaluate_single(problem, sol):
                        if self.logger:
                            self.logger.info(
                                "strategy_passed",
                                strategy_id=strategy.strategy_id,
                                retry=retry + 1,
                            )
                        return sol
                    if self.logger:
                        self.logger.debug(
                            "strategy_failed_retry",
                            strategy_id=strategy.strategy_id,
                            retry=retry + 1,
                        )
                # All retries exhausted for this strategy
                if self.logger:
                    self.logger.warning(
                        "strategy_exhausted",
                        strategy_id=strategy.strategy_id,
                    )
                return None

            # Run all strategies in parallel
            successful = await asyncio.gather(*[_solve_strategy(s) for s in strategies])
            successful = [s for s in successful if s is not None]

            if successful:
                # Pick best from successful candidates
                best = min(
                    successful,
                    key=lambda s: (not s.self_check_passed, len(s.steps)),
                )
                result = EvalResult(
                    problem_id=problem.problem_id,
                    chosen_strategy_id=best.strategy_id,
                    final_answer=best.final_answer,
                    is_correct=True,
                    confidence=0.9,
                    method_agreement=len(successful),
                    candidates=[best],
                )
                result.loop_count = loop_idx + 1
                break

            # All strategies failed: collect for replan
            if self.enable_replan_on_fail:
                failed_strategies.extend(strategies)
                all_solutions.extend(
                    [_failed_solution(s, Exception("eval_failed")) for s in strategies]
                )

        if result is None:
            result = EvalResult(
                problem_id=problem.problem_id,
                is_correct=False,
                confidence=0.0,
                method_agreement=0,
                candidates=all_solutions,
                notes="pipeline: all strategies exhausted",
            )

        if self.logger:
            self.logger.log_pipeline(result.model_dump())
            self.logger.log_trace(problem.problem_id, {
                "problem": problem.model_dump(),
                "result": result.model_dump(),
            })

        return result"""

content = content.replace(old_solve_one, new_solve_one)

with open("src/calc_solver/orchestrator/pipeline.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Pipeline refactored")
