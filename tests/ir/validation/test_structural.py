from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tests.ir.utils import generate_ir, get_blocks, get_block_labels, get_instructions, opcode_name


TERMINATORS = {"JUMP", "JUMP_IF", "JUMP_IF_NOT", "RETURN"}


def test_basic_blocks_have_valid_structure():
    src = """
fn main() void {
    int i = 0;
    while (i < 2) {
        i = i + 1;
    }
}
"""
    ir = generate_ir(src)
    blocks = get_blocks(ir, "main")

    assert len(blocks) == 4

    for block in blocks:
        assert block.label
        assert block.instructions
        assert opcode_name(block.instructions[-1]) in TERMINATORS


def test_all_labels_unique():
    src = """
fn main() void {
    int x = 0;
    if (x > 0) {
        x = 1;
    } else {
        x = 2;
    }
}
"""
    ir = generate_ir(src)
    labels = get_block_labels(ir, "main")

    assert len(labels) == len(set(labels))


def test_all_jump_targets_are_valid_labels():
    src = """
fn main() void {
    int i = 0;
    while (i < 2) {
        i = i + 1;
    }
}
"""
    ir = generate_ir(src)
    labels = set(get_block_labels(ir, "main"))

    for instruction in get_instructions(ir, "main"):
        for target in instruction.target_labels():
            assert target in labels


def test_structural_golden_properties():
    base = Path(__file__).parent / "structural_checks"
    source = (base / "while_structure.src").read_text(encoding="utf-8")
    expected_lines = (base / "while_structure.expected").read_text(encoding="utf-8").strip().splitlines()

    ir = generate_ir(source)
    blocks = get_blocks(ir, "main")
    instructions = get_instructions(ir, "main")
    labels = get_block_labels(ir, "main")

    stats = ir.statistics()
    actual = {
        "blocks": str(len(blocks)),
        "instructions": str(len(instructions)),
        "temporaries": str(stats["total_temporaries"]),
        "labels": ",".join(labels),
        "terminal_ops": ",".join(opcode_name(block.instructions[-1]) for block in blocks),
    }

    for line in expected_lines:
        key, value = line.split("=", 1)
        if key in actual:
            assert actual[key] == value