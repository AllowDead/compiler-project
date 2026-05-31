import sys
import os
import glob
import io

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from lexer.lexer import Lexer
from parser.parser import Parser
from parser.printer import ASTPrinter


def run_parser_test(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()

    buffer = io.StringIO()
    original_stdout = sys.stdout
    try:
        sys.stdout = buffer
        lexer = Lexer(source)
        tokens = lexer.scan_tokens()
        parser = Parser(tokens)
        ast = parser.parse()
        if ast:
            printer = ASTPrinter()
            print(printer.print(ast))
        else:
            print("PARSING_FAILED")
        return buffer.getvalue()
    finally:
        sys.stdout = original_stdout


def check_files(files, folder_name, is_valid):
    passed = 0
    failed = 0
    print(f"\n--- Checking {folder_name} ---")

    for f in files:
        fname = os.path.basename(f)
        expected_file = f + '.expected'

        if not os.path.exists(expected_file):
            print(f"[SKIP] {fname} (No .expected file)")
            continue

        try:
            actual = run_parser_test(f)
            with open(expected_file, 'r', encoding='utf-8') as ef:
                expected = ef.read()

            if expected.strip() == actual.strip():
                print("[PASS]")
                passed += 1
            else:
                print(f"[FAIL] {fname}")
                failed += 1
                # УБРАНО ОГРАНИЧЕНИЕ ДЛИНЫ
                print("--- Expected ---")
                print(expected)
                print("--- Actual ---")
                print(actual)
                print("-----------------")
        except Exception as e:
            print(f"[CRASH] {fname}: {e}")
            failed += 1

    return passed, failed


def main():
    base_path = os.path.dirname(__file__)
    valid_base = os.path.join(base_path, '../parser/valid')
    invalid_base = os.path.join(base_path, '../parser/invalid')

    v_pass, v_fail = 0, 0
    i_pass, i_fail = 0, 0

    # Проходим по всем подпапкам valid
    for root, dirs, files in os.walk(valid_base):
        src_files = glob.glob(os.path.join(root, '*.src'))
        if src_files:
            p, f = check_files(src_files, os.path.basename(root), is_valid=True)
            v_pass += p;
            v_fail += f

    # Проходим по всем подпапкам invalid
    for root, dirs, files in os.walk(invalid_base):
        src_files = glob.glob(os.path.join(root, '*.src'))
        if src_files:
            p, f = check_files(src_files, os.path.basename(root), is_valid=False)
            i_pass += p;
            i_fail += f

    print("\n" + "=" * 40)
    print(f"Parser Tests: {v_pass + i_pass} passed, {v_fail + i_fail} failed")
    print("=" * 40)

    if (v_fail + i_fail) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()