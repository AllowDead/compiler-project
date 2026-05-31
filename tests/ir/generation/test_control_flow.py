from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tests.ir.utils import generate_ir, get_block_labels, get_opnames, assert_golden


def test_if_else_ir():
    src = """
fn main() void {
    int x = 1;
    if (x > 0) {
        x = 2;
    } else {
        x = 3;
    }
}
"""
    ir = generate_ir(src)

    labels = get_block_labels(ir, "main")
    opnames = get_opnames(ir, "main")

    assert "entry" in labels
    assert any(label.startswith("L_then") for label in labels)
    assert any(label.startswith("L_else") for label in labels)
    assert any(label.startswith("L_endif") for label in labels)

    assert "CMP_GT" in opnames
    assert "JUMP_IF" in opnames
    assert "JUMP" in opnames
    assert "STORE" in opnames


def test_while_loop_ir():
    src = """
fn main() void {
    int i = 0;
    while (i < 10) {
        i = i + 1;
    }
}
"""
    ir = generate_ir(src)

    labels = get_block_labels(ir, "main")
    opnames = get_opnames(ir, "main")

    assert "entry" in labels
    assert any(label.startswith("L_loop_header") for label in labels)
    assert any(label.startswith("L_loop_body") for label in labels)
    assert any(label.startswith("L_loop_exit") for label in labels)

    assert "CMP_LT" in opnames
    assert "JUMP_IF" in opnames
    assert "ADD" in opnames
    assert "STORE" in opnames


def test_if_else_golden():
    base = Path(__file__).parent / "control_flow"
    assert_golden(base / "if_else.src", base / "if_else.expected")


def test_while_loop_golden():
    base = Path(__file__).parent / "control_flow"
    assert_golden(base / "while_loop.src", base / "while_loop.expected")