import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from lexer.lexer import Lexer
from parser.parser import Parser
from semantic.analyzer import SemanticAnalyzer
from ir.ir_generator import IRGenerator
from ir.optimizer import IROptimizer


def build_ir(src: str):
    tokens = Lexer(src).scan_tokens()
    ast = Parser(tokens).parse()
    analyzer = SemanticAnalyzer()
    decorated = analyzer.analyze(ast)
    assert not analyzer.get_errors(), "\n".join(map(str, analyzer.get_errors()))
    return IRGenerator(analyzer.symbol_table, None).generate(decorated)


def test_constant_folding_and_stats():
    ir = build_ir('''
fn main() int {
    int x = 10 + 20;
    return x;
}
''')
    optimizer = IROptimizer()
    optimizer.optimize(ir)
    assert optimizer.stats.constant_folds >= 1
    assert "30" in ir.to_text()


def test_optimization_pipeline_keeps_semantics_shape():
    ir = build_ir('''
fn main() int {
    int x = 3 * 4;
    if (x > 10) { return 1; }
    return 0;
}
''')
    optimizer = IROptimizer()
    optimizer.optimize(ir)
    assert optimizer.stats.iterations >= 1
    assert ir.statistics()["total_functions"] == 1
