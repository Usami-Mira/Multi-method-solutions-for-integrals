import sys

content = open("src/calc_solver/agents/evaluator.py", "r", encoding="utf-8").read()

insert_pos = content.find("    async def evaluate(self, problem: Problem, solutions: list[Solution]) -> EvalResult:")
if insert_pos == -1:
    print("ERROR: Could not find evaluate method")
    sys.exit(1)

new_method = '''    async def evaluate_single(self, problem: Problem, solution: Solution) -> bool:
        """单候选校验：返回是否通过"""
        pred = solution.final_answer or solution.final_answer_sympy or ""
        vr = self.verifier.is_equivalent(
            pred, problem.gold_answer,
            var=problem.variable,
            answer_type=problem.answer_type,
            question=problem.question
        )
        return vr.is_eq

'''

new_content = content[:insert_pos] + new_method + content[insert_pos:]
with open("src/calc_solver/agents/evaluator.py", "w", encoding="utf-8") as f:
    f.write(new_content)
print("Successfully added evaluate_single method to evaluator.py")
