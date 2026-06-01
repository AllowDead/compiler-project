"""Sprint 7 IR optimization passes: constant folding, propagation, and DCE."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Set
from .ir_instructions import IROp, IROperand, IRInstruction
from .ir_generator import IRProgram


def _lit_value(op):
    return getattr(op, "value", None) if getattr(op, "kind", None) == "literal" else None


def _is_lit(op):
    return getattr(op, "kind", None) == "literal"


@dataclass
class OptimizationStats:
    constant_folds: int = 0
    constants_propagated: int = 0
    dead_instructions_removed: int = 0
    unreachable_blocks_removed: int = 0
    iterations: int = 0

    def to_text(self) -> str:
        return (
            "Optimization Report:\n"
            f"  Constant folding: {self.constant_folds} expressions folded\n"
            f"  Constant propagation: {self.constants_propagated} operands propagated\n"
            f"  Dead code elimination: {self.dead_instructions_removed} instructions removed\n"
            f"  Unreachable blocks removed: {self.unreachable_blocks_removed}\n"
            f"  Iterations: {self.iterations}"
        )


class IROptimizer:
    def __init__(self):
        self.stats = OptimizationStats()

    def optimize(self, program: IRProgram, max_iterations: int = 4) -> IRProgram:
        for _ in range(max_iterations):
            before = self._signature(program)
            self.stats.iterations += 1
            self.constant_folding(program)
            self.constant_propagation(program)
            self.dead_code_elimination(program)
            if self._signature(program) == before:
                break
        return program

    def _signature(self, program: IRProgram) -> str:
        return program.to_text()

    def constant_folding(self, program: IRProgram) -> None:
        for function in program.functions.values():
            for block in function.blocks.values():
                for inst in block.instructions:
                    op = inst.op
                    if op in {IROp.ADD, IROp.SUB, IROp.MUL, IROp.DIV, IROp.MOD, IROp.CMP_EQ, IROp.CMP_NE, IROp.CMP_LT, IROp.CMP_LE, IROp.CMP_GT, IROp.CMP_GE, IROp.AND, IROp.OR} and len(inst.args) >= 2 and _is_lit(inst.args[0]) and _is_lit(inst.args[1]):
                        a, b = _lit_value(inst.args[0]), _lit_value(inst.args[1])
                        try:
                            value = self._eval_binary(op, a, b)
                        except Exception:
                            continue
                        inst.opcode = IROp.MOVE
                        inst.args = [IROperand.literal(value, inst.type_name)]
                        inst.comment = (inst.comment or "") + " ; constant folded"
                        self.stats.constant_folds += 1

    def _eval_binary(self, op, a, b):
        if op == IROp.ADD: return a + b
        if op == IROp.SUB: return a - b
        if op == IROp.MUL: return a * b
        if op == IROp.DIV: return int(a / b)
        if op == IROp.MOD: return a % b
        if op == IROp.AND: return bool(a) and bool(b)
        if op == IROp.OR: return bool(a) or bool(b)
        if op == IROp.CMP_EQ: return a == b
        if op == IROp.CMP_NE: return a != b
        if op == IROp.CMP_LT: return a < b
        if op == IROp.CMP_LE: return a <= b
        if op == IROp.CMP_GT: return a > b
        if op == IROp.CMP_GE: return a >= b
        raise ValueError(op)

    def constant_propagation(self, program: IRProgram) -> None:
        for function in program.functions.values():
            constants: Dict[str, IROperand] = {}
            for label in function.block_order:
                block = function.blocks[label]
                for inst in block.instructions:
                    new_args = []
                    for arg in inst.args:
                        key = str(getattr(arg, "value", arg))
                        if getattr(arg, "kind", None) in ("temp", "var", "variable") and key in constants:
                            new_args.append(constants[key])
                            self.stats.constants_propagated += 1
                        else:
                            new_args.append(arg)
                    inst.args = new_args
                    if inst.op == IROp.MOVE and inst.dest and inst.args and _is_lit(inst.args[0]):
                        constants[str(inst.dest.value)] = inst.args[0]
                    elif inst.dest:
                        constants.pop(str(inst.dest.value), None)

    def dead_code_elimination(self, program: IRProgram) -> None:
        for function in program.functions.values():
            reachable = self._reachable_blocks(function)

            for label in list(function.block_order):
                if label not in reachable:
                    function.block_order.remove(label)
                    function.blocks.pop(label, None)
                    self.stats.unreachable_blocks_removed += 1

            used: Set[str] = set()

            def mark_operand_used(operand: Any) -> None:
                kind = getattr(operand, "kind", None)
                value = getattr(operand, "value", None)

                if kind == "temp" and value is not None:
                    used.add(str(value))

                text = str(operand)

                # Dynamic memory operand: [*t3]
                # This means temp t3 is used as an address.
                if text.startswith("[*") and text.endswith("]"):
                    inner = text[2:-1]
                    inner = inner.split("+", 1)[0]
                    if inner.startswith("t"):
                        used.add(inner)

                # Offset memory operand: [t3+4] or [*t3+4]
                if text.startswith("[") and text.endswith("]"):
                    inner = text[1:-1]
                    inner = inner.lstrip("*")
                    inner = inner.split("+", 1)[0]
                    if inner.startswith("t"):
                        used.add(inner)

            for block in function.blocks.values():
                for inst in block.instructions:
                    for arg in getattr(inst, "args", []):
                        mark_operand_used(arg)

                    # STORE may use address in destination, for example STORE [*t3], value
                    dest = getattr(inst, "dest", None)
                    if dest is not None and getattr(inst, "op", None) == IROp.STORE:
                        mark_operand_used(dest)

            side_effects = {
                IROp.STORE,
                IROp.CALL,
                IROp.RETURN,
                IROp.JUMP,
                IROp.JUMP_IF,
                IROp.JUMP_IF_NOT,
                IROp.PARAM,
                IROp.ALLOCA,
            }

            # Sprint 7: GEP creates an address used by LOAD [*t].
            # Do not remove it as dead code.
            if hasattr(IROp, "GEP"):
                side_effects.add(IROp.GEP)

            for block in function.blocks.values():
                kept = []

                for inst in block.instructions:
                    dest = getattr(inst, "dest", None)

                    if (
                            dest is not None
                            and getattr(dest, "kind", None) == "temp"
                            and str(dest.value) not in used
                            and inst.op not in side_effects
                    ):
                        self.stats.dead_instructions_removed += 1
                        continue

                    kept.append(inst)

                block.instructions = kept

            function.cfg().rebuild_edges()

    def _reachable_blocks(self, function) -> Set[str]:
        if not function.block_order:
            return set()
        edges = function.cfg().edges()
        graph: Dict[str, List[str]] = {}
        for src, dst in edges:
            graph.setdefault(src, []).append(dst)
        start = function.block_order[0]
        seen = set()
        stack = [start]
        while stack:
            label = stack.pop()
            if label in seen:
                continue
            seen.add(label)
            stack.extend(graph.get(label, []))
        return seen
