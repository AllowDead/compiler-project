"""System V AMD64 ABI helpers for Sprint 5 code generation."""
from dataclasses import dataclass
from typing import List


INTEGER_ARG_REGS_64: List[str] = ["rdi", "rsi", "rdx", "rcx", "r8", "r9"]
INTEGER_ARG_REGS_32: List[str] = ["edi", "esi", "edx", "ecx", "r8d", "r9d"]
CALLER_SAVED: List[str] = ["rax", "rcx", "rdx", "rsi", "rdi", "r8", "r9", "r10", "r11"]
CALLEE_SAVED: List[str] = ["rbx", "rbp", "r12", "r13", "r14", "r15"]


def align_to(value: int, alignment: int = 16) -> int:
    if value <= 0:
        return 0
    return ((value + alignment - 1) // alignment) * alignment


def size_of(type_name: str) -> int:
    if type_name in ("bool", "byte"):
        return 1
    if type_name in ("int", "float"):
        return 4
    if type_name in ("void", None):
        return 0
    return 8


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
