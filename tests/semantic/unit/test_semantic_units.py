import pytest
import sys

sys.path.insert(0, 'src')
from semantic.type_system import *
from semantic.symbol_table import Symbol, SymbolTable, SymbolKind


# --- TEST-1: Type System ---

def test_int_assignable_to_float():
    assert INT_TYPE.is_assignable_to(FLOAT_TYPE) == True


def test_float_not_assignable_to_int():
    assert FLOAT_TYPE.is_assignable_to(INT_TYPE) == False


def test_bool_not_assignable_to_int():
    assert BOOL_TYPE.is_assignable_to(INT_TYPE) == False


def test_error_type_is_assignable_to_all():
    assert ERROR_TYPE.is_assignable_to(INT_TYPE) == True
    assert INT_TYPE.is_assignable_to(ERROR_TYPE) == True


def test_struct_size_and_padding():
    # struct Test { bool b; int x; }
    # bool(1) + padding(3) + int(4) = 8 байт
    fields = {"b": BOOL_TYPE, "x": INT_TYPE}
    test_struct = StructType("Test", fields)
    assert test_struct.size == 8
    assert test_struct.alignment == 4


# --- TEST-1: Symbol Table ---

def test_scope_insert_and_lookup():
    st = SymbolTable()
    st.enter_scope("global")
    sym = Symbol("x", INT_TYPE, SymbolKind.VARIABLE, 1, 1)
    st.insert(sym)
    assert st.lookup("x") == sym


def test_scope_nesting():
    st = SymbolTable()
    st.enter_scope("global")
    st.insert(Symbol("x", INT_TYPE, SymbolKind.VARIABLE, 1, 1))

    st.enter_scope("local")
    st.insert(Symbol("y", FLOAT_TYPE, SymbolKind.VARIABLE, 2, 1))

    assert st.lookup("x") is not None  # Видим глобальную
    assert st.lookup("y") is not None  # Видим локальную

    st.exit_scope()
    assert st.lookup("y") is None  # Локальная уничтожена
    assert st.lookup("x") is not None  # Глобальная на месте


def test_stack_offsets():
    st = SymbolTable()
    st.enter_scope("func")

    st.insert(Symbol("a", BOOL_TYPE, SymbolKind.VARIABLE, 1, 1))  # offset 0
    st.insert(Symbol("b", INT_TYPE, SymbolKind.VARIABLE, 2, 1))  # padding 3, offset 4

    sym_a = st.lookup("a")
    sym_b = st.lookup("b")

    assert sym_a.stack_offset == 0
    assert sym_b.stack_offset == 4