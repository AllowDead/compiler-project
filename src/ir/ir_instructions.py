from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class IROp(str, Enum):
    # Arithmetic
    ADD = "ADD"
    SUB = "SUB"
    MUL = "MUL"
    DIV = "DIV"
    MOD = "MOD"
    NEG = "NEG"

    # Logical
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    XOR = "XOR"

    # Comparison
    CMP_EQ = "CMP_EQ"
    CMP_NE = "CMP_NE"
    CMP_LT = "CMP_LT"
    CMP_LE = "CMP_LE"
    CMP_GT = "CMP_GT"
    CMP_GE = "CMP_GE"

    # Memory
    LOAD = "LOAD"
    STORE = "STORE"
    ALLOCA = "ALLOCA"
    GEP = "GEP"

    # Control flow
    JUMP = "JUMP"
    JUMP_IF = "JUMP_IF"
    JUMP_IF_NOT = "JUMP_IF_NOT"
    LABEL = "LABEL"
    PHI = "PHI"

    # Function
    CALL = "CALL"
    RETURN = "RETURN"
    PARAM = "PARAM"

    # Data movement
    MOVE = "MOVE"
    COMMENT = "COMMENT"


TERMINATORS = {IROp.JUMP, IROp.JUMP_IF, IROp.JUMP_IF_NOT, IROp.RETURN}


@dataclass(frozen=True)
class IROperand:
    """Typed IR operand.

    kind: temp | var | literal | label | memory | function | type | raw
    """

    kind: str
    value: Any
    type_name: Optional[str] = None

    @staticmethod
    def temp(name: str, type_name: Optional[str] = None) -> "IROperand":
        return IROperand("temp", name, type_name)

    @staticmethod
    def var(name: str, type_name: Optional[str] = None) -> "IROperand":
        return IROperand("var", name, type_name)

    @staticmethod
    def literal(value: Any, type_name: Optional[str] = None) -> "IROperand":
        return IROperand("literal", value, type_name)

    @staticmethod
    def label(name: str) -> "IROperand":
        return IROperand("label", name)

    @staticmethod
    def memory(name: str, type_name: Optional[str] = None) -> "IROperand":
        return IROperand("memory", name, type_name)

    @staticmethod
    def function(name: str, type_name: Optional[str] = None) -> "IROperand":
        return IROperand("function", name, type_name)

    def to_json(self) -> Dict[str, Any]:
        return {"kind": self.kind, "value": self.value, "type": self.type_name}

    def __str__(self) -> str:
        if self.kind == "literal":
            if isinstance(self.value, bool):
                return "true" if self.value else "false"
            if isinstance(self.value, str):
                return f'"{self.value}"' if self.type_name == "string" else self.value
            return str(self.value)
        if self.kind == "memory":
            value = str(self.value)
            if value.startswith("[") and value.endswith("]"):
                return value
            return f"[{value}]"
        return str(self.value)


@dataclass
class IRInstruction:
    opcode: IROp | str
    dest: Optional[IROperand] = None
    args: List[IROperand] = field(default_factory=list)
    comment: Optional[str] = None
    type_name: Optional[str] = None
    source_line: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def op(self) -> IROp:
        return self.opcode if isinstance(self.opcode, IROp) else IROp(self.opcode)

    def is_terminator(self) -> bool:
        return self.op in TERMINATORS

    def target_labels(self) -> List[str]:
        if self.op == IROp.JUMP and self.args:
            return [str(self.args[0])]
        if self.op in (IROp.JUMP_IF, IROp.JUMP_IF_NOT) and len(self.args) >= 2:
            return [str(self.args[1])]
        return []

    def to_json(self) -> Dict[str, Any]:
        return {
            "opcode": self.op.value,
            "dest": self.dest.to_json() if self.dest else None,
            "args": [a.to_json() for a in self.args],
            "comment": self.comment,
            "type": self.type_name,
            "source_line": self.source_line,
            "metadata": self.metadata,
        }

    def __str__(self) -> str:
        op = self.op
        text = ""
        if op == IROp.COMMENT:
            text = f"# {self.comment or ''}"
        elif op == IROp.LABEL:
            text = f"LABEL {self.args[0]}" if self.args else "LABEL"
        elif op == IROp.STORE:
            text = f"STORE {self.args[0]}, {self.args[1]}"
        elif op == IROp.ALLOCA:
            text = f"{self.dest} = ALLOCA {', '.join(map(str, self.args))}"
        elif op == IROp.LOAD:
            text = f"{self.dest} = LOAD {self.args[0]}"
        elif op == IROp.GEP:
            text = f"{self.dest} = GEP {', '.join(map(str, self.args))}"
        elif op == IROp.JUMP:
            text = f"JUMP {self.args[0]}"
        elif op in (IROp.JUMP_IF, IROp.JUMP_IF_NOT):
            text = f"{op.value} {self.args[0]}, {self.args[1]}"
        elif op == IROp.RETURN:
            text = "RETURN" if not self.args else f"RETURN {self.args[0]}"
        elif op == IROp.PARAM:
            text = f"PARAM {self.args[0]}, {self.args[1]}"
        elif op == IROp.CALL:
            if self.dest:
                text = f"{self.dest} = CALL {', '.join(map(str, self.args))}"
            else:
                text = f"CALL {', '.join(map(str, self.args))}"
        elif op == IROp.PHI:
            text = f"{self.dest} = PHI {', '.join(map(str, self.args))}"
        elif op == IROp.MOVE:
            text = f"{self.dest} = MOVE {self.args[0]}"
        else:
            if self.dest:
                text = f"{self.dest} = {op.value} {', '.join(map(str, self.args))}"
            else:
                text = f"{op.value} {', '.join(map(str, self.args))}"

        if self.type_name:
            text += f"    ; type={self.type_name}"
        if self.comment and op != IROp.COMMENT:
            text += f"    # {self.comment}"
        return text
