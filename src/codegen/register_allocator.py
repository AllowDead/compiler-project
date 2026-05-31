"""Small fixed-register helper used by the Sprint 5 backend.

This is intentionally simple. It keeps arithmetic in eax/ecx/edx and spills IR
variables/temporaries to stack slots, which is predictable and easy to test.
"""
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class RegisterAllocator:
    temp_registers: tuple[str, ...] = ("eax", "ecx", "edx", "r10d", "r11d")
    assigned: Dict[str, str] = field(default_factory=dict)
    spill_count: int = 0

    def preferred_accumulator(self) -> str:
        return "eax"

    def scratch(self) -> str:
        return "ecx"

    def record_spill(self, name: str) -> None:
        self.spill_count += 1
        self.assigned[name] = "stack"

    def statistics(self) -> Dict[str, int]:
        return {
            "registers_available": len(self.temp_registers),
            "spills": self.spill_count,
            "stack_assigned_values": sum(1 for value in self.assigned.values() if value == "stack"),
        }
