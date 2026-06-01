from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from parser.ast_nodes import (
    AssignmentExprNode,
    ArrayAccessExprNode,
    BinaryExprNode,
    BlockNode,
    CallExprNode,
    ExprStmtNode,
    ForStmtNode,
    FunctionDeclNode,
    IdentifierExprNode,
    IfStmtNode,
    LiteralExprNode,
    ProgramNode,
    ReturnStmtNode,
    StructDeclNode,
    UnaryExprNode,
    VarDeclNode,
    WhileStmtNode,
)

from .basic_block import BasicBlock
from .control_flow import ControlFlowGraph
from .ir_instructions import IRInstruction, IROp, IROperand


_TYPE_SIZES = {
    "int": 4,
    "float": 4,
    "bool": 1,
    "void": 0,
    "string": 8,
}


@dataclass
class VariableSlot:
    source_name: str
    ir_name: str
    type_name: str
    offset: int

    @property
    def memory(self) -> IROperand:
        return IROperand.memory(self.ir_name, self.type_name)

    def to_json(self) -> Dict[str, Any]:
        return {
            "source_name": self.source_name,
            "ir_name": self.ir_name,
            "type": self.type_name,
            "offset": self.offset,
        }


@dataclass
class FunctionIR:
    name: str
    return_type: str
    parameters: List[tuple[str, str]]
    blocks: Dict[str, BasicBlock] = field(default_factory=dict)
    block_order: List[str] = field(default_factory=list)
    variables: Dict[str, VariableSlot] = field(default_factory=dict)
    temp_types: Dict[str, str] = field(default_factory=dict)
    stack_size: int = 0

    def add_block(self, block: BasicBlock) -> BasicBlock:
        if block.label not in self.blocks:
            self.blocks[block.label] = block
            self.block_order.append(block.label)
        return self.blocks[block.label]

    def cfg(self) -> ControlFlowGraph:
        graph = ControlFlowGraph(self.blocks, "entry")
        graph.rebuild_edges()
        return graph

    def to_text(self) -> str:
        params = ", ".join(f"{typ} {name}" for typ, name in self.parameters)
        lines = [f"function {self.name}: {self.return_type} ({params})"]
        for label in self.block_order:
            lines.append(self.blocks[label].to_text("  "))
            lines.append("")
        if self.variables:
            lines.append("  # Symbol table mapping:")
            for slot in self.variables.values():
                lines.append(
                    f"  # {slot.ir_name} -> local variable {slot.source_name} "
                    f"at offset {slot.offset}, type {slot.type_name}"
                )
        return "\n".join(lines).rstrip()

    def to_json(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "return_type": self.return_type,
            "parameters": [{"name": n, "type": t} for t, n in self.parameters],
            "blocks": [self.blocks[label].to_json() for label in self.block_order],
            "variables": [slot.to_json() for slot in self.variables.values()],
            "temporaries": self.temp_types,
            "stack_size": self.stack_size,
        }

    def statistics(self) -> Dict[str, Any]:
        counts = Counter()
        total = 0
        for block in self.blocks.values():
            for inst in block.instructions:
                if inst.op != IROp.COMMENT:
                    counts[inst.op.value] += 1
                    total += 1
        return {
            "function": self.name,
            "instruction_count": total,
            "instruction_by_type": dict(sorted(counts.items())),
            "basic_blocks": len(self.blocks),
            "temporaries": len(self.temp_types),
            "max_stack_depth_estimate": self.stack_size,
        }


