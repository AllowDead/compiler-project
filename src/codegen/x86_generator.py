"""x86-64 NASM code generator for MiniCompiler Sprint 5.

The backend consumes the Sprint 4 IR program and emits Linux x86-64 assembly
following the System V AMD64 ABI. It deliberately uses a stack-heavy lowering:
IR variables and temporaries have stable stack slots, while eax/ecx/edx are used
as scratch registers for instruction selection.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .abi import INTEGER_ARG_REGS_32, mem_prefix, size_of
from .register_allocator import RegisterAllocator
from .stack_frame import StackFrame


TERMINATORS = {"JUMP", "JUMP_IF", "JUMP_IF_NOT", "RETURN"}


def _opname(instruction: Any) -> str:
    op = getattr(instruction, "op", None)
    if hasattr(op, "value"):
        return str(op.value)
    return str(op)


def _operand_kind(operand: Any) -> str:
    return str(getattr(operand, "kind", ""))


def _operand_value(operand: Any) -> Any:
    return getattr(operand, "value", operand)


def _operand_text(operand: Any) -> str:
    return str(operand)


def _is_int_literal(text: str) -> bool:
    try:
        int(text)
        return True
    except ValueError:
        return False


@dataclass
class CodegenResult:
    assembly: str
    stack_bytes: int
    instruction_count: int


class X86Generator:
    def __init__(self, target: str = "x86_64", syntax: str = "nasm"):
        if target != "x86_64":
            raise ValueError("Sprint 5 backend only supports target='x86_64'.")
        if syntax != "nasm":
            raise ValueError("Sprint 5 backend currently emits NASM syntax only.")
        self.target = target
        self.syntax = syntax
        self.lines: List[str] = []
        self.frame: Optional[StackFrame] = None
        self.regalloc = RegisterAllocator()
        self.current_function: Any = None
        self.label_map: Dict[str, str] = {}
        self.pending_call_args: List[Any] = []
        self.epilogue_label = ""
        self.instruction_count = 0

    def generate(self, ir_program: Any) -> str:
        self.lines = []
        self._emit_header(ir_program)
        function_order = getattr(ir_program, "function_order", list(getattr(ir_program, "functions", {}).keys()))
        functions = getattr(ir_program, "functions", {})
        for function_name in function_order:
            self._generate_function(functions[function_name])
        return "\n".join(self.lines).rstrip() + "\n"

    def generate_result(self, ir_program: Any) -> CodegenResult:
        asm = self.generate(ir_program)
        return CodegenResult(asm, self.frame.stack_size if self.frame else 0, self.instruction_count)

    def _emit_header(self, ir_program: Any) -> None:
        self.lines.append("; Generated MiniCompiler x86-64 assembly")
        self.lines.append("; Syntax: NASM, ABI: System V AMD64")
        self.lines.append("default rel")
        self.lines.append("section .text")
        functions = getattr(ir_program, "functions", {})
        for name in getattr(ir_program, "function_order", list(functions.keys())):
            self.lines.append(f"global {name}")
        self.lines.append("")

    def _generate_function(self, function: Any) -> None:
        self.current_function = function
        self.frame = self._build_stack_frame(function)
        self.label_map = self._make_label_map(function)
        self.pending_call_args = []
        name = getattr(function, "name", "function")
        self.epilogue_label = f".L{name}_epilogue"

        self.lines.append(f"; function {name}: {getattr(function, 'return_type', 'void')}")
        self.lines.append(f"{name}:")
        self.lines.append("    ; Prologue")
        self.lines.append("    push rbp")
        self.lines.append("    mov rbp, rsp")
        if self.frame.stack_size:
            self.lines.append(f"    sub rsp, {self.frame.stack_size}    ; 16-byte aligned local frame")
        else:
            self.lines.append("    ; no local stack allocation needed")
        self.lines.append("    ; Red zone strategy: not used; safe for functions that perform calls")

        for label in getattr(function, "block_order", []):
            block = function.blocks[label]
            asm_label = self.label_map[label]
            self.lines.append("")
            self.lines.append(f"{asm_label}:")
            if getattr(block, "kind", None):
                self.lines.append(f"    ; Basic block: {block.kind}")
            for instruction in block.instructions:
                self._lower_instruction(instruction)

        # Ensure all functions have a single generated epilogue.
        self.lines.append("")
        self.lines.append(f"{self.epilogue_label}:")
        if getattr(function, "return_type", "void") == "void":
            self.lines.append("    xor eax, eax    ; default void return code")
        self.lines.append("    ; Epilogue")
        self.lines.append("    mov rsp, rbp")
        self.lines.append("    pop rbp")
        self.lines.append("    ret")
        self.lines.append("")

    def _build_stack_frame(self, function: Any) -> StackFrame:
        frame = StackFrame(getattr(function, "name", "function"))

        # Variables from IR metadata.
        for slot in getattr(function, "variables", {}).values():
            ir_name = getattr(slot, "ir_name", None) or getattr(slot, "name", None) or str(slot)
            source_name = getattr(slot, "source_name", None) or getattr(slot, "name", None)
            type_name = getattr(slot, "type_name", "int")
            frame.add_slot(ir_name, type_name, source_name=source_name)

        # Temporaries from IR metadata.
        for temp_name, type_name in getattr(function, "temp_types", {}).items():
            frame.add_slot(temp_name, type_name, source_name=temp_name)

        # Also discover values from instructions to be robust.
        for block in [function.blocks[label] for label in getattr(function, "block_order", [])]:
            for inst in block.instructions:
                if getattr(inst, "dest", None) is not None:
                    dest = inst.dest
                    if _operand_kind(dest) in ("temp", "variable"):
                        frame.add_slot(str(_operand_value(dest)), getattr(inst, "type_name", "int"), str(_operand_value(dest)))
                for arg in getattr(inst, "args", []):
                    text = _operand_text(arg)
                    if text.startswith("[") and text.endswith("]"):
                        frame.add_slot(text[1:-1], "int", text[1:-1])
        return frame

    def _make_label_map(self, function: Any) -> Dict[str, str]:
        name = getattr(function, "name", "function")
        mapping = {}
        for index, label in enumerate(getattr(function, "block_order", [])):
            mapping[label] = f".LBB_{name}_{index}"
        return mapping

    def _lower_instruction(self, inst: Any) -> None:
        op = _opname(inst)
        comment = getattr(inst, "comment", None)
        if comment:
            self.lines.append(f"    ; {comment}")

        if op == "ALLOCA":
            self.lines.append(f"    ; {self._format_ir(inst)} ; stack slot allocated in prologue")
            return

        self.instruction_count += 1
        args = list(getattr(inst, "args", []))
        dest = getattr(inst, "dest", None)

        if op == "STORE":
            self._emit_load_to("eax", args[1])
            self.lines.append(f"    mov {self._memory(args[0])}, eax")
        elif op == "LOAD":
            self.lines.append(f"    mov eax, {self._memory(args[0])}")
            self._emit_store_from("eax", dest)
        elif op == "MOVE":
            self._emit_load_to("eax", args[0])
            self._emit_store_from("eax", dest)
        elif op in ("ADD", "SUB", "MUL", "AND", "OR", "XOR"):
            self._emit_binary(op, dest, args[0], args[1])
        elif op in ("DIV", "MOD"):
            self._emit_division(op, dest, args[0], args[1])
        elif op in ("NEG", "NOT"):
            self._emit_unary(op, dest, args[0])
        elif op.startswith("CMP_"):
            self._emit_compare(op, dest, args[0], args[1])
        elif op == "JUMP":
            self.lines.append(f"    jmp {self._label(args[0])}")
        elif op == "JUMP_IF":
            self._emit_load_to("eax", args[0])
            self.lines.append("    cmp eax, 0")
            self.lines.append(f"    jne {self._label(args[1])}")
        elif op == "JUMP_IF_NOT":
            self._emit_load_to("eax", args[0])
            self.lines.append("    cmp eax, 0")
            self.lines.append(f"    je {self._label(args[1])}")
        elif op == "PARAM":
            self.pending_call_args.append(args[1])
            self.lines.append(f"    ; PARAM {args[0]}, {args[1]}")
        elif op == "CALL":
            self._emit_call(dest, args)
        elif op == "RETURN":
            if args:
                self._emit_load_to("eax", args[0])
            self.lines.append(f"    jmp {self.epilogue_label}")
        elif op == "PHI":
            # This backend lowers memory-based IR. PHI is metadata for future SSA backends.
            self.lines.append(f"    ; PHI ignored by memory-based x86 lowering: {self._format_ir(inst)}")
        else:
            self.lines.append(f"    ; unsupported IR op kept as comment: {self._format_ir(inst)}")

    def _emit_binary(self, op: str, dest: Any, left: Any, right: Any) -> None:
        self._emit_load_to("eax", left)
        if op == "ADD":
            self.lines.append(f"    add eax, {self._rhs32(right)}")
        elif op == "SUB":
            self.lines.append(f"    sub eax, {self._rhs32(right)}")
        elif op == "MUL":
            self.lines.append(f"    imul eax, {self._rhs32(right)}")
        elif op == "AND":
            self.lines.append(f"    and eax, {self._rhs32(right)}")
        elif op == "OR":
            self.lines.append(f"    or eax, {self._rhs32(right)}")
        elif op == "XOR":
            self.lines.append(f"    xor eax, {self._rhs32(right)}")
        self._emit_store_from("eax", dest)

    def _emit_division(self, op: str, dest: Any, left: Any, right: Any) -> None:
        self._emit_load_to("eax", left)
        self.lines.append("    cdq")
        self._emit_load_to("ecx", right)
        self.lines.append("    idiv ecx")
        self._emit_store_from("edx" if op == "MOD" else "eax", dest)

    def _emit_unary(self, op: str, dest: Any, operand: Any) -> None:
        self._emit_load_to("eax", operand)
        if op == "NEG":
            self.lines.append("    neg eax")
        elif op == "NOT":
            self.lines.append("    cmp eax, 0")
            self.lines.append("    sete al")
            self.lines.append("    movzx eax, al")
        self._emit_store_from("eax", dest)

    def _emit_compare(self, op: str, dest: Any, left: Any, right: Any) -> None:
        jump_suffix = {
            "CMP_EQ": "e",
            "CMP_NE": "ne",
            "CMP_LT": "l",
            "CMP_LE": "le",
            "CMP_GT": "g",
            "CMP_GE": "ge",
        }[op]
        self._emit_load_to("eax", left)
        self.lines.append(f"    cmp eax, {self._rhs32(right)}")
        self.lines.append(f"    set{jump_suffix} al")
        self.lines.append("    movzx eax, al")
        self._emit_store_from("eax", dest)

    def _emit_call(self, dest: Any, args: List[Any]) -> None:
        func_name = str(_operand_value(args[0]))
        argc = int(str(_operand_value(args[1]))) if len(args) > 1 and _is_int_literal(str(_operand_value(args[1]))) else len(self.pending_call_args)
        call_args = self.pending_call_args[:argc]
        self.pending_call_args = self.pending_call_args[argc:]

        extra = call_args[6:]
        for arg in reversed(extra):
            self._emit_load_to("eax", arg)
            self.lines.append("    push rax")
        for index, arg in enumerate(call_args[:6]):
            self._emit_load_to("eax", arg)
            self.lines.append(f"    mov {INTEGER_ARG_REGS_32[index]}, eax")
        self.lines.append(f"    call {func_name}")
        if extra:
            self.lines.append(f"    add rsp, {len(extra) * 8}")
        if dest is not None:
            self._emit_store_from("eax", dest)

    def _emit_load_to(self, reg: str, operand: Any) -> None:
        text = _operand_text(operand)
        kind = _operand_kind(operand)
        value = _operand_value(operand)

        if text == "true":
            self.lines.append(f"    mov {reg}, 1")
        elif text == "false" or text == "None":
            self.lines.append(f"    mov {reg}, 0")
        elif _is_int_literal(text):
            self.lines.append(f"    mov {reg}, {int(text)}")
        elif text.startswith("[") and text.endswith("]"):
            self.lines.append(f"    mov {reg}, {self._memory(operand)}")
        elif kind in ("temp", "variable"):
            slot = self.frame.require(str(value))
            self.lines.append(f"    mov {reg}, dword {slot.address}")
        elif text in self._param_register_map():
            self.lines.append(f"    mov {reg}, {self._param_register_map()[text]}")
        else:
            # Symbolic variable or parameter name.
            slot = self._find_slot_by_source(text)
            if slot:
                self.lines.append(f"    mov {reg}, dword {slot.address}")
            else:
                self.lines.append(f"    ; unresolved operand {text}; defaulting to 0")
                self.lines.append(f"    xor {reg}, {reg}")

    def _rhs32(self, operand: Any) -> str:
        text = _operand_text(operand)
        if text == "true":
            return "1"
        if text == "false" or text == "None":
            return "0"
        if _is_int_literal(text):
            return str(int(text))
        if text.startswith("[") and text.endswith("]"):
            return self._memory(operand)
        kind = _operand_kind(operand)
        value = _operand_value(operand)
        if kind in ("temp", "variable"):
            return f"dword {self.frame.require(str(value)).address}"
        if text in self._param_register_map():
            return self._param_register_map()[text]
        slot = self._find_slot_by_source(text)
        if slot:
            return f"dword {slot.address}"
        return "0"

    def _emit_store_from(self, reg: str, dest: Any) -> None:
        if dest is None:
            return
        kind = _operand_kind(dest)
        value = str(_operand_value(dest))
        if kind in ("temp", "variable"):
            slot = self.frame.require(value, getattr(dest, "type_name", "int"))
            self.lines.append(f"    mov dword {slot.address}, {reg}")
        else:
            slot = self.frame.require(value)
            self.lines.append(f"    mov dword {slot.address}, {reg}")

    def _memory(self, operand: Any) -> str:
        text = _operand_text(operand)
        name = text[1:-1] if text.startswith("[") and text.endswith("]") else text
        slot = self.frame.require(name)
        return f"dword {slot.address}"

    def _label(self, operand: Any) -> str:
        text = str(_operand_value(operand))
        return self.label_map.get(text, text)

    def _param_register_map(self) -> Dict[str, str]:
        result: Dict[str, str] = {}
        for index, param in enumerate(getattr(self.current_function, "parameters", [])):
            if index >= len(INTEGER_ARG_REGS_32):
                break
            if isinstance(param, (list, tuple)) and len(param) >= 2:
                name = str(param[1])
            else:
                name = str(param)
            result[name] = INTEGER_ARG_REGS_32[index]
        return result

    def _find_slot_by_source(self, source_name: str):
        for slot in self.frame:
            if slot.source_name == source_name or slot.name == source_name:
                return slot
        return None

    def _format_ir(self, inst: Any) -> str:
        return str(inst).strip()
