"""Assembly label helpers for Sprint 6 control-flow code generation."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable


_SAFE = re.compile(r"[^A-Za-z0-9_$]")


def sanitize_label(text: str) -> str:
    value = _SAFE.sub("_", str(text))
    if not value or value[0].isdigit():
        value = f"L_{value}"
    return value


@dataclass
class LabelManager:
    """Creates stable, conflict-free local labels for each function."""

    function_name: str
    mapping: Dict[str, str] = field(default_factory=dict)

    def map_basic_blocks(self, labels: Iterable[str]) -> Dict[str, str]:
        self.mapping = {
            label: f".LBB_{sanitize_label(self.function_name)}_{index}_{sanitize_label(label)}"
            for index, label in enumerate(labels)
        }
        return self.mapping

    def label(self, ir_label: str) -> str:
        return self.mapping.get(str(ir_label), str(ir_label))
