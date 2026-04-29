with open("src/calc_solver/orchestrator/pipeline.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    "builder_concurrency_per_problem: int = 3,",
    "builder_concurrency_per_problem: int = 3," + chr(10) + "        max_retries_per_strategy: int = 2,"
)
content = content.replace(
    "self.builder_sem = asyncio.Semaphore(problem_concurrency * builder_concurrency_per_problem)",
    "self.builder_sem = asyncio.Semaphore(problem_concurrency * builder_concurrency_per_problem)" + chr(10) + "        self.max_retries_per_strategy = max_retries_per_strategy"
)

with open("src/calc_solver/orchestrator/pipeline.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Done")