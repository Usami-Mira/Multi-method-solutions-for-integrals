from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal, Optional

import numpy as np
import sympy as sp
from pydantic import BaseModel

from calc_solver.tools.latex_parser import best_parse

if TYPE_CHECKING:
    from calc_solver.llm.client import QwenClient


class VerifyResult(BaseModel):
    is_eq: bool
    level_used: Literal["L1", "L2", "L3", "L4", "L5", "fail"]
    confidence: float
    evidence: str


SIMPLIFIERS = [
    sp.simplify,
    lambda e: sp.trigsimp(e, method="fu"),
    sp.expand_trig,
    lambda e: sp.expand_log(e, force=True),
    sp.radsimp,
    sp.together,
    sp.cancel,
    sp.factor,
    sp.powsimp,
    lambda e: sp.logcombine(e, force=True),
    lambda e: sp.simplify(sp.expand(e)),
    lambda e: sp.nsimplify(e, rational=True),
]


def _try_zero(diff_expr: sp.Expr) -> bool:
    if diff_expr == 0:
        return True
    for f in SIMPLIFIERS:
        try:
            r = f(diff_expr)
            if r == 0 or (hasattr(r, "is_zero") and r.is_zero is True):
                return True
        except Exception:
            continue
    return False


class Verifier:
    def __init__(
        self,
        llm_client: Optional["QwenClient"] = None,
        n_samples: int = 30,
        llm_for_unsure: bool = True,
    ):
        self.llm_client = llm_client
        self.n_samples = n_samples
        self.llm_for_unsure = llm_for_unsure

    def is_equivalent(
        self,
        pred: str,
        gold: str,
        *,
        var: str = "x",
        answer_type: str = "expression",
        question: str = "",
    ) -> VerifyResult:
        # L1: string normalisation
        if self._l1(pred, gold):
            return VerifyResult(is_eq=True, level_used="L1", confidence=1.0, evidence="string_equal")

        pred_expr = best_parse(pred, var)
        gold_expr = best_parse(gold, var)

        if pred_expr is None or gold_expr is None:
            # Can't do symbolic checks; try L5 if available
            if self.llm_client and self.llm_for_unsure:
                return self._l5(pred, gold, var, answer_type, question, 0, 0)
            return VerifyResult(is_eq=False, level_used="fail", confidence=0.0, evidence="parse_failed")

        # L2: symbolic simplification
        l2 = self._l2(pred_expr, gold_expr, answer_type)
        if l2 is not None:
            return VerifyResult(is_eq=l2, level_used="L2", confidence=0.95,
                                evidence="symbolic_simplify")

        # L3: type-specific
        l3 = self._l3(pred_expr, gold_expr, pred, gold, var, answer_type)
        if l3 is not None:
            return VerifyResult(is_eq=l3, level_used="L3", confidence=0.95,
                                evidence="type_specific")

        # L4: numerical sampling
        l4_result, pass_count, total_count = self._l4(pred_expr, gold_expr, var, answer_type)
        if l4_result is True:
            return VerifyResult(is_eq=True, level_used="L4", confidence=0.9,
                                evidence=f"numerical_{pass_count}/{total_count}")
        if l4_result is False:
            return VerifyResult(is_eq=False, level_used="L4", confidence=0.9,
                                evidence=f"numerical_{pass_count}/{total_count}")

        # L4 inconclusive → maybe L5
        if self.llm_client and self.llm_for_unsure and pass_count >= total_count * 0.5:
            return self._l5(pred, gold, var, answer_type, question, pass_count, total_count)

        return VerifyResult(is_eq=False, level_used="L4", confidence=0.5,
                            evidence=f"inconclusive_{pass_count}/{total_count}")

    # ── L1 ──────────────────────────────────────────────────────────────────
    def _l1(self, pred: str, gold: str) -> bool:
        def norm(s: str) -> str:
            s = s.strip().replace(" ", "")
            s = s.replace(r"\dfrac", r"\frac").replace(r"\tfrac", r"\frac")
            s = re.sub(r"[\(\)\{\}]", lambda m: {"(": "[", ")": "]", "{": "[", "}": "]"}[m.group()], s)
            return s
        return norm(pred) == norm(gold)

    # ── L2 ──────────────────────────────────────────────────────────────────
    def _l2(self, pred: sp.Expr, gold: sp.Expr, answer_type: str) -> bool | None:
        """Returns True if proven equal, None if uncertain. Never returns False."""
        try:
            diff = pred - gold
            if _try_zero(diff):
                return True
        except Exception:
            pass
        return None

    # ── L3 ──────────────────────────────────────────────────────────────────
    def _l3(self, pred: sp.Expr, gold: sp.Expr, pred_str: str, gold_str: str,
             var: str, answer_type: str) -> bool | None:
        x = sp.Symbol(var)
        try:
            if answer_type == "expression":
                # For indefinite integrals: compare derivatives
                dp = sp.diff(pred, x)
                dg = sp.diff(gold, x)
                if _try_zero(dp - dg):
                    return True
            elif answer_type == "value":
                try:
                    pv = float(pred.evalf())
                    gv = float(gold.evalf())
                    return abs(pv - gv) < 1e-7
                except Exception:
                    pass
            elif answer_type in ("set", "interval"):
                if pred == gold:
                    return True
        except Exception:
            pass
        return None

    # ── L4 ──────────────────────────────────────────────────────────────────
    def _l4(self, pred: sp.Expr, gold: sp.Expr, var: str,
             answer_type: str) -> tuple[bool | None, int, int]:
        x = sp.Symbol(var)
        rng = np.random.RandomState(42)
        points = rng.uniform(-3, 3, self.n_samples)

        # For indefinite integrals compare derivatives to cancel +C
        if answer_type == "expression":
            try:
                pred_d = sp.diff(pred, x)
                gold_d = sp.diff(gold, x)
                pred_fn = sp.lambdify(x, pred_d, "numpy")
                gold_fn = sp.lambdify(x, gold_d, "numpy")
            except Exception:
                return None, 0, 0
        else:
            try:
                pred_fn = sp.lambdify(x, pred, "numpy")
                gold_fn = sp.lambdify(x, gold, "numpy")
            except Exception:
                return None, 0, 0

        pass_count = 0
        valid_count = 0
        for pt in points:
            try:
                pv = complex(pred_fn(pt))
                gv = complex(gold_fn(pt))
                if np.isnan(pv.real) or np.isinf(pv.real) or np.isnan(gv.real) or np.isinf(gv.real):
                    continue
                if abs(pv.imag) > 1e-6 or abs(gv.imag) > 1e-6:
                    continue
                tol = max(1e-7, 1e-6 * abs(gv.real))
                valid_count += 1
                if abs(pv.real - gv.real) < tol:
                    pass_count += 1
            except Exception:
                continue

        if valid_count < 10:
            return None, pass_count, valid_count
        if pass_count >= 28 * valid_count / 30:
            return True, pass_count, valid_count
        return False, pass_count, valid_count

    # ── L5 ──────────────────────────────────────────────────────────────────
    def _l5(self, pred: str, gold: str, var: str, answer_type: str,
             question: str, pass_count: int, total: int) -> VerifyResult:
        import asyncio
        import json as _json
        prompt = (
            f"你是数学等价性裁判，只回答数学等价问题。\n"
            f"题目背景: {question[:300]}\n"
            f"答案类型: {answer_type}\n"
            f"候选答案 P: {pred}\n"
            f"标准答案 G: {gold}\n"
            f"数值采样线索: {pass_count}/{total} 点近似相等，符号化简未能归零\n\n"
            "只输出JSON（无Markdown）：\n"
            '{"equivalent": true | false, "reason": "≤2句中文说明"}\n\n'
            "判定准则：仅当P、G在所有合法定义域上恒等才为true；"
            "含任意常数C（不定积分）时把P-G是否为常数视作等价。"
        )
        try:
            if asyncio.get_event_loop().is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    fut = pool.submit(asyncio.run,
                                      self.llm_client.chat([{"role": "user", "content": prompt}],
                                                            temperature=0.0, json_mode=True))
                    raw = fut.result(timeout=30)
            else:
                raw = asyncio.run(
                    self.llm_client.chat([{"role": "user", "content": prompt}],
                                         temperature=0.0, json_mode=True))
            data = _json.loads(raw)
            is_eq = bool(data.get("equivalent", False))
            reason = data.get("reason", "")
            return VerifyResult(is_eq=is_eq, level_used="L5", confidence=0.6, evidence=reason)
        except Exception as e:
            return VerifyResult(is_eq=False, level_used="fail", confidence=0.0,
                                evidence=f"L5_error: {e}")
