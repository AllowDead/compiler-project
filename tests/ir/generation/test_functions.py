from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tests.ir.utils import generate_ir, get_opnames, get_function, assert_golden


def test_function_call_ir():
    src = """
fn inc(x int) int {
    return x + 1;
}

fn main() int {
    int y = inc(41);
    return y;
}
"""
    ir = generate_ir(src)

    assert "inc" in ir.functions
    assert "main" in ir.functions

    main_ops = get_opnames(ir, "main")
    inc_ops = get_opnames(ir, "inc")

    assert "PARAM" in main_ops
    assert "CALL" in main_ops
    assert "RETURN" in main_ops
    assert "ADD" in inc_ops
    assert "RETURN" in inc_ops


def test_recursive_factorial_ir():
    src = """
fn factorial(n int) int {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}
"""
    ir = generate_ir(src)
    ops = get_opnames(ir, "factorial")

    assert "CMP_LE" in ops
    assert "JUMP_IF" in ops
    assert "SUB" in ops
    assert "PARAM" in ops
    assert "CALL" in ops
    assert "MUL" in ops
    assert "RETURN" in ops


def test_function_representation_has_parameters_and_return_type():
    src = """
fn inc(x int) int {
    return x + 1;
}
"""
    ir = generate_ir(src)
    function = get_function(ir, "inc")

    assert function.name == "inc"
    assert function.return_type == "int"
    assert function.parameters == [("int", "x")]


def test_function_call_golden():
    base = Path(__file__).parent / "functions"
    assert_golden(base / "function_call.src", base / "function_call.expected")