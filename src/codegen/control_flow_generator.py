"""Control-flow instruction selection for Sprint 6.

This module contains the small amount of pattern matching needed to turn IR
comparison + branch pairs into direct x86-64 conditional jumps such as jl/jle.
"""
from __future__ import annotations

from typing import Any, Optional, Tuple


CMP_TO_JUMP = {
    "CMP_EQ": "e",
    "CMP_NE": "ne",
    "CMP_LT": "l",
    "CMP_LE": "le",
    "CMP_GT": "g",
    "CMP_GE": "ge",
}

INVERT_JUMP = {
    "e": "ne",
    "ne": "e",
    "l": "ge",
    "le": "g",
    "g": "le",
    "ge": "l",
}


def opname(instruction: Any) -> str:
    op = getattr(instruction, "op", None)
    if hasattr(op, "value"):
        return str(op.value)
    return str(op)


def operand_value(operand: Any) -> Any:
    return getattr(operand, "value", operand)


def same_operand(left: Any, right: Any) -> bool:
    return str(operand_value(left)) == str(operand_value(right))


class ControlFlowGenerator:
    """Recognizes compare-then-branch IR patterns."""

    @staticmethod
    def branch_from_compare(compare_inst: Any, branch_inst: Any) -> Optional[Tuple[str, Any, Any, Any]]:
        cmp_op = opname(compare_inst)
        br_op = opname(branch_inst)
        if cmp_op not in CMP_TO_JUMP or br_op not in ("JUMP_IF", "JUMP_IF_NOT"):
            return None
        if getattr(compare_inst, "dest", None) is None or len(getattr(compare_inst, "args", [])) < 2:
            return None
        branch_args = list(getattr(branch_inst, "args", []))
        if len(branch_args) < 2 or not same_operand(compare_inst.dest, branch_args[0]):
            return None

        suffix = CMP_TO_JUMP[cmp_op]
        if br_op == "JUMP_IF_NOT":
            suffix = INVERT_JUMP[suffix]
        left, right = compare_inst.args[0], compare_inst.args[1]
        target = branch_args[1]
        return suffix, left, right, target
