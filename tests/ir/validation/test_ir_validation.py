import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from lexer.lexer import Lexer
from parser.parser import Parser
from semantic.analyzer import SemanticAnalyzer
from ir.ir_generator import IRGenerator


def generate_ir(source: str):
    tokens = Lexer(source).scan_tokens()
    ast = Parser(tokens).parse()
    analyzer = SemanticAnalyzer()
    decorated = analyzer.analyze(ast)
    assert analyzer.get_errors() == []
    return IRGenerator(analyzer.symbol_table, None).generate(decorated)


def test_jumps_target_valid_labels():
    ir = generate_ir("""
fn test() void {
    int x = 0;
    if (x == 0) { x = 1; }
}
""")
    result = ir.functions["test"].cfg().validate()
    assert result.ok
    assert result.errors == []


def test_json_output_contains_complete_program_structure():
    ir = generate_ir("""
fn test() int {
    return 42;
}
""")
    data = ir.to_json()
    assert '"functions"' in data
    assert '"blocks"' in data
    assert '"statistics"' in data


def test_statistics_report_required_values():
    ir = generate_ir("""
fn test() int {
    int x = 1;
    return x;
}
""")
    stats = ir.statistics()
    assert stats["total_functions"] == 1
    assert stats["total_basic_blocks"] >= 1
    assert stats["total_instructions"] >= 1
    assert "RETURN" in stats["instruction_by_type"]