@dataclass
class IRProgram:
    functions: Dict[str, FunctionIR] = field(default_factory=dict)
    function_order: List[str] = field(default_factory=list)
    structs: Dict[str, Any] = field(default_factory=dict)

    def add_function(self, function_ir: FunctionIR) -> None:
        if function_ir.name not in self.functions:
            self.function_order.append(function_ir.name)
        self.functions[function_ir.name] = function_ir

    def to_text(self) -> str:
        lines = ["# Generated MiniCompiler IR", ""]
        for name in self.function_order:
            lines.append(self.functions[name].to_text())
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def to_json(self) -> str:
        data = {
            "format": "MiniCompiler IR",
            "functions": [self.functions[name].to_json() for name in self.function_order],
            "structs": self.structs,
            "statistics": self.statistics(),
        }
        return json.dumps(data, indent=2)

    def to_dot(self) -> str:
        lines = ["digraph CFG {", "  graph [rankdir=TB];", "  node [shape=box, fontname=Courier];"]
        colors = {
            "entry": "lightgreen",
            "exit": "lightgray",
            "then": "lightblue",
            "else": "mistyrose",
            "join": "khaki",
            "loop_header": "orange",
            "loop_body": "palegreen",
            "loop_exit": "lightgray",
            "block": "white",
        }
        for fname in self.function_order:
            function = self.functions[fname]
            lines.append(f"  subgraph cluster_{fname} {{")
            lines.append(f"    label=\"function {fname}\";")
            for label in function.block_order:
                block = function.blocks[label]
                body = "\\l".join(str(i).replace('"', "\\\"") for i in block.instructions) + "\\l"
                fill = colors.get(block.kind, "white")
                node_name = f"{fname}_{label}"
                lines.append(
                    f"    {node_name} [style=filled, fillcolor=\"{fill}\", "
                    f"label=\"{label}:\\l{body}\"] ;"
                )
            for src, dst in function.cfg().edges():
                lines.append(f"    {fname}_{src} -> {fname}_{dst};")
            lines.append("  }")
        lines.append("}")
        return "\n".join(lines) + "\n"

    def statistics(self) -> Dict[str, Any]:
        functions = [self.functions[name].statistics() for name in self.function_order]
        total_by_type = Counter()
        for stat in functions:
            total_by_type.update(stat["instruction_by_type"])
        return {
            "functions": functions,
            "total_functions": len(functions),
            "total_basic_blocks": sum(s["basic_blocks"] for s in functions),
            "total_instructions": sum(s["instruction_count"] for s in functions),
            "total_temporaries": sum(s["temporaries"] for s in functions),
            "max_stack_depth_estimate": max((s["max_stack_depth_estimate"] for s in functions), default=0),
            "instruction_by_type": dict(sorted(total_by_type.items())),
        }

    def statistics_text(self) -> str:
        stats = self.statistics()
        lines = ["IR statistics:"]
        lines.append(f"  functions: {stats['total_functions']}")
        lines.append(f"  basic blocks: {stats['total_basic_blocks']}")
        lines.append(f"  instructions: {stats['total_instructions']}")
        lines.append(f"  temporaries: {stats['total_temporaries']}")
        lines.append(f"  max stack depth estimate: {stats['max_stack_depth_estimate']}")
        lines.append("  instruction counts:")
        for op, count in stats["instruction_by_type"].items():
            lines.append(f"    {op}: {count}")
        return "\n".join(lines)


