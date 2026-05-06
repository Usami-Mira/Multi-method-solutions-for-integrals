with open("D:/PHY-LLM/MMSI/src/calc_solver/tools/latex_parser.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix _simple_latex_to_sympy_str to preserve math function names
# Change: s = re.sub(r"\\[a-zA-Z]+", "", s)
# To: preserve sin, cos, tan, sqrt, log, etc.

old_strip = "s = re.sub(r'\\\\[a-zA-Z]+', '', s)"
new_strip = """# Remove LaTeX commands but preserve math function names
    math_funcs = ['sin', 'cos', 'tan', 'sec', 'csc', 'cot', 'log', 'ln', 'exp', 'sqrt', 'abs', 'floor', 'ceil']
    for func in math_funcs:
        s = s.replace(r'\\\\' + func, func)
    s = re.sub(r'\\\\[a-zA-Z]+', '', s)  # Remove any remaining LaTeX commands"""

content = content.replace(old_strip, new_strip)

with open("D:/PHY-LLM/MMSI/src/calc_solver/tools/latex_parser.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed _simple_latex_to_sympy_str to preserve math functions")
