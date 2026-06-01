import subprocess
import sys
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parents[2]
    print("=" * 70)
    print("Running MiniCompiler Sprint 7 tests")
    print("=" * 70)
    result = subprocess.run([sys.executable, "-m", "pytest", "tests/sprint7", "tests/optimization", "-v"], cwd=project_root)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
