import re
import sympy as sp
from sympy.parsing.latex import parse_latex as sympy_parse_latex


def parse_latex(latex: str) -> sp.Expr | None:
    """Parse LaTeX string to SymPy expression using SymPy's built-in parser."""
    latex = re.sub(r"\s*[+\-]\s*C\b", "", latex, flags=re.IGNORECASE).strip()
    latex = re.sub(r"\\left\(", "(", latex)
    latex = re.sub(r"\\right\)", ")", latex)
    try:
        return sympy_parse_latex(latex)
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
    text = re.sub(r"\s*[+\-]\s*C\b", "", text, flags=re.IGNORECASE).strip()
    if "\\" in text:
        expr = parse_latex(text)
        if expr is not None:
            return expr
    expr = parse_expr(text, var)
    if expr is not None:
        return expr
    return parse_latex(text)
