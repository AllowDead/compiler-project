from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from .ir_instructions import IRInstruction, IROp


@dataclass
class BasicBlock:
    label: str
    kind: str = "block"
    instructions: List[IRInstruction] = field(default_factory=list)
    predecessors: List[str] = field(default_factory=list)
    successors: List[str] = field(default_factory=list)

    def add_instruction(self, instruction: IRInstruction) -> IRInstruction:
        self.instructions.append(instruction)
        return instruction

    def has_terminator(self) -> bool:
        return bool(self.instructions and self.instructions[-1].is_terminator())

    def add_successor(self, label: str) -> None:
        if label not in self.successors:
            self.successors.append(label)

    def add_predecessor(self, label: str) -> None:
        if label not in self.predecessors:
            self.predecessors.append(label)

    def to_json(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "kind": self.kind,
            "instructions": [i.to_json() for i in self.instructions],
            "predecessors": self.predecessors,
            "successors": self.successors,
        }

    def to_text(self, indent: str = "  ") -> str:
        lines = [f"{indent}# Basic block: {self.kind}", f"{indent}{self.label}:"]
        if not self.instructions:
            lines.append(f"{indent}  # empty")
        else:
            for inst in self.instructions:
                lines.append(f"{indent}  {inst}")
        return "\n".join(lines)
