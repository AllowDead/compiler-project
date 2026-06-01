from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def compile_source(source: str) -> str:
    with tempfile.TemporaryDirectory(prefix="minic_cf_asm_") as tmp:
        source_path = Path(tmp) / "case.src"
        asm_path = Path(tmp) / "case.asm"
        source_path.write_text(source, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "src/main.py", "compile", "--input", str(source_path), "--output", str(asm_path)],
            cwd=PROJECT_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
        )
        assert result.returncode == 0, result.stdout + result.stderr + (asm_path.read_text(encoding="utf-8", errors="replace") if asm_path.exists() else "")
        return asm_path.read_text(encoding="utf-8")


def test_if_comparison_uses_direct_conditional_jump():
    asm = compile_source("""
fn main() int {
    int x = 1;
    if (x > 0) { return 1; }
    return 0;
}
""")
    assert "cmp eax, 0" in asm
    assert "jg .LBB_" in asm


def test_while_loop_has_header_body_exit_jumps():
    asm = compile_source("""
fn main() int {
    int i = 0;
    while (i < 3) { i = i + 1; }
    return i;
}
""")
    assert "loop_header" in asm
    assert "loop_body" in asm
    assert "loop_exit" in asm
    assert "jmp .LBB_" in asm


def test_and_short_circuit_skips_rhs_division():
    asm = compile_source("""
fn main() int {
    int a = 0;
    int b = 10;
    if (a != 0 && b / a > 2) { return 1; }
    return 2;
}
""")
    assert "&& short-circuit false" in asm
    assert "&& left true: evaluate right" in asm
    assert "idiv ecx" in asm
    assert asm.index("&& short-circuit false") < asm.index("idiv ecx")


def test_or_short_circuit_skips_rhs_division():
    asm = compile_source("""
fn main() int {
    int a = 0;
    if (true || 10 / a > 1) { return 5; }
    return 0;
}
""")
    assert "|| short-circuit true" in asm
    assert "|| left false: evaluate right" in asm
    assert "idiv ecx" in asm
    assert asm.index("|| short-circuit true") < asm.index("idiv ecx")


def test_division_by_zero_runtime_trap_is_emitted():
    asm = compile_source("""
fn main() int {
    return 10 / 0;
}
""")
    assert "cmp ecx, 0" in asm
    assert "je __minic_division_by_zero" in asm
