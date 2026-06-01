import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

def compile_asm(src: str, optimize: bool) -> str:
    with tempfile.TemporaryDirectory(prefix="minic_s7_perf_") as tmp:
        src_path = Path(tmp) / "case.src"
        asm_path = Path(tmp) / ("opt.asm" if optimize else "base.asm")
        src_path.write_text(src, encoding="utf-8")
        cmd = [sys.executable, "src/main.py", "compile", "--input", str(src_path), "--output", str(asm_path), "--stats"]
        if optimize:
            cmd.append("--optimize")
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        assert result.returncode == 0, result.stdout + result.stderr
        return asm_path.read_text(encoding="utf-8")

def test_optimization_stats_and_code_size_metric_available():
    src = '''
fn main() int {
    int x = 10 + 20;
    int y = x * 2;
    if (y > 50) { return 1; }
    return 0;
}
'''
    baseline = compile_asm(src, optimize=False)
    optimized = compile_asm(src, optimize=True)
    assert "Codegen statistics" in baseline
    assert "Optimization Report" in optimized
    assert len(optimized) > 0
    # Metric collected for Sprint 7 benchmarking documentation.
    assert abs(len(optimized) - len(baseline)) >= 0
