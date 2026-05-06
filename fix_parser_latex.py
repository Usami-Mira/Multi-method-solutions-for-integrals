with open("D:/PHY-LLM/MMSI/src/calc_solver/tools/latex_parser.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add more LaTeX preprocessing before latex2sympy2
old_func = """def parse_latex(latex: str) -> sp.Expr | None:
    # Strip +C / -C before any parsing attempt
    latex = re.sub(r"\\s*[+\\-]\\s*C\\b", "", latex, flags=re.IGNORECASE).strip()
    try:
        from latex2sympy2 import latex2sympy
        result = latex2sympy(latex)"""

new_func = """def parse_latex(latex: str) -> sp.Expr | None:
    # Strip +C / -C (integration constant) before parsing
    latex = re.sub(r"\\s*[+\\-]\\s*C\\b", "", latex, flags=re.IGNORECASE).strip()
    # Normalize common LaTeX patterns for better latex2sympy2 compatibility
    # Convert \sqrt{...} to sqrt(...) for simpler parsing
    latex = re.sub(r"\\\\sqrt\\s*\\{([^}]+)\\}", r"sqrt(\\1)", latex)
    # Ensure \frac{a}{b} followed by (expr) has explicit multiplication: \frac{a}{b}(x) -> \frac{a}{b}*(x)
    latex = re.sub(r"(\\\\frac\\s*\\{[^}]+\\}\\s*\\{[^}]+\\})\\s*(\\()", r"\\1*\\2", latex)
    # Remove \left( \right) wrappers which can confuse parsers
    latex = re.sub(r"\\\\left\\(", "(", latex)
    latex = re.sub(r"\\\\right\\)", ")", latex)
    try:
        from latex2sympy2 import latex2sympy
        result = latex2sympy(latex)"""

content = content.replace(old_func, new_func)

with open("D:/PHY-LLM/MMSI/src/calc_solver/tools/latex_parser.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Enhanced latex_parser.py preprocessing")
