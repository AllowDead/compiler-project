from enum import Enum, auto


class TypeEnum(Enum):
    INT = auto()
    FLOAT = auto()
    BOOL = auto()
    VOID = auto()
    STRING = auto()
    STRUCT = auto()
    FUNCTION = auto()
    POINTER = auto()
    ARRAY = auto()
    ERROR = auto()


class Type:
    def __init__(self, type_enum: TypeEnum):
        self.type_enum = type_enum

    @property
    def size(self) -> int:
        return 0

    @property
    def alignment(self) -> int:
        return 1

    def is_assignable_to(self, target_type: 'Type') -> bool:
        if target_type is None:
            return False
        if target_type.type_enum == TypeEnum.ERROR or self.type_enum == TypeEnum.ERROR:
            return True
        if self.type_enum == TypeEnum.INT and target_type.type_enum == TypeEnum.FLOAT:
            return True
        if self.type_enum == TypeEnum.ARRAY and target_type.type_enum == TypeEnum.POINTER:
            return self.element_type.is_assignable_to(target_type.pointee)
        if self.type_enum == TypeEnum.POINTER and target_type.type_enum == TypeEnum.POINTER:
            return self.pointee.is_assignable_to(target_type.pointee) or target_type.pointee.type_enum == TypeEnum.VOID
        return self.type_enum == target_type.type_enum

    def __repr__(self):
        return self.type_enum.name.lower()


class BaseType(Type):
    PROPS = {
        TypeEnum.INT: (4, 4),
        TypeEnum.FLOAT: (4, 4),
        TypeEnum.BOOL: (1, 1),
        TypeEnum.VOID: (0, 1),
        TypeEnum.STRING: (8, 8),
        TypeEnum.ERROR: (0, 1),
    }

    def __init__(self, type_enum: TypeEnum):
        super().__init__(type_enum)
        self._size, self._align = self.PROPS.get(type_enum, (0, 1))

    @property
    def size(self) -> int:
        return self._size

    @property
    def alignment(self) -> int:
        return self._align


INT_TYPE = BaseType(TypeEnum.INT)
FLOAT_TYPE = BaseType(TypeEnum.FLOAT)
BOOL_TYPE = BaseType(TypeEnum.BOOL)
VOID_TYPE = BaseType(TypeEnum.VOID)
STRING_TYPE = BaseType(TypeEnum.STRING)
ERROR_TYPE = BaseType(TypeEnum.ERROR)


class PointerType(Type):
    def __init__(self, pointee: Type):
        super().__init__(TypeEnum.POINTER)
        self.pointee = pointee

    @property
    def size(self) -> int:
        return 8

    @property
    def alignment(self) -> int:
        return 8

    def __repr__(self):
        return f"{self.pointee}*"


class ArrayType(Type):
    def __init__(self, element_type: Type, dimensions: list[int]):
        super().__init__(TypeEnum.ARRAY)
        self.element_type = element_type
        self.dimensions = list(dimensions)

    @property
    def size(self) -> int:
        total = self.element_type.size
        for dim in self.dimensions:
            total *= int(dim)
        return total

    @property
    def alignment(self) -> int:
        return self.element_type.alignment

    def decay_to_pointer(self) -> PointerType:
        return PointerType(self.element_type)

    def __repr__(self):
        return f"{self.element_type}" + "".join(f"[{d}]" for d in self.dimensions)


class StructType(Type):
    def __init__(self, name: str, fields: dict):
        super().__init__(TypeEnum.STRUCT)
        self.name = name
        self.fields = fields
        self._size = 0
        self._align = 1
        for f_type in fields.values():
            self._align = max(self._align, f_type.alignment)
            if self._size % f_type.alignment != 0:
                self._size += f_type.alignment - (self._size % f_type.alignment)
            self._size += f_type.size
        if self._size % self._align != 0:
            self._size += self._align - (self._size % self._align)

    @property
    def size(self) -> int:
        return self._size

    @property
    def alignment(self) -> int:
        return self._align

    def __repr__(self):
        return f"struct {self.name} (size={self._size})"


class FunctionType(Type):
    def __init__(self, return_type: Type, param_types: list, variadic: bool = False, external: bool = False):
        super().__init__(TypeEnum.FUNCTION)
        self.return_type = return_type
        self.param_types = param_types
        self.variadic = variadic
        self.external = external

    def __repr__(self):
        suffix = ", ..." if self.variadic else ""
        return f"({', '.join(map(str, self.param_types))}{suffix}) -> {self.return_type}"


def pointer_to(base: Type) -> PointerType:
    return PointerType(base)


def type_to_ir_name(t: Type) -> str:
    if t.type_enum == TypeEnum.ARRAY:
        return repr(t)
    if t.type_enum == TypeEnum.POINTER:
        return repr(t)
    return repr(t)
