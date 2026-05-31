"""Stack frame layout for x86-64 code generation."""
from dataclasses import dataclass
from typing import Dict, Iterable, Optional

from .abi import align_to, size_of


@dataclass
class StackSlot:
    name: str
    type_name: str
    offset: int
    size: int
    source_name: Optional[str] = None

    @property
    def address(self) -> str:
        return f"[rbp-{self.offset}]"


class StackFrame:
    """Assigns fixed negative RBP offsets to variables and temporaries."""

    def __init__(self, function_name: str):
        self.function_name = function_name
        self.slots: Dict[str, StackSlot] = {}
        self._next_offset = 0

    def add_slot(self, name: str, type_name: str = "int", source_name: Optional[str] = None) -> StackSlot:
        if name in self.slots:
            return self.slots[name]
        size = max(size_of(type_name), 4)  # keep integer temporaries addressable as dword
        self._next_offset += size
        # natural alignment, capped to 8 for this simple backend
        align = min(max(size, 1), 8)
        self._next_offset = align_to(self._next_offset, align)
        slot = StackSlot(name=name, type_name=type_name or "int", offset=self._next_offset, size=size, source_name=source_name)
        self.slots[name] = slot
        return slot

    def get(self, name: str) -> Optional[StackSlot]:
        return self.slots.get(name)

    def require(self, name: str, type_name: str = "int") -> StackSlot:
        return self.slots.get(name) or self.add_slot(name, type_name)

    @property
    def stack_size(self) -> int:
        return align_to(self._next_offset, 16)

    def __iter__(self) -> Iterable[StackSlot]:
        return iter(self.slots.values())
