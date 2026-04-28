from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


class Problem(BaseModel):
    problem_id: str
    question: str
    gold_answer: str
    answer_type: Literal["expression", "value", "set", "interval"] = "expression"
    variable: str = "x"
    metadata: dict = Field(default_factory=dict)


class Strategy(BaseModel):
    strategy_id: str
    name: str
    rationale: str
    steps_outline: list[str]


class StepTrace(BaseModel):
    step_no: int
    thought: str
    tool_call: Optional[dict] = None
    tool_result: Optional[str] = None
    state: Optional[str] = None


class Solution(BaseModel):
    strategy_id: str
    final_answer: str = ""
    final_answer_sympy: Optional[str] = None
    steps: list[StepTrace] = Field(default_factory=list)
    self_check_passed: bool = False
    error: Optional[str] = None


class EvalResult(BaseModel):
    problem_id: str
    chosen_strategy_id: Optional[str] = None
    final_answer: Optional[str] = None
    is_correct: bool = False
    confidence: float = 0.0
    method_agreement: int = 0
    candidates: list[Solution] = Field(default_factory=list)
    notes: str = ""
    loop_count: int = 0
