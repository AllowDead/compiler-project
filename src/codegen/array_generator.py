"""Sprint 7 array layout helpers."""
from dataclasses import dataclass
from functools import reduce
from operator import mul

@dataclass(frozen=True)
class ArrayLayout:
    element_type: str
    dimensions: list[int]
    element_size: int = 4

    @property
    def element_count(self) -> int:
        return reduce(mul, self.dimensions, 1)

    @property
    def total_size(self) -> int:
        return self.element_count * self.element_size

    def offset_for_indices(self, indices: list[int]) -> int:
        if len(indices) != len(self.dimensions):
            raise ValueError("wrong number of indices")
        linear = 0
        stride = 1
        for index, dim in zip(reversed(indices), reversed(self.dimensions)):
            if index < 0 or index >= dim:
                raise IndexError("array index out of bounds")
            linear += index * stride
            stride *= dim
        return linear * self.element_size
