from __future__ import annotations

import asyncio
from typing import Optional

from calc_solver.agents.builder import BuilderAgent
from calc_solver.agents.evaluator import EvaluatorAgent
from calc_solver.agents.planner import PlannerAgent
from calc_solver.schema import EvalResult, Problem, Solution, Strategy
from calc_solver.utils.logger import RunLogger


def _failed_solution(strategy: Strategy, exc: Exception) -> Solution:
    return Solution(
        strategy_id=strategy.strategy_id,
        final_answer="",
        error=str(exc),
        self_check_passed=False,
    )


class Pipeline:
    def __init__(
        self,
        planner: PlannerAgent,
        builder: BuilderAgent,
        evaluator: EvaluatorAgent,
        K: int = 3,
        max_outer_loops: int = 2,
        problem_concurrency: int = 4,
        builder_concurrency_per_problem: int = 3,
        enable_replan_on_fail: bool = True,
        logger: Optional[RunLogger] = None,
    ):
        self.planner = planner
        self.builder = builder
        self.evaluator = evaluator
        self.K = K
        self.max_outer_loops = max_outer_loops
        self.problem_sem = asyncio.Semaphore(problem_concurrency)
        self.builder_sem = asyncio.Semaphore(problem_concurrency * builder_concurrency_per_problem)
        self.enable_replan_on_fail = enable_replan_on_fail
        self.logger = logger

    async def solve_one(self, problem: Problem) -> EvalResult:
        """
        Outer loop: Planner → K Builders (parallel) → Evaluator.
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

        return result

    async def run_batch(
        self,
        problems: list[Problem],
        resume_ids: Optional[set[str]] = None,
    ) -> list[EvalResult]:
        resume_ids = resume_ids or set()
        results: list[EvalResult] = []

        async def _wrap(p: Problem) -> EvalResult:
            if p.problem_id in resume_ids:
                if self.logger:
                    self.logger.info("skip_resume", problem_id=p.problem_id)
                return EvalResult(
                    problem_id=p.problem_id,
                    is_correct=False,
                    confidence=0.0,
                    method_agreement=0,
                    notes="skipped_resume",
                )
            async with self.problem_sem:
                try:
                    return await self.solve_one(p)
                except Exception as e:
                    if self.logger:
                        self.logger.error("solve_one_failed",
                                          problem_id=p.problem_id, error=str(e))
                    return EvalResult(
                        problem_id=p.problem_id,
                        is_correct=False,
                        confidence=0.0,
                        method_agreement=0,
                        notes=f"pipeline_error: {e}",
                    )

        try:
            from tqdm.asyncio import tqdm_asyncio
            results = await tqdm_asyncio.gather(*[_wrap(p) for p in problems], desc="Solving")
        except ImportError:
            results = list(await asyncio.gather(*[_wrap(p) for p in problems]))

        return results
