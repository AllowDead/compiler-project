import subprocess
import sys
import tempfile
from pathlib import Path


SRC = '''
fn main() int {
    int x = 10 + 20;
    int y = x * 2;
    if (y > 50) { return 1; }
    return 0;
}
'''


def meaningful_asm_size(asm_text: str) -> int:
    """
    Count only meaningful assembly lines.

    We ignore:
    - empty lines
    - comments
    - optimization report comments

    This makes the benchmark compare generated code size,
    not documentation/statistics embedded into the .asm file.
    """
    meaningful_lines = []

    for line in asm_text.splitlines():
        stripped = line.strip()

        if not stripped:
            continue

        if stripped.startswith(";"):
            continue

        meaningful_lines.append(stripped)

    return len("\n".join(meaningful_lines).encode("utf-8"))


def extract_optimization_report(asm_text: str) -> str:
    if "Optimization Report:" not in asm_text:
        return ""

    report = asm_text.split("Optimization Report:", 1)[1].strip()
    return "Optimization Report:\n" + report


def compile_case(project_root: Path, optimize: bool):
    with tempfile.TemporaryDirectory(prefix="minic_s7_bench_") as tmp:
        src = Path(tmp) / "case.src"
        asm = Path(tmp) / ("opt.asm" if optimize else "base.asm")

        src.write_text(SRC, encoding="utf-8")

        cmd = [
            sys.executable,
            "src/main.py",
            "compile",
            "--input",
            str(src),
            "--output",
            str(asm),
            "--stats",
        ]

        if optimize:
            cmd.append("--optimize")

        result = subprocess.run(
            cmd,
            cwd=project_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        asm_text = asm.read_text(encoding="utf-8") if asm.exists() else ""
        meaningful_size = meaningful_asm_size(asm_text)

        return {
            "returncode": result.returncode,
            "asm_size": meaningful_size,
            "asm_text": asm_text,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": " ".join(cmd),
        }


def main():
    root = Path(__file__).resolve().parents[2]

    base = compile_case(root, optimize=False)
    opt = compile_case(root, optimize=True)

    print("Sprint 7 optimization benchmark")
    print(f"baseline meaningful asm bytes:  {base['asm_size']}")
    print(f"optimized meaningful asm bytes: {opt['asm_size']}")

    report = extract_optimization_report(opt["asm_text"])
    if report:
        print()
        print(report)

    if base["returncode"] != 0:
        print()
        print("[ERROR] Baseline compilation failed")
        print("Command:", base["command"])
        if base["stdout"]:
            print("stdout:")
            print(base["stdout"])
        if base["stderr"]:
            print("stderr:")
            print(base["stderr"])

    if opt["returncode"] != 0:
        print()
        print("[ERROR] Optimized compilation failed")
        print("Command:", opt["command"])
        if opt["stdout"]:
            print("stdout:")
            print(opt["stdout"])
        if opt["stderr"]:
            print("stderr:")
            print(opt["stderr"])

    return 0 if base["returncode"] == 0 and opt["returncode"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())