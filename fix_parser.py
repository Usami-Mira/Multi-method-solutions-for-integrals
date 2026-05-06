import re

code = '''import re
import sympy as sp

def _simple_latex_to_sympy_str(latex: str) -> str:
    s = latex.strip()
    # Remove \\displaystyle, \\text, etc.
    s = re.sub(r"\\\\(displaystyle|text|mathrm|mathbf)\\s*\\{?([^}]*)\\}?", r"\\2", s)
    
    def find_balanced_brace(text, start):
        if start >= len(text) or text[start] != "{":
            return -1
        depth, i = 1, start + 1
        while i < len(text):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        return -1
    
    # Convert \\frac{a}{b} to (a)/(b)
    while True:
        idx = s.find(r"\\\\frac")
        if idx == -1:
            break
        s1 = s.find("{", idx)
        if s1 == -1:
            break
        e1 = find_balanced_brace(s, s1)
        if e1 == -1:
            break
        s2 = s.find("{", e1 + 1)
        if s2 == -1:
            break
        e2 = find_balanced_brace(s, s2)
        if e2 == -1:
            break
        num = s[s1+1:e1].strip()
        den = s[s2+1:e2].strip()
        s = s[:idx] + f"({num})/({den})" + s[e2+1:]
    
    # Convert \\sqrt{expr} to (expr)**(1/2)
    while True:
        idx = s.find(r"\\\\sqrt")
        if idx == -1:
            break
        brace_start = s.find("{", idx)
        if brace_start == -1:
            break
        brace_end = find_balanced_brace(s, brace_start)
        if brace_end == -1:
            break
        inner = s[brace_start+1:brace_end]
        s = s[:idx] + f"({inner})**(1/2)" + s[brace_end+1:]
    
    # Convert \\sin{expr}, \\cos{expr}, etc.
    for func in ["sin", "cos", "tan", "sec", "csc", "cot", "log", "ln", "exp"]:
        pattern = r"\\\\" + func + r"\\s*(?:\\{([^{}]*)\\}|\\(([^()]*)\\))"
        while True:
            match = re.search(pattern, s)
            if not match:
                break
            inner = match.group(1) if match.group(1) is not None else match.group(2)
            s = s[:match.start()] + f"{func}({inner})" + s[match.end():]
    
    # Handle power notation
    s = re.sub(r"\\{([^{}]+)\\}\\^\\{([^{}]+)\\}", r"\\1**\\2", s)
    s = re.sub(r"([a-zA-Z_][a-zA-Z0-9_]*)\\^\\{([^}]+)\\}", r"\\1**\\2", s)
    s = re.sub(r"([a-zA-Z_][a-zA-Z0-9_]*)\\^([a-zA-Z0-9]+)", r"\\1**\\2", s)
    
    # Handle multiplication symbols
    s = s.replace(r"\\cdot", "*").replace(r"\\times", "*")
    
    # Handle implicit multiplication
    s = re.sub(r"(\\d)\\s*([a-zA-Z_])", r"\\1*\\2", s)
    s = re.sub(r"\\)\\s*([a-zA-Z_(])", r")*\\1", s)
    s = re.sub(r"([a-zA-Z_])\\s*\\(", r"\\1*(", s)
    
    # Remove remaining LaTeX commands
    s = re.sub(r"\\\\(?!sin|cos|tan|sec|csc|cot|log|ln|exp|sqrt|frac)[a-zA-Z]+", "", s)
    
    # Remove braces
    s = s.replace("{", "").replace("}", "")
    
    # Strip +C / -C
    s = re.sub(r"\\s*[+\\-]\\s*C\\b", "", s, flags=re.IGNORECASE)
    
    return s.strip()


def parse_latex(latex: str) -> sp.Expr | None:
    latex = re.sub(r"\\s*[+\\-]\\s*C\\b", "", latex, flags=re.IGNORECASE).strip()
    latex = re.sub(r"\\\\left\\(", "(", latex)
    latex = re.sub(r"\\\\right\\)", ")", latex)
    try:
        sympy_str = _simple_latex_to_sympy_str(latex)
        if sympy_str:
            return sp.sympify(sympy_str, evaluate=True)
    except Exception:
        pass
    try:
        return sp.sympify(latex, evaluate=True)
    except Exception:
        return None

def parse_expr(text: str, var: str = "x") -> sp.Expr | None:
    try:
        local_dict = {var: sp.Symbol(var)}
        return sp.sympify(text, locals=local_dict, evaluate=True)
    except Exception:
        return None

def best_parse(text: str, var: str = "x") -> sp.Expr | None:
    text = text.strip()
    text = re.sub(r"\\s*[+\\-]\\s*C\\b", "", text, flags=re.IGNORECASE).strip()
    if "\\\\" in text:
        expr = parse_latex(text)
        if expr is not None:
            return expr
    expr = parse_expr(text, var)
    if expr is not None:
        return expr
    return parse_latex(text)
'''

with open('src/calc_solver/tools/latex_parser.py', 'w', encoding='utf-8') as f:
    f.write(code)
print('Done')
