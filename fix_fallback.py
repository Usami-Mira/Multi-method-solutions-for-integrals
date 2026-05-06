with open("D:/PHY-LLM/MMSI/src/calc_solver/tools/latex_parser.py", "r", encoding="utf-8") as f:
    content = f.read()

# Since SymPy native parser needs antlr4 (not installed), enhance the fallback path
# Add implicit multiplication fix after preprocessing

old_preprocess = """    # Normalize \\\\sin, \\\\cos, etc. function names
    for func in ["sin", "cos", "tan", "sec", "csc", "cot", "log", "ln", "exp"]:
        latex = re.sub(rf"\\\\{func}\\s*\\(?", f"{func}(", latex)"""

new_preprocess = """    # Normalize \\\\sin, \\\\cos, etc. function names
    for func in ["sin", "cos", "tan", "sec", "csc", "cot", "log", "ln", "exp"]:
        latex = re.sub(rf"\\\\{func}\\s*\\(?", f"{func}(", latex)
    # Fix implicit multiplication: )func( -> )*func(, )var -> )*var
    latex = re.sub(r"\\)\\s*([a-zA-Z])", r")*\\1", latex)"""

content = content.replace(old_preprocess, new_preprocess)

# Also update the parse_latex function to skip antlr4-dependent native parser
# and go straight to fallback since antlr4 isn't available
old_try_native = """    # Try SymPy native LaTeX parser first
    try:
        from sympy.parsing.latex import parse_latex as sympy_parse
        return sympy_parse(latex)
    except Exception:
        pass"""

new_try_native = """    # SymPy native parser requires antlr4; skip if not available
    # Fallback to simple string conversion + sympify (more reliable for our use case)"""

content = content.replace(old_try_native, new_try_native)

with open("D:/PHY-LLM/MMSI/src/calc_solver/tools/latex_parser.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Enhanced fallback parsing")
