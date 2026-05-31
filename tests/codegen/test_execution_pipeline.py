from pathlib import Path
import pytest

from tests.codegen.utils import assemble_and_run, has_tool

RUNTIME = Path(__file__).resolve().parents[2] / "src" / "runtime" / "runtime.asm"

pytestmark = pytest.mark.skipif(
    not (has_tool("nasm") and has_tool("ld")),
    reason="Sprint 5 execution tests require Linux/WSL with nasm and ld installed.",
)


def test_simple_return_execution(tmp_path):
    result = assemble_and_run(tmp_path, """
fn main() int {
    return 5;
}
""", RUNTIME)
    assert result.returncode == 5


def test_arithmetic_execution(tmp_path):
    result = assemble_and_run(tmp_path, """
fn main() int {
    int x = 2 + 3 * 4;
    return x;
}
""", RUNTIME)
    assert result.returncode == 14


def test_function_call_execution(tmp_path):
    result = assemble_and_run(tmp_path, """
fn add(a int, b int) int {
    return a + b;
}

fn main() int {
    return add(20, 22);
}
""", RUNTIME)
    assert result.returncode == 42
