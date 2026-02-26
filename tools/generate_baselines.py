import sys
import os
import glob
import io

# Добавляем src в путь
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from lexer.lexer import Lexer


def generate_for_folder(folder_path):
    files = glob.glob(os.path.join(folder_path, '*.src'))
    for src_file in files:
        with open(src_file, 'r', encoding='utf-8') as f:
            source = f.read()

        # Перехватываем stdout, чтобы сохранить и токены, и ошибки (которые печатает лексер)
        buffer = io.StringIO()

        # Сохраняем настоящий stdout
        original_stdout = sys.stdout

        try:
            # Перенаправляем вывод в буфер
            sys.stdout = buffer

            lexer = Lexer(source)
            tokens = lexer.scan_tokens()

            # Печатаем токены так же, как это делает main.py или раннер
            for t in tokens:
                print(t)

            # Получаем результат
            output = buffer.getvalue()

        finally:
            # Возвращаем stdout
            sys.stdout = original_stdout

        # Сохраняем в файл с расширением .tokens
        baseline_file = src_file + '.tokens'
        with open(baseline_file, 'w', encoding='utf-8') as f:
            f.write(output)

        print(f"Generated: {baseline_file}")


if __name__ == "__main__":
    base_path = os.path.dirname(__file__)
    valid_path = os.path.join(base_path, '../tests/lexer/valid')
    invalid_path = os.path.join(base_path, '../tests/lexer/invalid')

    print("Generating baselines for VALID tests...")
    generate_for_folder(valid_path)

    print("\nGenerating baselines for INVALID tests...")
    generate_for_folder(invalid_path)

    print("\nDone!")