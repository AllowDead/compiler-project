from enum import Enum, auto
from .type_system import Type

class SymbolKind(Enum):
    VARIABLE = auto()
    FUNCTION = auto()
    PARAMETER = auto()
    STRUCT = auto()

class Symbol:
    def __init__(self, name: str, type: Type, kind: SymbolKind, line: int, col: int, extra=None):
        self.name = name
        self.type = type
        self.kind = kind
        self.line = line
        self.col = col
        self.extra = extra # Для функций: список параметров, для структур: поля


class Scope:
    def __init__(self, name: str, parent=None):
        self.name = name
        self.symbols = {}
        self.parent = parent
        self.stack_offset = 0  # Смещение для следующей переменной

    def insert(self, symbol: Symbol):
        if symbol.kind in (SymbolKind.VARIABLE, SymbolKind.PARAMETER):
            # Вычисляем выравнивание (alignment)
            align = symbol.type.alignment
            if self.stack_offset % align != 0:
                self.stack_offset += align - (self.stack_offset % align)

            # Сохраняем смещение в символ
            symbol.stack_offset = self.stack_offset
            # Сдвигаем указатель стека на размер типа
            self.stack_offset += symbol.type.size

        self.symbols[symbol.name] = symbol

    def lookup(self, name: str) -> Symbol:
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def lookup_local(self, name: str) -> Symbol:
        return self.symbols.get(name)

class SymbolTable:
    def __init__(self):
        self.current_scope = Scope("global")

    def enter_scope(self, name: str):
        self.current_scope = Scope(name, self.current_scope)

    def exit_scope(self):
        self.current_scope = self.current_scope.parent

    def insert(self, symbol: Symbol):
        self.current_scope.insert(symbol)

    def lookup(self, name: str) -> Symbol:
        return self.current_scope.lookup(name)

    def lookup_local(self, name: str) -> Symbol:
        return self.current_scope.lookup_local(name)