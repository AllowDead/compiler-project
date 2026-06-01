import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

def compile_to_asm(src: str) -> str:
    with tempfile.TemporaryDirectory(prefix="minic_s7_ext_") as tmp:
        src_path = Path(tmp) / "case.src"
        asm_path = Path(tmp) / "case.asm"
        src_path.write_text(src, encoding="utf-8")
        result = subprocess.run([sys.executable, "src/main.py", "compile", "--input", str(src_path), "--output", str(asm_path)], cwd=PROJECT_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        assert result.returncode == 0, result.stdout + result.stderr + (asm_path.read_text(encoding="utf-8", errors="replace") if asm_path.exists() else "")
        return asm_path.read_text(encoding="utf-8")

def test_printf_variadic_and_string_literal_data_section():
    asm = compile_to_asm('''
fn main() int {
    printf("answer=%d\\n", 42);
    return 0;
}
''')
    assert "extern printf" in asm
    assert "section .data" in asm
    assert "xor eax, eax" in asm
    assert "call printf" in asm

def test_malloc_and_free_are_external_calls_with_pointer_return():
    asm = compile_to_asm('''
fn main() int {
    ptr p = malloc(16);
    free(p);
    return 0;
}
''')
    assert "extern malloc" in asm
    assert "extern free" in asm
    assert "call malloc" in asm
    assert "mov qword" in asm
    assert "call free" in asm
