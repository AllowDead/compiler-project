import subprocess
import sys
from pathlib import Path


def main() -> int:
    """
    Runs all Sprint 4 IR tests.

    Usage from project root:
        python tests/test_runner/run_ir_tests.py

    Or from anywhere:
        python path/to/compiler-project/tests/test_runner/run_ir_tests.py
    """
    project_root = Path(__file__).resolve().parents[2]
    ir_tests_dir = project_root / "tests" / "ir"

    if not ir_tests_dir.exists():
        print(f"[ERROR] IR tests directory not found: {ir_tests_dir}")
        return 1

    command = [
        sys.executable,
        "-m",
        "pytest",
        str(ir_tests_dir),
        "-v",
    ]

    print("=" * 70)
    print("Running MiniCompiler Sprint 4 IR tests")
    print("=" * 70)
    print(f"Project root: {project_root}")
    print(f"Tests path:   {ir_tests_dir}")
    print(f"Command:      {' '.join(command)}")
    print("=" * 70)

    result = subprocess.run(
        command,
        cwd=project_root,
    )

    print("=" * 70)

    if result.returncode == 0:
        print("[RESULT] PASS: all IR tests passed.")
    else:
        print(f"[RESULT] FAIL: IR tests failed with exit code {result.returncode}.")

    print("=" * 70)

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())