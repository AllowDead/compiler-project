import sys
import os
import glob
import io

# Добавляем src в путь для импорта модулей
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from lexer.lexer import Lexer


def get_lexer_output(source_code):
    """
    Запускает лексер и возвращает весь вывод (токены + ошибки в stdout) как строку.
    """
    buffer = io.StringIO()

    # Перенаправляем stdout в буфер, чтобы захватить ошибки (print)
    original_stdout = sys.stdout

    try:
        sys.stdout = buffer

        lexer = Lexer(source_code)
        tokens = lexer.scan_tokens()

        # Печатаем токены так же, как это делает main.py
        for token in tokens:
            print(token)

        # Получаем весь вывод
        return buffer.getvalue()
    finally:
        # Обязательно возвращаем stdout на место
        sys.stdout = original_stdout


def check_files(files, folder_name):
    passed_count = 0
    failed_count = 0

    print(f"\n--- Checking {folder_name} ---")

    for f in files:
        fname = os.path.basename(f)
        expected_file = f + '.tokens'

        # Если эталонного файла нет, пропускаем тест
        if not os.path.exists(expected_file):
            print(f"[SKIP] {fname} (Missing .tokens baseline file)")
            continue

        # Читаем исходный код
        with open(f, 'r', encoding='utf-8') as sf:
            source = sf.read()

        # Получаем реальный вывод лексера
        actual_output = get_lexer_output(source)

        # Читаем ожидаемый вывод (Golden Master)
        with open(expected_file, 'r', encoding='utf-8') as ef:
            expected_output = ef.read()

        # Сравниваем
        if actual_output == expected_output:
            print(f"[PASS] {fname}")
            passed_count += 1
        else:
            print(f"[FAIL] {fname}")
            failed_count += 1
            print("-" * 60)
            print(">>> Expected (from .tokens file):")
            print(expected_output)
            print(">>> Actual (from Lexer):")
            print(actual_output)
            print("-" * 60)

    return passed_count, failed_count


def main():
    base_path = os.path.dirname(__file__)
    valid_path = os.path.join(base_path, '../lexer/valid')
    invalid_path = os.path.join(base_path, '../lexer/invalid')

    # Получаем списки файлов
    valid_files = sorted(glob.glob(os.path.join(valid_path, '*.src')))
    invalid_files = sorted(glob.glob(os.path.join(invalid_path, '*.src')))

    print("=" * 60)
    print("Running Lexer Tests against Golden Master")
    print("=" * 60)

    v_pass, v_fail = check_files(valid_files, "VALID")
    i_pass, i_fail = check_files(invalid_files, "INVALID")

    total_pass = v_pass + i_pass
    total_fail = v_fail + i_fail

    print("\n" + "=" * 60)
    print(f"Results: {total_pass} passed, {total_fail} failed")
    print("=" * 60)

    if total_fail > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()