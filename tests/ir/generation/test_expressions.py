from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tests.ir.utils import generate_ir, get_opnames, get_instructions, assert_golden


def test_arithmetic_expression():
    src = """
fn main() void {
    int x = 2 + 3 * 4;
}
"""
    ir = generate_ir(src)
    opnames = get_opnames(ir, "main")

    assert "ALLOCA" in opnames
    assert "MUL" in opnames
    assert "ADD" in opnames
    assert "STORE" in opnames


def test_expression_uses_three_address_temporaries():
    src = """
fn main() void {
    int x = 2 + 3 * 4;
}
"""
    ir = generate_ir(src)
    instructions = get_instructions(ir, "main")

    temp_dests = [
        inst.dest.value
        for inst in instructions
        if inst.dest is not None and getattr(inst.dest, "kind", None) == "temp"
    ]

    assert "t1" in temp_dests
    assert "t2" in temp_dests


def test_arithmetic_golden():
    base = Path(__file__).parent / "expressions"
    assert_golden(base / "arithmetic.src", base / "arithmetic.expected")