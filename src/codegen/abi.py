"""System V AMD64 ABI helpers for Sprint 5-7 code generation."""
from dataclasses import dataclass
from typing import List
import re


INTEGER_ARG_REGS_64: List[str] = ["rdi", "rsi", "rdx", "rcx", "r8", "r9"]
INTEGER_ARG_REGS_32: List[str] = ["edi", "esi", "edx", "ecx", "r8d", "r9d"]
CALLER_SAVED: List[str] = ["rax", "rcx", "rdx", "rsi", "rdi", "r8", "r9", "r10", "r11"]
CALLEE_SAVED: List[str] = ["rbx", "rbp", "r12", "r13", "r14", "r15"]


def align_to(value: int, alignment: int = 16) -> int:
    if value <= 0:
        return 0
    return ((value + alignment - 1) // alignment) * alignment


def _base_size(type_name: str) -> int:
    if type_name in ("bool", "byte", "char"):
        return 1
    if type_name in ("int", "float"):
        return 4
    if type_name in ("void", None):
        return 0
    if type_name == "string" or str(type_name).endswith("*") or str(type_name).endswith("[]") or type_name == "ptr":
        return 8
    return 8


def size_of(type_name: str) -> int:
    text = str(type_name or "void")
    dims = [int(x) for x in re.findall(r"\[(\d+)\]", text)]
    if dims:
        base = re.sub(r"\[\d+\]", "", text)
        size = _base_size(base)
        for dim in dims:
            size *= dim
        return size
    return _base_size(text)


def is_pointer_like(type_name: str) -> bool:
    text = str(type_name or "")
    return text in ("string", "ptr") or text.endswith("*") or text.endswith("[]")


def mem_prefix(type_name: str) -> str:
    size = size_of(type_name)
    if size == 1:
        return "byte"
    if size == 4:
        return "dword"
    return "qword"


@dataclass(frozen=True)
class ABIInfo:
    integer_arg_regs_64: List[str]
    integer_arg_regs_32: List[str]
    caller_saved: List[str]
    callee_saved: List[str]
    stack_alignment: int = 16
    red_zone_size: int = 128


SYSTEM_V_AMD64 = ABIInfo(
    integer_arg_regs_64=INTEGER_ARG_REGS_64,
    integer_arg_regs_32=INTEGER_ARG_REGS_32,
    caller_saved=CALLER_SAVED,
    callee_saved=CALLEE_SAVED,
)
