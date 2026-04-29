import re
import sympy as sp

def _simple_latex_to_sympy_str(latex: str) -> str:
    s = latex.strip()
    s = re.sub(r'\\(displaystyle|text|mathrm|mathbf)\\?{?([^}]*)}?', r'\\2', s)
    
    def balanced_brace_match(text, start):
        if start >= len(text) or text[start] != '{':
            return -1
        depth, i = 0, start
        while i < len(text):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        return -1
    
    while True:
        idx = s.find(r'\\frac')
        if idx == -1:
            break
        s1 = s.find('{', idx)
        if s1 == -1:
            break
        e1 = balanced_brace_match(s, s1)
        if e1 == -1:
            break
        s2 = s.find('{', e1 + 1)
        if s2 == -1:
            break
        e2 = balanced_brace_match(s, s2)
        if e2 == -1:
            break
        num = s[s1+1:e1].strip()
        den = s[s2+1:e2].strip()
        s = s[:idx] + f'({num})/({den})' + s[e2+1:]
    
    s = re.sub(r'\{([^{}]+)\}\^\{([^{}]+)\}', r'\1**\2', s)
    s = re.sub(r'([a-zA-Z])\^\{([^}]+)\}', r'\1**\2', s)
    s = re.sub(r'([a-zA-Z])\^([a-zA-Z0-9]+)', r'\1**\2', s)
    s = s.replace(r'\\cdot', '*').replace(r'\\times', '*')
    s = re.sub(r'\\[a-zA-Z]+', '', s)
    s = s.replace('{', '').replace('}', '')
    s = re.sub(r'\\?\s*[+\-]\s*C\b', '', s, flags=re.IGNORECASE)
    return s.strip()


def parse_latex(latex: str) -> sp.Expr | None:
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
        return None


def parse_expr(text: str, var: str = "x") -> sp.Expr | None:
    try:
        local_dict = {var: sp.Symbol(var)}
        return sp.sympify(text, locals=local_dict, evaluate=True)
    except Exception:
        return None


def best_parse(text: str, var: str = "x") -> sp.Expr | None:
    text = text.strip()
    if "\\" in text:
        expr = parse_latex(text)
        if expr is not None:
            return expr
    expr = parse_expr(text, var)
    if expr is not None:
        return expr
    return parse_latex(text)
