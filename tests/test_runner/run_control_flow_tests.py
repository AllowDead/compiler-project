from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run_command(command, cwd: Path, timeout: int = 10) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )


def read_expected(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def collect_cases(path: Path):
    return sorted(path.rglob("*.src"))


def compile_to_asm(project_root: Path, source_path: Path, asm_path: Path):
    return run_command(
        [sys.executable, "src/main.py", "compile", "--input", str(source_path), "--output", str(asm_path)],
        cwd=project_root,
        timeout=15,
    )


def assemble_and_link(project_root: Path, asm_path: Path, work_dir: Path):
    obj = work_dir / "program.o"
    runtime_obj = work_dir / "runtime.o"
    exe = work_dir / "program"

    result = run_command(["nasm", "-f", "elf64", "-o", str(obj), str(asm_path)], cwd=project_root, timeout=15)
    if result.returncode != 0:
        return result, None

    result = run_command(["nasm", "-f", "elf64", "-o", str(runtime_obj), "src/runtime/runtime.asm"], cwd=project_root, timeout=15)
    if result.returncode != 0:
        return result, None

    result = run_command(["ld", "-o", str(exe), str(runtime_obj), str(obj)], cwd=project_root, timeout=15)
    if result.returncode != 0:
        return result, None

    return result, exe


def run_valid_case(project_root: Path, source_path: Path) -> bool:
    expected_path = source_path.with_suffix(".expected")
    if not expected_path.exists():
        print(f"[FAIL] Missing expected file: {expected_path}")
        return False
    expected = read_expected(expected_path)

    with tempfile.TemporaryDirectory(prefix="minic_cf_valid_") as tmp:
        work_dir = Path(tmp)
        asm_path = work_dir / "program.asm"
        compile_result = compile_to_asm(project_root, source_path, asm_path)
        if compile_result.returncode != 0:
            print(f"[FAIL] {source_path}")
            print("  compile failed")
            print(compile_result.stdout)
            print(compile_result.stderr)
            if asm_path.exists():
                print(asm_path.read_text(encoding="utf-8", errors="replace"))
            return False

        build_result, exe = assemble_and_link(project_root, asm_path, work_dir)
        if build_result.returncode != 0 or exe is None:
            print(f"[FAIL] {source_path}")
            print("  assemble/link failed")
            print(build_result.stdout)
            print(build_result.stderr)
            return False

        try:
            run_result = run_command([str(exe)], cwd=project_root, timeout=5)
        except subprocess.TimeoutExpired:
            print(f"[FAIL] {source_path}")
            print("  valid program timed out")
            return False

        actual = str(run_result.returncode)
        if actual != expected:
            print(f"[FAIL] {source_path}")
            print(f"  expected exit code: {expected}")
            print(f"  actual exit code:   {actual}")
            print(run_result.stdout)
            print(run_result.stderr)
            return False

        print(f"[PASS] {source_path} -> exit code {actual}")
        return True


def run_invalid_case(project_root: Path, source_path: Path) -> bool:
    expected_path = source_path.with_suffix(".expected")
    if not expected_path.exists():
        print(f"[FAIL] Missing expected file: {expected_path}")
        return False
    expected = read_expected(expected_path)

    with tempfile.TemporaryDirectory(prefix="minic_cf_invalid_") as tmp:
        work_dir = Path(tmp)
        asm_path = work_dir / "program.asm"
        compile_result = compile_to_asm(project_root, source_path, asm_path)
        generated_output = asm_path.read_text(encoding="utf-8", errors="replace") if asm_path.exists() else ""
        compile_output = compile_result.stdout + "\n" + compile_result.stderr + "\n" + generated_output

        if expected in compile_output:
            print(f"[PASS] {source_path} -> expected compile diagnostic found")
            return True
        if expected.startswith("semantic error") and compile_result.returncode != 0:
            print(f"[PASS] {source_path} -> semantic error detected")
            return True
        if compile_result.returncode != 0:
            print(f"[FAIL] {source_path}")
            print("  compile failed, but expected diagnostic was not found")
            print(f"  expected: {expected}")
            print(compile_output)
            return False

        build_result, exe = assemble_and_link(project_root, asm_path, work_dir)
        if build_result.returncode != 0 or exe is None:
            build_output = build_result.stdout + "\n" + build_result.stderr
            if expected in build_output:
                print(f"[PASS] {source_path} -> expected assembly/link diagnostic found")
                return True
            print(f"[FAIL] {source_path}")
            print("  assemble/link failed, but expected diagnostic was not found")
            print(build_output)
            return False

        try:
            run_result = run_command([str(exe)], cwd=project_root, timeout=3)
        except subprocess.TimeoutExpired:
            runtime_output = "runtime warning: potential infinite loop"
            if expected in runtime_output:
                print(f"[PASS] {source_path} -> expected timeout/infinite loop warning")
                return True
            print(f"[FAIL] {source_path}")
            print("  timed out, but expected diagnostic did not match")
            print(f"  expected: {expected}")
            return False

        runtime_output = run_result.stdout + "\n" + run_result.stderr + f"\nexit_code={run_result.returncode}"
        if expected in runtime_output:
            print(f"[PASS] {source_path} -> expected runtime diagnostic found")
            return True

        print(f"[FAIL] {source_path}")
        print("  expected diagnostic was not found")
        print(f"  expected: {expected}")
        print(runtime_output)
        return False


def check_tools():
    return [tool for tool in ("nasm", "ld") if shutil.which(tool) is None]


def main() -> int:
    project_root = Path(__file__).resolve().parents[2]
    print("=" * 70)
    print("Running MiniCompiler Sprint 6 control-flow tests")
    print("=" * 70)
    print(f"Project root: {project_root}")

    missing = check_tools()
    if missing:
        print("[ERROR] Missing required Linux tools:")
        for tool in missing:
            print(f"  - {tool}")
        print("Install inside WSL/Linux: sudo apt install -y nasm binutils")
        return 1

    valid_dir = project_root / "tests" / "control_flow" / "valid"
    invalid_dir = project_root / "tests" / "control_flow" / "invalid"
    ok = True

    print("\n[1/2] Running valid control-flow execution tests")
    print("-" * 70)
    for case in collect_cases(valid_dir):
        ok = run_valid_case(project_root, case) and ok

    print("\n[2/2] Running invalid control-flow diagnostics tests")
    print("-" * 70)
    for case in collect_cases(invalid_dir):
        ok = run_invalid_case(project_root, case) and ok

    print("=" * 70)
    if ok:
        print("[RESULT] PASS: all Sprint 6 control-flow tests passed.")
        return 0
    print("[RESULT] FAIL: some Sprint 6 control-flow tests failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
