from __future__ import annotations

from typing import Any

import sympy as sp


def parse_latex(latex: str) -> sp.Expr | None:
    """Try latex2sympy2 first, fall back to sympify."""
    try:
        from latex2sympy2 import latex2sympy  # type: ignore
        result = latex2sympy(latex)
        if result is not None:
            return result
    except Exception:
        pass
    try:
        return sp.sympify(latex, evaluate=True)
    except Exception:
        return None


def parse_expr(text: str, var: str = "x") -> sp.Expr | None:
    """Parse a plain sympy-style expression string."""
    try:
        local_dict = {var: sp.Symbol(var)}
        return sp.sympify(text, locals=local_dict, evaluate=True)
    except Exception:
        return None


def best_parse(text: str, var: str = "x") -> sp.Expr | None:
    """For LaTeX strings (contain backslash), try latex2sympy2 first; otherwise sympify."""
    text = text.strip()
    if "\\" in text:
        expr = parse_latex(text)
        if expr is not None:
            return expr
    # Try sympify directly (handles standard Python/SymPy expression syntax)
    expr = parse_expr(text, var)
    if expr is not None:
        return expr
    # Last resort: latex2sympy2 for non-backslash strings
    return parse_latex(text)
