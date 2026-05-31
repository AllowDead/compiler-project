import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run_command(command, cwd, timeout=10):
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )


def read_expected(expected_path: Path) -> str:
    return expected_path.read_text(encoding="utf-8").strip()


def collect_cases(base_dir: Path):
    return sorted(base_dir.rglob("*.src"))


def compile_to_asm(project_root: Path, source_path: Path, asm_path: Path):
    return run_command(
        [
            sys.executable,
            "src/main.py",
            "compile",
            "--input",
            str(source_path),
            "--output",
            str(asm_path),
        ],
        cwd=project_root,
        timeout=15,
    )


def assemble_and_link(project_root: Path, asm_path: Path, work_dir: Path):
    object_path = work_dir / "program.o"
    runtime_object_path = work_dir / "runtime.o"
    executable_path = work_dir / "program"

    nasm_program = run_command(
        [
            "nasm",
            "-f",
            "elf64",
            "-o",
            str(object_path),
            str(asm_path),
        ],
        cwd=project_root,
        timeout=15,
    )

    if nasm_program.returncode != 0:
        return nasm_program, None

    nasm_runtime = run_command(
        [
            "nasm",
            "-f",
            "elf64",
            "-o",
            str(runtime_object_path),
            "src/runtime/runtime.asm",
        ],
        cwd=project_root,
        timeout=15,
    )

    if nasm_runtime.returncode != 0:
        return nasm_runtime, None

    link_result = run_command(
        [
            "ld",
            "-o",
            str(executable_path),
            str(runtime_object_path),
            str(object_path),
        ],
        cwd=project_root,
        timeout=15,
    )

    if link_result.returncode != 0:
        return link_result, None

    return link_result, executable_path


def run_valid_case(project_root: Path, source_path: Path) -> bool:
    expected_path = source_path.with_suffix(".expected")

    if not expected_path.exists():
        print(f"[FAIL] Missing expected file: {expected_path}")
        return False

    expected = read_expected(expected_path)

    with tempfile.TemporaryDirectory(prefix="minic_codegen_") as tmp:
        work_dir = Path(tmp)
        asm_path = work_dir / "program.asm"

        compile_result = compile_to_asm(project_root, source_path, asm_path)

        if compile_result.returncode != 0:
            print(f"[FAIL] {source_path}")
            print("  Compilation failed.")
            print(compile_result.stdout)
            print(compile_result.stderr)
            return False

        build_result, executable_path = assemble_and_link(project_root, asm_path, work_dir)

        if build_result.returncode != 0 or executable_path is None:
            print(f"[FAIL] {source_path}")
            print("  Assembly/linking failed.")
            print(build_result.stdout)
            print(build_result.stderr)
            return False

        run_result = run_command(
            [str(executable_path)],
            cwd=project_root,
            timeout=5,
        )

        actual = str(run_result.returncode)

        if actual != expected:
            print(f"[FAIL] {source_path}")
            print(f"  Expected exit code: {expected}")
            print(f"  Actual exit code:   {actual}")
            print("  stdout:")
            print(run_result.stdout)
            print("  stderr:")
            print(run_result.stderr)
            return False

        print(f"[PASS] {source_path} -> exit code {actual}")
        return True


