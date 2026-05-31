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


def test_expression_translation_to_three_address_code():
    ir = generate_ir("""
fn test() int {
    int x = 2 * 3 + 4;
    return x;
}
""")
    text = ir.to_text()
    assert "MUL 2, 3" in text
    assert "ADD" in text
    assert "STORE [x_0]" in text
    assert "RETURN" in text


def test_if_generates_basic_blocks_and_jumps():
    ir = generate_ir("""
fn test() void {
    int x = 1;
    if (x > 0) {
        x = x + 1;
    } else {
        x = x - 1;
    }
}
""")
    text = ir.to_text()
    assert "JUMP_IF" in text
    assert "L_then" in text
    assert "L_else" in text
    assert "PHI" in text


def test_while_generates_back_edge():
    ir = generate_ir("""
fn test() void {
    int x = 0;
    while (x < 3) {
        x = x + 1;
    }
}
""")
    function = ir.functions["test"]
    edges = function.cfg().edges()
    assert any("L_loop_body" in src and "L_loop_header" in dst for src, dst in edges)


def test_function_call_translation():
    ir = generate_ir("""
fn inc(x int) int {
    return x + 1;
}
fn test() int {
    return inc(5);
}
""")
    text = ir.to_text()
    assert "PARAM 0, 5" in text
    assert "CALL inc" in text
