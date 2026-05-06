with open("D:/PHY-LLM/MMSI/src/calc_solver/tools/latex_parser.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find and replace the parse_latex function with a cleaner version
new_func = """def parse_latex(latex: str) -> sp.Expr | None:
    # Strip +C / -C (integration constant) before parsing
    latex = re.sub(r"\\s*[+\\-]\\s*C\\b", "", latex, flags=re.IGNORECASE).strip()
    # Remove \\left( \\right) wrappers
    latex = re.sub(r"\\\\left\\(", "(", latex)
    latex = re.sub(r"\\\\right\\)", ")", latex)
    # Normalize \\sqrt{...} to sqrt(...) for simpler parsing
    latex = re.sub(r"\\\\sqrt\\s*\\{([^}]+)\\}", r"sqrt(\\1)", latex)
    
    # Convert to sympy string using existing helper
    try:
        sympy_str = _simple_latex_to_sympy_str(latex)
        if sympy_str:
            # Fix implicit multiplication: )x -> )*x, )sin -> )*sin, etc.
            sympy_str = re.sub(r"\\)\\s*([a-zA-Z])", r")*\\1", sympy_str)
            return sp.sympify(sympy_str, evaluate=True)
    except Exception:
        pass
    
    # Last resort: direct sympify of preprocessed input
    try:
        return sp.sympify(latex, evaluate=True)
    except Exception:
        return None

"""

# Find function boundaries
start_idx = end_idx = None
for i, line in enumerate(lines):
    if line.strip().startswith("def parse_latex("):
        start_idx = i
    elif start_idx is not None and line.strip().startswith("def ") and "parse_latex" not in line:
        end_idx = i
        break

if start_idx is not None and end_idx is not None:
    new_lines = lines[:start_idx] + [new_func] + lines[end_idx:]
    with open("D:/PHY-LLM/MMSI/src/calc_solver/tools/latex_parser.py", "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print(f"Simplified parse_latex (lines {start_idx+1}-{end_idx})")
else:
    print("Could not find function boundaries")
