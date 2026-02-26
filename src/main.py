import sys
import argparse
from lexer.lexer import Lexer


def main():
    parser = argparse.ArgumentParser(description="MiniCompiler Lexer")
    parser.add_argument('command', help="Command to run (e.g., 'lex')")
    parser.add_argument('--input', required=True, help="Input source file")
    parser.add_argument('--output', help="Output token file (optional, prints to stdout if omitted)")

    args = parser.parse_args()

    if args.command != 'lex':
        print("Error: Only 'lex' command is supported in Sprint 1.")
        sys.exit(1)

    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            source_code = f.read()

        lexer = Lexer(source_code)
        tokens = lexer.scan_tokens()

        output_content = "\n".join([str(token) for token in tokens])

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output_content)
            print(f"Tokens successfully written to {args.output}")
        else:
            print(output_content)

    except FileNotFoundError:
        print(f"Error: File '{args.input}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()