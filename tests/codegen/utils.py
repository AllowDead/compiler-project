from pathlib import Path
import shutil
import subprocess
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
from codegen.x86_generator import X86Generator


def compile_to_assembly(source_code: str) -> str:
    tokens = Lexer(source_code).scan_tokens()
    ast = Parser(tokens).parse()
    analyzer = SemanticAnalyzer()
    decorated_ast = analyzer.analyze(ast)
    errors = analyzer.get_errors()
    if errors:
        raise AssertionError("Semantic errors during codegen test:\n" + "\n".join(str(e) for e in errors))
    ir_program = IRGenerator(analyzer.symbol_table, None).generate(decorated_ast)
    return X86Generator().generate(ir_program)


def has_tool(name: str) -> bool:
    return shutil.which(name) is not None


def assemble_and_run(tmp_path: Path, source_code: str, runtime_path: Path):
    asm = compile_to_assembly(source_code)
    asm_path = tmp_path / "program.asm"
    obj_path = tmp_path / "program.o"
    runtime_obj = tmp_path / "runtime.o"
    exe_path = tmp_path / "program"
    asm_path.write_text(asm, encoding="utf-8")

    subprocess.run(["nasm", "-f", "elf64", str(asm_path), "-o", str(obj_path)], check=True, capture_output=True, text=True)
    subprocess.run(["nasm", "-f", "elf64", str(runtime_path), "-o", str(runtime_obj)], check=True, capture_output=True, text=True)
    subprocess.run(["ld", "-o", str(exe_path), str(runtime_obj), str(obj_path)], check=True, capture_output=True, text=True)
    return subprocess.run([str(exe_path)], capture_output=True, text=True)
