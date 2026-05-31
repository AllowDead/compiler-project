from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tests.ir.utils import generate_ir, get_function, get_instructions, opcode_name


def test_arithmetic_and_comparison_types():
    src = """
fn main() void {
    int a = 10;
    int b = 20;
    bool c = a < b;
}
"""
    ir = generate_ir(src)
    function = get_function(ir, "main")

    assert function.temp_types["t1"] == "int"
    assert function.temp_types["t2"] == "int"
    assert function.temp_types["t3"] == "bool"

    instructions = get_instructions(ir, "main")
    cmp_instructions = [inst for inst in instructions if opcode_name(inst) == "CMP_LT"]

    assert len(cmp_instructions) == 1
    assert cmp_instructions[0].type_name == "bool"


def test_variable_slots_preserve_type_information():
    src = """
fn main() void {
    int a = 10;
    bool b = true;
}
"""
    ir = generate_ir(src)
    function = get_function(ir, "main")

    variable_slots = list(function.variables.values())

    assert any(
        slot.source_name == "a" and slot.type_name == "int"
        for slot in variable_slots
    )

    assert any(
        slot.source_name == "b" and slot.type_name == "bool"
        for slot in variable_slots
    )


def test_type_consistency_expected_properties():
    base = Path(__file__).parent / "type_consistency"
    source = (base / "typed_ops.src").read_text(encoding="utf-8")
    expected_lines = (base / "typed_ops.expected").read_text(encoding="utf-8").strip().splitlines()

    ir = generate_ir(source)
    function = get_function(ir, "main")
    instructions = get_instructions(ir, "main")

    typed_temporaries = ",".join(
        f"{name}:{type_name}" for name, type_name in sorted(function.temp_types.items())
    )

    actual = {
        "blocks": str(len(function.blocks)),
        "instructions": str(len(instructions)),
        "temporaries": str(len(function.temp_types)),
        "typed_temporaries": typed_temporaries,
    }

    for line in expected_lines:
        key, value = line.split("=", 1)
        if key in actual:
            assert actual[key] == value