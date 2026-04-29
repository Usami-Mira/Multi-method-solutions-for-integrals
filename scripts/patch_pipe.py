with open("src/calc_solver/orchestrator/pipeline.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "builder_concurrency_per_problem: int = 3," in line:
        lines.insert(i+1, "        max_retries_per_strategy: int = 2,\n")
        break

for i, line in enumerate(lines):
    if "self.builder_sem = asyncio.Semaphore(problem_concurrency * builder_concurrency_per_problem)" in line:
        lines.insert(i+1, "        self.max_retries_per_strategy = max_retries_per_strategy\n")
        break

with open("src/calc_solver/orchestrator/pipeline.py", "w", encoding="utf-8") as f:
    f.writelines(lines)

print("Done")