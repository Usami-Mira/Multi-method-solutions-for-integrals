# Read the file
with open("D:/PHY-LLM/MMSI/src/calc_solver/tools/latex_parser.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find the parse_latex function and replace it
new_func = """def parse_latex(latex: str) -> sp.Expr | None:
    # Strip +C / -C (integration constant) before parsing
    latex = re.sub(r"\\s*[+\\-]\\s*C\\b", "", latex, flags=re.IGNORECASE).strip()
    # Normalize common LaTeX patterns for better SymPy compatibility
    # Convert \\sqrt{...} to sqrt(...)
    latex = re.sub(r"\\\\sqrt\\s*\\{([^}]+)\\}", r"sqrt(\\1)", latex)
    # Ensure \\frac{a}{b} followed by (expr) has explicit multiplication
    latex = re.sub(r"(\\\\frac\\s*\\{[^}]+\\}\\s*\\{[^}]+\\})\\s*(\\()", r"\\1*\\2", latex)
    # Remove \\left( \\right) wrappers
    latex = re.sub(r"\\\\left\\(", "(", latex)
    latex = re.sub(r"\\\\right\\)", ")", latex)
    # Normalize \\sin, \\cos, etc. function names
    for func in ["sin", "cos", "tan", "sec", "csc", "cot", "log", "ln", "exp"]:
        latex = re.sub(rf"\\\\{func}\\s*\\(?", f"{func}(", latex)
    
    # Try SymPy native LaTeX parser first
    try:
        from sympy.parsing.latex import parse_latex as sympy_parse
        return sympy_parse(latex)
    except Exception:
        pass
    
    # Fallback: simple string conversion + sympify
    try:
        sympy_str = _simple_latex_to_sympy_str(latex)
        if sympy_str:
            return sp.sympify(sympy_str, evaluate=True)
    except Exception:
        pass
    
    # Last resort: direct sympify
    try:
        return sp.sympify(latex, evaluate=True)
    except Exception:
        return None

"""

# Find start and end of parse_latex function
start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if line.strip().startswith("def parse_latex("):
        start_idx = i
    elif start_idx is not None and line.strip().startswith("def ") and "parse_latex" not in line:
        end_idx = i
        break

if start_idx is not None and end_idx is not None:
    # Replace the function
    new_lines = lines[:start_idx] + [new_func] + lines[end_idx:]
    with open("D:/PHY-LLM/MMSI/src/calc_solver/tools/latex_parser.py", "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print(f"Replaced parse_latex function (lines {start_idx+1}-{end_idx})")
else:
    print(f"Could not find function boundaries: start={start_idx}, end={end_idx}")
