import sys
import os
import glob
import io

# Добавляем src в путь
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from lexer.lexer import Lexer


def run_test_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()

    # Перехватываем вывод (токены + ошибки)
    buffer = io.StringIO()
    original_stdout = sys.stdout

    try:
        sys.stdout = buffer
        lexer = Lexer(source)
        tokens = lexer.scan_tokens()
        for t in tokens:
            print(t)
        output = buffer.getvalue()
    finally:
        sys.stdout = original_stdout

    return output


def main():
    base_path = os.path.dirname(__file__)
    valid_path = os.path.join(base_path, '../lexer/valid')
    invalid_path = os.path.join(base_path, '../lexer/invalid')

    valid_files = glob.glob(os.path.join(valid_path, '*.src'))
    invalid_files = glob.glob(os.path.join(invalid_path, '*.src'))

    all_passed = True

    print("=" * 60)
    print("Running tests against Golden Master (.tokens files)")
    print("=" * 60)

    # Общая функция для запуска
    def check_files(files, folder_name):
        nonlocal all_passed
        for f in files:
            fname = os.path.basename(f)
            expected_file = f + '.tokens'

            # Проверяем, существует ли файл с ожидаемым результатом
            if not os.path.exists(expected_file):
                print(f"[SKIP] {fname} (No baseline file found. Run 'generate_baselines.py' first)")
                continue

            try:
                actual_output = run_test_file(f)

                with open(expected_file, 'r', encoding='utf-8') as ef:
                    expected_output = ef.read()

                if actual_output == expected_output:
                    print(f"[PASS] {fname}")
                else:
                    print(f"[FAIL] {fname}")
                    all_passed = False
                    print("-" * 40)
                    print("Expected:")
                    print(expected_output)
                    print("Actual:")
                    print(actual_output)
                    print("-" * 40)

            except Exception as e:
                print(f"[CRASH] {fname}: {e}")
                all_passed = False

    print("\n--- Valid Tests ---")
    check_files(valid_files, "valid")

    print("\n--- Invalid Tests ---")
    check_files(invalid_files, "invalid")

    if all_passed:
        print("\n" + "=" * 60)
        print("SUCCESS: All tests match expected output.")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("FAILURE: Some tests do not match expected output.")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()