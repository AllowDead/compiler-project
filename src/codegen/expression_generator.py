"""Expression codegen notes and reusable helpers for Sprint 6.

The current backend still lowers most arithmetic expressions through the IR
stack-machine style used in Sprint 5. Sprint 6 adds branch-aware handling for
boolean expressions: the IR generator emits short-circuit basic blocks for
&&/||, and x86_generator lowers comparison branches directly to jl/jle/jg/etc.
"""
from __future__ import annotations

from typing import Any


def is_boolean_literal(operand: Any) -> bool:
    return str(operand) in {"true", "false"}


def truthy_literal_value(operand: Any) -> int:
    text = str(operand)
    if text == "true":
        return 1
    if text in {"false", "None"}:
        return 0
    return int(text)
