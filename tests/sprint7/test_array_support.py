import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

def compile_to_asm(src: str) -> str:
    with tempfile.TemporaryDirectory(prefix="minic_s7_arr_") as tmp:
        src_path = Path(tmp) / "case.src"
        asm_path = Path(tmp) / "case.asm"
        src_path.write_text(src, encoding="utf-8")
        result = subprocess.run([sys.executable, "src/main.py", "compile", "--input", str(src_path), "--output", str(asm_path)], cwd=PROJECT_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        assert result.returncode == 0, result.stdout + result.stderr + (asm_path.read_text(encoding="utf-8", errors="replace") if asm_path.exists() else "")
        return asm_path.read_text(encoding="utf-8")

def test_static_array_initializer_and_indexing_generates_gep_code():
    asm = compile_to_asm('''
fn main() int {
    int arr[3] = {1, 2, 3};
    arr[1] = 5;
    return arr[0] + arr[1] + arr[2];
}
''')
    assert "ALLOCA 12" in asm
    assert "array element address" in asm
    assert "imul rcx, 4" in asm
    assert "mov r11" in asm

def test_array_parameter_decays_to_pointer():
    asm = compile_to_asm('''
fn first(arr int[], size int) int {
    return arr[0];
}
fn main() int {
    int data[2] = {7, 9};
    return first(data, 2);
}
''')
    assert "call first" in asm
    assert "array element load" in asm
