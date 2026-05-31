import os
import sys

# 1. Находим корень проекта (на 2 папки выше от текущего файла)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))

# 2. Добавляем папку src в пути импорта (чтобы точно находил Lexer и Parser)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))

from lexer.lexer import Lexer
from parser.parser import Parser
from semantic.analyzer import SemanticAnalyzer


def run_semantic_test(src_path):
    try:
        with open(src_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # 1. Лексер
        lexer = Lexer(source)
        tokens = lexer.scan_tokens()

        # 2. Парсер
        parser = Parser(tokens)
        ast = parser.parse()
        if not ast:
            return "[PARSER ERROR] Parser failed to build AST."

        # 3. Семантика
        analyzer = SemanticAnalyzer()
        analyzer.analyze(ast)

        errors = analyzer.get_errors()
        if errors:
            return "\n".join([str(e) for e in errors])
        return "OK"

    except Exception as e:
        return f"[RUNTIME ERROR] {str(e)}"


def check_files(directory, is_valid):
    results = []
    found_files = 0

    for root, dirs, files in os.walk(directory):
        if 'unit' in root: continue  # Пропускаем папку с unit-тестами

        for filename in files:
            if not filename.endswith(".src"): continue
            found_files += 1

            src_path = os.path.join(root, filename)
            expected_path = src_path.replace(".src", ".expected")
            rel_path = os.path.relpath(src_path, directory)

            print(f"\n{'=' * 50}")
            print(f"FILE: {rel_path}")
            print(f"{'=' * 50}")

            # Всегда печатаем то, что выдал анализ
            actual = run_semantic_test(src_path)
            print(f">>> ACTUAL OUTPUT:\n{actual}\n")

            if is_valid:
                if actual == "OK":
                    print("[RESULT] PASS")
                else:
                    print("[RESULT] FAIL (Valid file generated errors)")
                    results.append(rel_path)
            else:
                if not os.path.exists(expected_path):
                    print("[RESULT] SKIP (No .expected file found)")
                    continue

                with open(expected_path, 'r', encoding='utf-8') as f:
                    expected = f.read().strip()

                print(f">>> EXPECTED OUTPUT:\n{expected}\n")

                if actual.strip() == expected:
                    print("[RESULT] PASS")
                else:
                    print("[RESULT] FAIL (Output mismatch)")
                    results.append(rel_path)

    if found_files == 0:
        print("\n[WARNING] No .src files found! Check directory paths.")

    return results


def main():
    # 3. Используем вычисленный PROJECT_ROOT
    base_dir = os.path.join(PROJECT_ROOT, "tests", "semantic")

    print(f"=== Semantic Tests (Debug Mode) ===")
    print(f"Looking in: {base_dir}\n")

    print("--- Checking VALID ---")
    fail_valid = check_files(os.path.join(base_dir, "valid"), is_valid=True)

    print("\n--- Checking INVALID ---")
    fail_invalid = check_files(os.path.join(base_dir, "invalid"), is_valid=False)

    fails = fail_valid + fail_invalid
    print("\n" + "=" * 50)
    if not fails:
        print("RESULT: ALL PASSED")
    else:
        print(f"RESULT: {len(fails)} FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()