from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .basic_block import BasicBlock
from .ir_instructions import IROp


@dataclass
class CFGValidationResult:
    ok: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class ControlFlowGraph:
    def __init__(self, blocks: Dict[str, BasicBlock], entry_label: str = "entry"):
        self.blocks = blocks
        self.entry_label = entry_label

    def rebuild_edges(self) -> None:
        for block in self.blocks.values():
            block.predecessors.clear()
            block.successors.clear()

        for label, block in self.blocks.items():
            for inst in block.instructions:
                for target in inst.target_labels():
                    if target in self.blocks:
                        block.add_successor(target)
                        self.blocks[target].add_predecessor(label)

    def validate(self) -> CFGValidationResult:
        self.rebuild_edges()
        errors: List[str] = []
        warnings: List[str] = []
        labels = set(self.blocks.keys())

        if self.entry_label not in labels:
            errors.append(f"Missing entry block '{self.entry_label}'.")

        for label, block in self.blocks.items():
            if not block.instructions:
                warnings.append(f"Block '{label}' is empty.")
                continue

            if not block.has_terminator():
                warnings.append(f"Block '{label}' does not end with a control-flow instruction.")

            for inst in block.instructions:
                for target in inst.target_labels():
                    if target not in labels:
                        errors.append(f"Instruction in block '{label}' jumps to undefined label '{target}'.")

        reachable = self._reachable_labels()
        for label in labels - reachable:
            warnings.append(f"Block '{label}' is unreachable from entry.")

        return CFGValidationResult(not errors, errors, warnings)

    def edges(self) -> List[Tuple[str, str]]:
        self.rebuild_edges()
        return [(src, dst) for src, block in self.blocks.items() for dst in block.successors]

    def _reachable_labels(self) -> set[str]:
        if self.entry_label not in self.blocks:
            return set()
        self.rebuild_edges()
        seen = set()
        stack = [self.entry_label]
        while stack:
            label = stack.pop()
            if label in seen:
                continue
            seen.add(label)
            stack.extend(self.blocks[label].successors)
        return seen
