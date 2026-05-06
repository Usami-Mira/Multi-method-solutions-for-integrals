import re

with open("D:/PHY-LLM/MMSI/src/calc_solver/tools/latex_parser.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace the entire parse_latex function to use SymPy native parser
old_function = """def parse_latex(latex: str) -> sp.Expr | None:
    # Strip +C / -C (integration constant) before parsing
    latex = re.sub(r"\\s*[+\\-]\\s*C\\b", "", latex, flags=re.IGNORECASE).strip()
    # Normalize common LaTeX patterns for better latex2sympy2 compatibility
    # Convert \\sqrt{...} to sqrt(...) for simpler parsing
    latex = re.sub(r"\\\\sqrt\\s*\\{([^}]+)\\}", r"sqrt(\\1)", latex)
    # Ensure \\frac{a}{b} followed by (expr) has explicit multiplication: \\frac{a}{b}(x) -> \\frac{a}{b}*(x)
    latex = re.sub(r"(\\\\frac\\s*\\{[^}]+\\}\\s*\\{[^}]+\\})\\s*(\\()", r"\\1*\\2", latex)
    # Remove \\left( \\right) wrappers which can confuse parsers
    latex = re.sub(r"\\\\left\\(", "(", latex)
    latex = re.sub(r"\\\\right\\)", ")", latex)
    try:
        from latex2sympy2 import latex2sympy
        result = latex2sympy(latex)
        if result is not None:
            return result
    except Exception:
        pass
    try:
        sympy_str = _simple_latex_to_sympy_str(latex)
        if sympy_str:
            return sp.sympify(sympy_str, evaluate=True)
    except Exception:
        pass
    try:
        return sp.sympify(latex, evaluate=True)
    except Exception:
        return None"""

new_function = """def parse_latex(latex: str) -> sp.Expr | None:
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
    # Normalize \sin, \cos, \tan, \sec, \csc, \cot function names
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
        return None"""

content = content.replace(old_function, new_function)

with open("D:/PHY-LLM/MMSI/src/calc_solver/tools/latex_parser.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Switched to SymPy native parse_latex")
