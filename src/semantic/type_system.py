from enum import Enum, auto


class TypeEnum(Enum):
    INT = auto()
    FLOAT = auto()
    BOOL = auto()
    VOID = auto()
    STRING = auto()
    STRUCT = auto()
    FUNCTION = auto()
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
        if target_type.type_enum == TypeEnum.ERROR or self.type_enum == TypeEnum.ERROR:
            return True
        if self.type_enum == TypeEnum.INT and target_type.type_enum == TypeEnum.FLOAT:
            return True
        return self.type_enum == target_type.type_enum

    def __repr__(self):
        return self.type_enum.name.lower()


class BaseType(Type):
    # Словарь: тип -> (размер в байтах, выравнивание)
    PROPS = {
        TypeEnum.INT: (4, 4),
        TypeEnum.FLOAT: (4, 4),
        TypeEnum.BOOL: (1, 1),
        TypeEnum.VOID: (0, 1),
        TypeEnum.STRING: (8, 8),  # Указатель на строку (для упрощения)
    }

    def __init__(self, type_enum: TypeEnum):
        super().__init__(type_enum)
        self._size, self._align = self.PROPS.get(type_enum, (0, 1))

    @property
    def size(self) -> int: return self._size

    @property
    def alignment(self) -> int: return self._align


# Базовые синглтоны
INT_TYPE = BaseType(TypeEnum.INT)
FLOAT_TYPE = BaseType(TypeEnum.FLOAT)
BOOL_TYPE = BaseType(TypeEnum.BOOL)
VOID_TYPE = BaseType(TypeEnum.VOID)
STRING_TYPE = BaseType(TypeEnum.STRING)
ERROR_TYPE = BaseType(TypeEnum.ERROR)


class StructType(Type):
    def __init__(self, name: str, fields: dict):
        super().__init__(TypeEnum.STRUCT)
        self.name = name
        self.fields = fields
        self._size = 0
        self._align = 1

        # Вычисляем размер и выравнивание структуры на основе полей
        for f_type in fields.values():
            self._align = max(self._align, f_type.alignment)
            # Добавляем паддинг (выравнивание начала поля)
            if self._size % f_type.alignment != 0:
                self._size += f_type.alignment - (self._size % f_type.alignment)
            self._size += f_type.size

        # Выравниваем конец структуры до кратного выравниванию
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
    def __init__(self, return_type: Type, param_types: list):
        super().__init__(TypeEnum.FUNCTION)
        self.return_type = return_type
        self.param_types = param_types

    def __repr__(self): return f"({', '.join(map(str, self.param_types))}) -> {self.return_type}"