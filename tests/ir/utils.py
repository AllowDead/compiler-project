from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from lexer.lexer import Lexer
from parser.parser import Parser
from semantic.analyzer import SemanticAnalyzer
from ir.ir_generator import IRGenerator
from ir.ir_instructions import IROp


def generate_ir(source_code: str):
    lexer = Lexer(source_code)
    tokens = lexer.scan_tokens()

    parser = Parser(tokens)
    ast = parser.parse()

    analyzer = SemanticAnalyzer()
    decorated_ast = analyzer.analyze(ast)
    errors = analyzer.get_errors()

    if errors:
        formatted = "\n".join(str(error) for error in errors)
        raise AssertionError(f"Semantic errors during IR test:\n{formatted}")

    generator = IRGenerator(analyzer.symbol_table, None)
    return generator.generate(decorated_ast)


def generate_ir_text(source_code: str) -> str:
    return generate_ir(source_code).to_text().strip()


def get_function(ir_program, name: str = "main"):
    assert name in ir_program.functions, f"Function '{name}' not found in IR program"
    return ir_program.functions[name]


def get_blocks(ir_program, function_name: str = "main"):
    function = get_function(ir_program, function_name)
    return [function.blocks[label] for label in function.block_order]


def get_block_labels(ir_program, function_name: str = "main"):
    return [block.label for block in get_blocks(ir_program, function_name)]


def get_instructions(ir_program, function_name: str = "main"):
    instructions = []
    for block in get_blocks(ir_program, function_name):
        instructions.extend(block.instructions)
    return instructions


def get_all_instructions(ir_program):
    instructions = []
    for function_name in ir_program.function_order:
        instructions.extend(get_instructions(ir_program, function_name))
    return instructions


def opcode_name(instruction) -> str:
    op = instruction.op
    if isinstance(op, IROp):
        return op.value
    return str(op)


def get_opnames(ir_program, function_name: str = "main"):
    return [opcode_name(inst) for inst in get_instructions(ir_program, function_name)]


def assert_golden(source_path: Path, expected_path: Path):
    source = source_path.read_text(encoding="utf-8")
    expected = expected_path.read_text(encoding="utf-8").strip()
    actual = generate_ir_text(source)
    assert actual == expected