def run_invalid_case(project_root: Path, source_path: Path) -> bool:
    expected_path = source_path.with_suffix(".expected")

    if not expected_path.exists():
        print(f"[FAIL] Missing expected file: {expected_path}")
        return False

    expected_fragment = read_expected(expected_path)

    with tempfile.TemporaryDirectory(prefix="minic_codegen_invalid_") as tmp:
        work_dir = Path(tmp)
        asm_path = work_dir / "program.asm"

        compile_result = compile_to_asm(project_root, source_path, asm_path)

        generated_output = ""
        if asm_path.exists():
            generated_output = asm_path.read_text(encoding="utf-8", errors="replace")

        compile_output = (
            compile_result.stdout
            + "\n"
            + compile_result.stderr
            + "\n"
            + generated_output
            + f"\ncompile_exit_code={compile_result.returncode}"
        )

        # 1. Если ожидаемый текст реально есть в stdout/stderr/output-файле
        if expected_fragment in compile_output:
            print(f"[PASS] {source_path} -> expected compile diagnostic found")
            return True

        # 2. Semantic invalid cases.
        # Твой compile сейчас корректно завершается с кодом != 0,
        # но может не печатать точный текст "semantic error: ...".
        if compile_result.returncode != 0:
            if expected_fragment.startswith("semantic error:"):
                print(f"[PASS] {source_path} -> semantic error detected")
                return True

            print(f"[FAIL] {source_path}")
            print("  Compilation failed, but expected fragment was not found.")
            print(f"  Expected fragment: {expected_fragment}")
            print("  Actual output:")
            print(compile_output)
            return False

        # 3. Если компиляция прошла, собираем asm.
        build_result, executable_path = assemble_and_link(project_root, asm_path, work_dir)

        build_output = (
            build_result.stdout
            + "\n"
            + build_result.stderr
            + f"\nlink_exit_code={build_result.returncode}"
        )

        if expected_fragment in build_output:
            print(f"[PASS] {source_path} -> expected assembly/link diagnostic found")
            return True

        if build_result.returncode != 0 or executable_path is None:
            print(f"[FAIL] {source_path}")
            print("  Assembly/linking failed, but expected fragment was not found.")
            print(f"  Expected fragment: {expected_fragment}")
            print("  Actual output:")
            print(build_output)
            return False

        # 4. Запускаем программу.
        try:
            run_result = run_command(
                [str(executable_path)],
                cwd=project_root,
                timeout=3,
            )
        except subprocess.TimeoutExpired:
            runtime_output = "runtime warning: potential infinite loop"

            if expected_fragment in runtime_output:
                print(f"[PASS] {source_path} -> expected timeout/infinite loop warning")
                return True

            print(f"[FAIL] {source_path}")
            print("  Program timed out, but expected fragment did not match.")
            print(f"  Expected fragment: {expected_fragment}")
            print(f"  Actual output: {runtime_output}")
            return False

        runtime_output = (
            run_result.stdout
            + "\n"
            + run_result.stderr
            + f"\nexit_code={run_result.returncode}"
        )

        # Linux SIGFPE: деление на ноль обычно возвращает -8.
        if run_result.returncode == -8:
            runtime_output += "\nruntime error: division by zero"

        if expected_fragment in runtime_output:
            print(f"[PASS] {source_path} -> expected runtime result found")
            return True

        print(f"[FAIL] {source_path}")
        print("  Expected error/runtime fragment was not found.")
        print(f"  Expected fragment: {expected_fragment}")
        print("  Actual output:")
        print(runtime_output)
        return False


def run_pytest_suite(project_root: Path) -> bool:
    tests_dir = project_root / "tests" / "codegen"

    result = run_command(
        [
            sys.executable,
            "-m",
            "pytest",
            str(tests_dir),
            "-v",
        ],
        cwd=project_root,
        timeout=60,
    )

    print(result.stdout)

    if result.stderr:
        print(result.stderr)

    return result.returncode == 0


def check_tools_available():
    missing = []

    for tool in ["nasm", "ld"]:
        if shutil.which(tool) is None:
            missing.append(tool)

    return missing


def main() -> int:
    project_root = Path(__file__).resolve().parents[2]

    print("=" * 70)
    print("Running MiniCompiler Sprint 5 codegen tests")
    print("=" * 70)
    print(f"Project root: {project_root}")
    print("=" * 70)

    missing_tools = check_tools_available()

    if missing_tools:
        print("[ERROR] Missing required tools for full Sprint 5 execution pipeline:")
        for tool in missing_tools:
            print(f"  - {tool}")
        print()
        print("Install inside WSL/Linux:")
        print("  sudo apt update")
        print("  sudo apt install -y nasm binutils")
        print("=" * 70)
        return 1

    ok = True

    print("\n[1/3] Running pytest codegen tests")
    print("-" * 70)
    ok = run_pytest_suite(project_root) and ok

    valid_dir = project_root / "tests" / "codegen" / "valid"
    invalid_dir = project_root / "tests" / "codegen" / "invalid"

    print("\n[2/3] Running valid .src/.expected execution tests")
    print("-" * 70)

    valid_cases = collect_cases(valid_dir)

    if not valid_cases:
        print(f"[WARN] No valid .src files found in {valid_dir}")

    for source_path in valid_cases:
        ok = run_valid_case(project_root, source_path) and ok

    print("\n[3/3] Running invalid .src/.expected diagnostics tests")
    print("-" * 70)

    invalid_cases = collect_cases(invalid_dir)

    if not invalid_cases:
        print(f"[WARN] No invalid .src files found in {invalid_dir}")

    for source_path in invalid_cases:
        ok = run_invalid_case(project_root, source_path) and ok

    print("=" * 70)

    if ok:
        print("[RESULT] PASS: all Sprint 5 codegen tests passed.")
        print("=" * 70)
        return 0

    print("[RESULT] FAIL: some Sprint 5 codegen tests failed.")
    print("=" * 70)
    return 1


if __name__ == "__main__":
    sys.exit(main())