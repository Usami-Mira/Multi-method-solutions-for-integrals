with open("src/calc_solver/agents/evaluator.py", "r", encoding="utf-8") as f: lines = f.readlines()
insert_idx = None
for i, line in enumerate(lines):
    if "async def evaluate(self, problem: Problem, solutions: list[Solution])" in line:
        insert_idx = i
        break
if insert_idx is None:
    print("ERROR")
    exit(1)
new = ["    async def evaluate_single(self, problem: Problem, solution: Solution) -> bool:\n", "        \"\"\"Single candidate check: returns True if passed\"\"\"\n", "        pred = solution.final_answer or solution.final_answer_sympy or \"\"\n", "        vr = self.verifier.is_equivalent(\n", "            pred, problem.gold_answer,\n", "            var=problem.variable,\n", "            answer_type=problem.answer_type,\n", "            question=problem.question\n", "        )\n", "        return vr.is_eq\n", "\n"]
lines = lines[:insert_idx] + new + lines[insert_idx:]
with open("src/calc_solver/agents/evaluator.py", "w", encoding="utf-8") as f: f.writelines(lines)
print("OK")