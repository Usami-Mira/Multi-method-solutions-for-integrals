import sys

with open("src/calc_solver/orchestrator/pipeline.py", "r", encoding="utf-8", newline="") as f:
    lines = f.readlines()

# Add config param to __init__
for i, line in enumerate(lines):
    if "builder_concurrency_per_problem: int = 3," in line:
        lines.insert(i+1, "        max_retries_per_strategy: int = 2,\n")
        break

# Add instance variable
for i, line in enumerate(lines):
    if "self.builder_sem = asyncio.Semaphore(problem_concurrency * builder_concurrency_per_problem)" in line:
        lines.insert(i+1, "        self.max_retries_per_strategy = max_retries_per_strategy\n")
        break

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
    print("ERROR")
    sys.exit(1)

# New solve_one method
new_method = [
    "    async def solve_one(self, problem: Problem) -> EvalResult:\n",
    '        """Strategy-level retry: each strategy has independent Builder+Evaluator loop."""\n',
    "        all_solutions: list[Solution] = []\n",
    "        failed_strategies: list[Strategy] = []\n",
    "        result: Optional[EvalResult] = None\n",
    "\n",
    "        for loop_idx in range(self.max_outer_loops):\n",
    "            try:\n",
    "                strategies = await self.planner.plan(problem, K=self.K,\n",
    "                    failed_strategies=failed_strategies if loop_idx > 0 else None)\n",
    "            except Exception as e:\n",
    "                if self.logger:\n",
    "                    self.logger.error(\"planner_failed\", problem_id=problem.problem_id, error=str(e))\n",
    "                break\n",
    "            if not strategies:\n",
    "                break\n",
    "\n",
    "            async def _solve_strategy(strategy: Strategy) -> Optional[Solution]:\n",
    '                """Run one strategy with its own retry loop and evaluator."""\n',
    "                for retry in range(self.max_retries_per_strategy):\n",
    "                    async with self.builder_sem:\n",
    "                        try:\n",
    "                            sol = await self.builder.build(problem, strategy)\n",
    "                        except Exception as exc:\n",
    "                            if self.logger:\n",
    "                                self.logger.warning(\"strategy_build_failed\", strategy_id=strategy.strategy_id, retry=retry+1, error=str(exc))\n",
    "                            continue\n",
    "                    if await self.evaluator.evaluate_single(problem, sol):\n",
    "                        if self.logger:\n",
    "                            self.logger.info(\"strategy_passed\", strategy_id=strategy.strategy_id, retry=retry+1)\n",
    "                        return sol\n",
    "                    if self.logger:\n",
    "                        self.logger.debug(\"strategy_failed_retry\", strategy_id=strategy.strategy_id, retry=retry+1)\n",
    "                if self.logger:\n",
    "                    self.logger.warning(\"strategy_exhausted\", strategy_id=strategy.strategy_id)\n",
    "                return None\n",
    "\n",
    "            successful = await asyncio.gather(*[_solve_strategy(s) for s in strategies])\n",
    "            successful = [s for s in successful if s is not None]\n",
    "\n",
    "            if successful:\n",
    "                best = min(successful, key=lambda s: (not s.self_check_passed, len(s.steps)))\n",
    "                result = EvalResult(problem_id=problem.problem_id, chosen_strategy_id=best.strategy_id,\n",
    "                    final_answer=best.final_answer, is_correct=True, confidence=0.9,\n",
    "                    method_agreement=len(successful), candidates=[best])\n",
    "                result.loop_count = loop_idx + 1\n",
    "                break\n",
    "\n",
    "            if self.enable_replan_on_fail:\n",
    "                failed_strategies.extend(strategies)\n",
    "                all_solutions.extend([_failed_solution(s, Exception(\"eval_failed\")) for s in strategies])\n",
    "\n",
    "        if result is None:\n",
    "            result = EvalResult(problem_id=problem.problem_id, is_correct=False, confidence=0.0,\n",
    "                method_agreement=0, candidates=all_solutions, notes=\"pipeline: all strategies exhausted\")\n",
    "\n",
    "        if self.logger:\n",
    "            self.logger.log_pipeline(result.model_dump())\n",
    "            self.logger.log_trace(problem.problem_id, {\"problem\": problem.model_dump(), \"result\": result.model_dump()})\n",
    "        return result\n",
    "\n",
]

lines = lines[:start] + new_method + lines[end:]

with open("src/calc_solver/orchestrator/pipeline.py", "w", encoding="utf-8", newline="") as f:
    f.writelines(lines)

print("Done")
