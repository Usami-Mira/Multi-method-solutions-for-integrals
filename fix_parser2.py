import re

with open("D:/PHY-LLM/MMSI/src/calc_solver/tools/latex_parser.py", "r", encoding="utf-8") as f:
    content = f.read()

# Also strip +C in parse_latex before latex2sympy2 tries to parse
old_parse_latex = """def parse_latex(latex: str) -> sp.Expr | None:
    try:
        from latex2sympy2 import latex2sympy
        result = latex2sympy(latex)"""

new_parse_latex = """def parse_latex(latex: str) -> sp.Expr | None:
    # Strip +C / -C before any parsing attempt
    latex = re.sub(r"\\s*[+\\-]\\s*C\\b", "", latex, flags=re.IGNORECASE).strip()
    try:
        from latex2sympy2 import latex2sympy
        result = latex2sympy(latex)"""

content = content.replace(old_parse_latex, new_parse_latex)

with open("D:/PHY-LLM/MMSI/src/calc_solver/tools/latex_parser.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Added +C stripping to parse_latex")