class IRGenerator:
    """Decorated AST -> three-address IR.

    The constructor keeps the required Sprint 4 shape:
    IRGenerator(symbol_table, type_system). Both parameters are optional because
    most data is already stored on the decorated AST by SemanticAnalyzer.
    """

    def __init__(self, symbol_table=None, type_system=None):
        self.symbol_table = symbol_table
        self.type_system = type_system
        self.program = IRProgram()
        self.current_function: Optional[FunctionIR] = None
        self.current_block: Optional[BasicBlock] = None
        self.temp_counter = 0
        self.label_counter = 0
        self.var_counter = 0
        self.scope_stack: List[Dict[str, VariableSlot]] = []
        self.assigned_stack: List[Set[str]] = []

    def generate(self, ast: ProgramNode) -> IRProgram:
        self.program = IRProgram()
        for decl in ast.declarations:
            if isinstance(decl, StructDeclNode):
                self.program.structs[decl.name] = [
                    {"name": f.name, "type": f.var_type} for f in decl.fields
                ]
        for decl in ast.declarations:
            if isinstance(decl, FunctionDeclNode):
                self.visit_function_decl(decl)
        return self.program

    def get_function_ir(self, name: str) -> Optional[FunctionIR]:
        return self.program.functions.get(name)

    def get_all_ir(self) -> IRProgram:
        return self.program

    # --- Function and block helpers ---

    def _new_temp(self, type_name: Optional[str] = None) -> IROperand:
        self.temp_counter += 1
        name = f"t{self.temp_counter}"
        if self.current_function:
            self.current_function.temp_types[name] = type_name or "unknown"
        return IROperand.temp(name, type_name)

    def _new_label(self, prefix: str = "L") -> str:
        self.label_counter += 1
        return f"{prefix}{self.label_counter}"

    def _emit(self, opcode: IROp, dest: Optional[IROperand] = None, args: Optional[List[IROperand]] = None,
              comment: Optional[str] = None, type_name: Optional[str] = None, source_line: Optional[int] = None,
              metadata: Optional[Dict[str, Any]] = None) -> IRInstruction:
        if self.current_block is None:
            raise RuntimeError("No current basic block for IR emission.")
        inst = IRInstruction(opcode, dest, args or [], comment, type_name, source_line, metadata or {})
        self.current_block.add_instruction(inst)
        return inst

    def _start_block(self, label: str, kind: str = "block") -> BasicBlock:
        if self.current_function is None:
            raise RuntimeError("No current function.")
        block = self.current_function.add_block(BasicBlock(label, kind))
        self.current_block = block
        return block

    def _jump_to(self, label: str) -> None:
        if self.current_block and not self.current_block.has_terminator():
            self._emit(IROp.JUMP, args=[IROperand.label(label)])

    def _type_name(self, value: Any) -> str:
        if value is None:
            return "void"
        if hasattr(value, "inferred_type"):
            return str(value.inferred_type)
        if hasattr(value, "var_type"):
            return str(value.var_type)
        if hasattr(value, "param_type"):
            return str(value.param_type)
        if isinstance(value, bool):
            return "bool"
        if isinstance(value, int):
            return "int"
        if isinstance(value, float):
            return "float"
        if isinstance(value, str):
            return "string"
        return "unknown"

    def _type_size(self, type_name: str) -> int:
        from codegen.abi import size_of
        if str(type_name).startswith("struct"):
            return 8
        return size_of(str(type_name))

    # --- Scope and variables ---

    def _enter_scope(self) -> None:
        self.scope_stack.append({})

    def _exit_scope(self) -> None:
        self.scope_stack.pop()

    def _declare_variable(self, source_name: str, type_name: str, source_line: Optional[int] = None) -> VariableSlot:
        if self.current_function is None:
            raise RuntimeError("No current function.")
        if not self.scope_stack:
            self._enter_scope()

        self.var_counter += 1
        offset = self.current_function.stack_size
        size = self._type_size(type_name)
        self.current_function.stack_size += size
        ir_name = f"{source_name}_{self.var_counter - 1}"
        slot = VariableSlot(source_name, ir_name, type_name, offset)
        self.scope_stack[-1][source_name] = slot
        self.current_function.variables[ir_name] = slot
        self._emit(
            IROp.ALLOCA,
            dest=IROperand.var(ir_name, type_name),
            args=[IROperand.literal(size, "int")],
            comment=f"allocate {source_name}: {type_name}",
            type_name=type_name,
            source_line=source_line,
        )
        return slot

    def _lookup_variable(self, name: str) -> Optional[VariableSlot]:
        for scope in reversed(self.scope_stack):
            if name in scope:
                return scope[name]
        return None

    def _mark_assigned(self, name: str) -> None:
        if self.assigned_stack:
            self.assigned_stack[-1].add(name)

    def _collect_assigned(self, callback) -> Set[str]:
        self.assigned_stack.append(set())
        callback()
        return self.assigned_stack.pop()

    # --- Visitors for declarations/statements ---

    def visit_function_decl(self, node: FunctionDeclNode) -> None:
        self.temp_counter = 0
        self.label_counter = 0
        self.var_counter = 0
        params = [(p.param_type, p.name) for p in node.params]
        function = FunctionIR(node.name, node.return_type, params)
        self.current_function = function
        self.current_block = None
        self.scope_stack = []
        self.assigned_stack = []

        self.program.add_function(function)
        self._start_block("entry", "entry")
        self._enter_scope()

        for p in node.params:
            slot = self._declare_variable(p.name, p.param_type, p.line)
            self._emit(
                IROp.STORE,
                args=[slot.memory, IROperand.var(p.name, p.param_type)],
                comment=f"parameter {p.name}",
                source_line=p.line,
            )

        node.body.accept(self)

        if self.current_block and not self.current_block.has_terminator():
            if node.return_type == "void":
                self._emit(IROp.RETURN, comment="implicit void return")
            else:
                self._emit(IROp.RETURN, args=[IROperand.literal(0, "int")], comment="implicit fallback return")

        self._exit_scope()
        function.cfg().rebuild_edges()
        self.current_function = None
        self.current_block = None

    def visit_struct_decl(self, node: StructDeclNode) -> None:
        return None

    def visit_var_decl(self, node: VarDeclNode) -> None:
        type_name = node.var_type
        if getattr(node, "array_dimensions", None):
            type_name = node.var_type + "".join(f"[{d}]" for d in node.array_dimensions if d is not None)
        slot = self._declare_variable(node.name, type_name, node.line)
        if isinstance(node.initializer, list):
            elem_size = self._type_size(node.var_type)
            for index, init_expr in enumerate(node.initializer):
                value = init_expr.accept(self)
                self._emit(
                    IROp.STORE,
                    args=[IROperand.memory(f"{slot.ir_name}+{index * elem_size}", node.var_type), value],
                    comment=f"{node.name}[{index}] = initializer",
                    source_line=node.line,
                )
            if node.initializer:
                self._mark_assigned(node.name)
        elif node.initializer is not None:
            value = node.initializer.accept(self)
            self._emit(IROp.STORE, args=[slot.memory, value], comment=f"{node.name} = initializer", source_line=node.line)
            self._mark_assigned(node.name)

    def visit_block(self, node: BlockNode) -> None:
        self._enter_scope()
        for stmt in node.statements:
            if stmt is not None:
                stmt.accept(self)
        self._exit_scope()

    def visit_expr_stmt(self, node: ExprStmtNode) -> None:
        node.expr.accept(self)

    def visit_if_stmt(self, node: IfStmtNode) -> None:
        cond = node.condition.accept(self)
        then_label = self._new_label("L_then")
        else_label = self._new_label("L_else") if node.else_branch else None
        end_label = self._new_label("L_endif")

        false_target = else_label or end_label
        self._emit(IROp.JUMP_IF, args=[cond, IROperand.label(then_label)], comment="if condition true", source_line=node.line)
        self._emit(IROp.JUMP, args=[IROperand.label(false_target)], comment="if condition false", source_line=node.line)

        self._start_block(then_label, "then")
        then_assigned = self._collect_assigned(lambda: node.then_branch.accept(self))
        self._jump_to(end_label)

        else_assigned: Set[str] = set()
        if node.else_branch:
            self._start_block(else_label, "else")
            else_assigned = self._collect_assigned(lambda: node.else_branch.accept(self))
            self._jump_to(end_label)

        self._start_block(end_label, "join")
        merged = then_assigned | else_assigned
        for name in sorted(merged):
            slot = self._lookup_variable(name)
            type_name = slot.type_name if slot else "unknown"
            temp = self._new_temp(type_name)
            incoming = [IROperand.literal(f"{name}@{then_label}")]
            if node.else_branch:
                incoming.append(IROperand.literal(f"{name}@{else_label}"))
            else:
                incoming.append(IROperand.literal(f"{name}@entry"))
            self._emit(IROp.PHI, dest=temp, args=incoming, comment=f"merge possible values of {name}", type_name=type_name)

    def visit_while_stmt(self, node: WhileStmtNode) -> None:
        header_label = self._new_label("L_loop_header")
        body_label = self._new_label("L_loop_body")
        exit_label = self._new_label("L_loop_exit")

        self._jump_to(header_label)
        self._start_block(header_label, "loop_header")
        cond = node.condition.accept(self)
        self._emit(IROp.JUMP_IF, args=[cond, IROperand.label(body_label)], comment="while condition true", source_line=node.line)
        self._emit(IROp.JUMP, args=[IROperand.label(exit_label)], comment="while condition false", source_line=node.line)

        self._start_block(body_label, "loop_body")
        assigned = self._collect_assigned(lambda: node.body.accept(self))
        self._jump_to(header_label)

        self._start_block(exit_label, "loop_exit")
        for name in sorted(assigned):
            slot = self._lookup_variable(name)
            type_name = slot.type_name if slot else "unknown"
            temp = self._new_temp(type_name)
            self._emit(
                IROp.PHI,
                dest=temp,
                args=[IROperand.literal(f"{name}@entry"), IROperand.literal(f"{name}@{body_label}")],
                comment=f"merge loop-carried value of {name}",
                type_name=type_name,
            )

    def visit_for_stmt(self, node: ForStmtNode) -> None:
        self._enter_scope()
        if node.init:
            node.init.accept(self)

        header_label = self._new_label("L_for_header")
        body_label = self._new_label("L_for_body")
        update_label = self._new_label("L_for_update")
        exit_label = self._new_label("L_for_exit")

        self._jump_to(header_label)
        self._start_block(header_label, "loop_header")
        if node.condition:
            cond = node.condition.accept(self)
        else:
            cond = IROperand.literal(True, "bool")
        self._emit(IROp.JUMP_IF, args=[cond, IROperand.label(body_label)], comment="for condition true", source_line=node.line)
        self._emit(IROp.JUMP, args=[IROperand.label(exit_label)], comment="for condition false", source_line=node.line)

        self._start_block(body_label, "loop_body")
        body_assigned = self._collect_assigned(lambda: node.body.accept(self))
        self._jump_to(update_label)

        self._start_block(update_label, "block")
        update_assigned: Set[str] = set()
        if node.update:
            update_assigned = self._collect_assigned(lambda: node.update.accept(self))
        self._jump_to(header_label)

        self._start_block(exit_label, "loop_exit")
        for name in sorted(body_assigned | update_assigned):
            slot = self._lookup_variable(name)
            type_name = slot.type_name if slot else "unknown"
            temp = self._new_temp(type_name)
            self._emit(
                IROp.PHI,
                dest=temp,
                args=[IROperand.literal(f"{name}@entry"), IROperand.literal(f"{name}@{body_label}"), IROperand.literal(f"{name}@{update_label}")],
                comment=f"merge for-loop value of {name}",
                type_name=type_name,
            )
        self._exit_scope()

    def visit_return_stmt(self, node: ReturnStmtNode) -> None:
        if node.value is None:
            self._emit(IROp.RETURN, comment="return void", source_line=node.line)
        else:
            value = node.value.accept(self)
            self._emit(IROp.RETURN, args=[value], comment="return value", source_line=node.line)

    # --- Visitors for expressions ---

    def visit_literal_expr(self, node: LiteralExprNode) -> IROperand:
        return IROperand.literal(node.value, self._type_name(node.value))

    def visit_identifier_expr(self, node: IdentifierExprNode) -> IROperand:
        slot = self._lookup_variable(node.name)
        if slot is None:
            # Functions can appear as identifiers in CallExprNode. Unknown names stay symbolic.
            return IROperand.var(node.name, self._type_name(node))
        temp = self._new_temp(slot.type_name)
        self._emit(IROp.LOAD, dest=temp, args=[slot.memory], comment=f"load {node.name}", type_name=slot.type_name, source_line=node.line)
        return temp

    def _address_of(self, node) -> IROperand:
        if isinstance(node, IdentifierExprNode):
            slot = self._lookup_variable(node.name)
            if slot is not None:
                return slot.memory
            return IROperand.memory(node.name)
        if isinstance(node, ArrayAccessExprNode):
            return self._array_element_address(node)
        if isinstance(node, BinaryExprNode) and node.operator == ".":
            base_addr = self._address_of(node.left) if isinstance(node.left, (IdentifierExprNode, BinaryExprNode, ArrayAccessExprNode)) else node.left.accept(self)
            field = node.right.name if isinstance(node.right, IdentifierExprNode) else "field"
            addr = self._new_temp("ptr")
            self._emit(IROp.GEP, dest=addr, args=[base_addr, IROperand.literal(field)], comment=f"address of field {field}", source_line=node.line)
            return IROperand.memory(f"*{addr.value}")
        raise RuntimeError("Unsupported assignment target.")

    def _array_element_address(self, node: ArrayAccessExprNode) -> IROperand:
        # Arrays are lowered as base pointer + index * element_size.
        base = node.array
        index = node.index.accept(self)
        elem_type = self._type_name(node) or "int"
        elem_size = self._type_size(elem_type)
        if isinstance(base, IdentifierExprNode):
            slot = self._lookup_variable(base.name)
            base_op = slot.memory if slot else IROperand.memory(base.name)
        else:
            base_op = base.accept(self)
        addr = self._new_temp("ptr")
        self._emit(
            IROp.GEP,
            dest=addr,
            args=[base_op, index, IROperand.literal(elem_size, "int")],
            comment="array element address",
            type_name="ptr",
            source_line=node.line,
        )
        return IROperand.memory(f"*{addr.value}", elem_type)

    def visit_array_access_expr(self, node: ArrayAccessExprNode) -> IROperand:
        addr = self._array_element_address(node)
        temp = self._new_temp(self._type_name(node))
        self._emit(IROp.LOAD, dest=temp, args=[addr], comment="array element load", type_name=temp.type_name, source_line=node.line)
        return temp

    def visit_binary_expr(self, node: BinaryExprNode) -> IROperand:
        if node.operator == ".":
            addr = self._address_of(node)
            temp = self._new_temp(self._type_name(node))
            self._emit(
                IROp.LOAD,
                dest=temp,
                args=[addr],
                comment="field access",
                type_name=temp.type_name,
                source_line=node.line,
            )
            return temp

        # Sprint 6: real short-circuit evaluation.
        # Important: do NOT evaluate node.right before deciding from node.left.
        if node.operator in ("&&", "||"):
            return self._emit_short_circuit_logical(node)

        left = node.left.accept(self)
        right = node.right.accept(self)

        op_map = {
            "+": IROp.ADD,
            "-": IROp.SUB,
            "*": IROp.MUL,
            "/": IROp.DIV,
            "%": IROp.MOD,
            "==": IROp.CMP_EQ,
            "!=": IROp.CMP_NE,
            "<": IROp.CMP_LT,
            "<=": IROp.CMP_LE,
            ">": IROp.CMP_GT,
            ">=": IROp.CMP_GE,
        }

        opcode = op_map[node.operator]
        result_type = self._type_name(node)
        dest = self._new_temp(result_type)

        self._emit(
            opcode,
            dest=dest,
            args=[left, right],
            comment=f"{node.operator} expression",
            type_name=result_type,
            source_line=node.line,
        )

        return dest

    def _emit_short_circuit_logical(self, node: BinaryExprNode) -> IROperand:
        result = self._new_temp("bool")

        rhs_label = self._new_label("L_logic_rhs")
        true_label = self._new_label("L_logic_true")
        false_label = self._new_label("L_logic_false")
        end_label = self._new_label("L_logic_end")

        left = node.left.accept(self)

        if node.operator == "&&":
            # false && anything -> false, right side is skipped
            self._emit(
                IROp.JUMP_IF,
                args=[left, IROperand.label(rhs_label)],
                comment="&& left true: evaluate right",
                source_line=node.line,
            )
            self._emit(
                IROp.JUMP,
                args=[IROperand.label(false_label)],
                comment="&& short-circuit false",
                source_line=node.line,
            )

        elif node.operator == "||":
            # true || anything -> true, right side is skipped
            self._emit(
                IROp.JUMP_IF,
                args=[left, IROperand.label(true_label)],
                comment="|| short-circuit true",
                source_line=node.line,
            )
            self._emit(
                IROp.JUMP,
                args=[IROperand.label(rhs_label)],
                comment="|| left false: evaluate right",
                source_line=node.line,
            )

        self._start_block(rhs_label, "block")
        right = node.right.accept(self)
        self._emit(
            IROp.JUMP_IF,
            args=[right, IROperand.label(true_label)],
            comment=f"{node.operator} right true",
            source_line=node.line,
        )
        self._emit(
            IROp.JUMP,
            args=[IROperand.label(false_label)],
            comment=f"{node.operator} right false",
            source_line=node.line,
        )

        self._start_block(true_label, "block")
        self._emit(
            IROp.MOVE,
            dest=result,
            args=[IROperand.literal(True, "bool")],
            comment=f"{node.operator} result true",
            type_name="bool",
            source_line=node.line,
        )
        self._jump_to(end_label)

        self._start_block(false_label, "block")
        self._emit(
            IROp.MOVE,
            dest=result,
            args=[IROperand.literal(False, "bool")],
            comment=f"{node.operator} result false",
            type_name="bool",
            source_line=node.line,
        )
        self._jump_to(end_label)

        self._start_block(end_label, "join")
        return result

    def _emit_short_circuit_expr(self, node: BinaryExprNode) -> IROperand:
        """Lower && and || with real short-circuit control flow.

        The right operand is emitted only in the RHS basic block, so dangerous
        expressions such as `a != 0 && b / a > 2` do not evaluate `b / a`
        when the left operand already determines the result.
        """
        result = self._new_temp("bool")
        rhs_label = self._new_label("L_logic_rhs")
        true_label = self._new_label("L_logic_true")
        false_label = self._new_label("L_logic_false")
        end_label = self._new_label("L_logic_end")

        left = node.left.accept(self)
        if node.operator == "&&":
            self._emit(IROp.JUMP_IF, args=[left, IROperand.label(rhs_label)], comment="&& left true: evaluate right", source_line=node.line)
            self._emit(IROp.JUMP, args=[IROperand.label(false_label)], comment="&& short-circuit false", source_line=node.line)
        else:
            self._emit(IROp.JUMP_IF, args=[left, IROperand.label(true_label)], comment="|| short-circuit true", source_line=node.line)
            self._emit(IROp.JUMP, args=[IROperand.label(rhs_label)], comment="|| left false: evaluate right", source_line=node.line)

        self._start_block(rhs_label, "block")
        right = node.right.accept(self)
        self._emit(IROp.JUMP_IF, args=[right, IROperand.label(true_label)], comment=f"{node.operator} right true", source_line=node.line)
        self._emit(IROp.JUMP, args=[IROperand.label(false_label)], comment=f"{node.operator} right false", source_line=node.line)

        self._start_block(true_label, "block")
        self._emit(IROp.MOVE, dest=result, args=[IROperand.literal(True, "bool")], comment=f"{node.operator} result true", type_name="bool", source_line=node.line)
        self._jump_to(end_label)

        self._start_block(false_label, "block")
        self._emit(IROp.MOVE, dest=result, args=[IROperand.literal(False, "bool")], comment=f"{node.operator} result false", type_name="bool", source_line=node.line)
        self._jump_to(end_label)

        self._start_block(end_label, "join")
        return result

    def visit_unary_expr(self, node: UnaryExprNode) -> IROperand:
        operand = node.right.accept(self)
        opcode = IROp.NEG if node.operator == "-" else IROp.NOT
        result_type = self._type_name(node)
        dest = self._new_temp(result_type)
        self._emit(opcode, dest=dest, args=[operand], comment=f"unary {node.operator}", type_name=result_type, source_line=node.line)
        return dest

    def visit_call_expr(self, node: CallExprNode) -> IROperand:
        arg_values = [arg.accept(self) for arg in node.arguments]

        for idx, arg in enumerate(arg_values):
            self._emit(
                IROp.PARAM,
                args=[IROperand.literal(idx, "int"), arg],
                comment=f"argument {idx}",
                source_line=node.line,
            )

        func_name = node.callee.name if isinstance(node.callee, IdentifierExprNode) else str(node.callee)
        result_type = self._type_name(node)
        dest = None if result_type == "void" else self._new_temp(result_type)

        # Важно для Sprint 4 golden tests:
        # аргументы уже переданы отдельными PARAM-инструкциями,
        # поэтому CALL хранит только имя функции и количество аргументов.
        args = [
            IROperand.function(func_name),
            IROperand.literal(len(arg_values), "int"),
        ]

        self._emit(
            IROp.CALL,
            dest=dest,
            args=args,
            comment=f"call {func_name}",
            type_name=result_type,
            source_line=node.line,
        )

        return dest or IROperand.literal(None, "void")

    def visit_assignment_expr(self, node: AssignmentExprNode) -> IROperand:
        if not isinstance(node.target, (IdentifierExprNode, BinaryExprNode, ArrayAccessExprNode)):
            raise RuntimeError("Invalid assignment target in IR generation.")

        if node.operator == "=":
            value = node.value.accept(self)
        else:
            current = node.target.accept(self)
            rhs = node.value.accept(self)
            op_map = {
                "+=": IROp.ADD,
                "-=": IROp.SUB,
                "*=": IROp.MUL,
                "/=": IROp.DIV,
                "%=": IROp.MOD,
            }
            value = self._new_temp(self._type_name(node))
            self._emit(op_map[node.operator], dest=value, args=[current, rhs], comment=f"compound assignment {node.operator}", source_line=node.line)

        address = self._address_of(node.target)
        target_name = node.target.name if isinstance(node.target, IdentifierExprNode) else "element"
        self._emit(IROp.STORE, args=[address, value], comment=f"assign {target_name}", source_line=node.line)
        if isinstance(node.target, IdentifierExprNode):
            self._mark_assigned(node.target.name)
        return value
