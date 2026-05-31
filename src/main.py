import sys
import argparse
from lexer.lexer import Lexer
from parser.parser import Parser
from parser.printer import ASTPrinter, DotPrinter


def main():
    parser_args = argparse.ArgumentParser(description="MiniCompiler")
    parser_args.add_argument('command', help="Command to run (lex, parse)")
    parser_args.add_argument('--input', required=True, help="Input source file")
    parser_args.add_argument('--output', '--output-file', help="Output file (optional)")
    parser_args.add_argument('--format', '--ast-format', choices=['text', 'dot', 'json'], default='text', help="Output format for AST")
    parser_args.add_argument('--verbose', action='store_true', help="Enable verbose output")

    args = parser_args.parse_args()

    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            source_code = f.read()

        # 1. Lexing
        lexer = Lexer(source_code)
        tokens = lexer.scan_tokens()

        if args.command == 'lex' and args.verbose:
            print(f"Verbose: Scanned {len(tokens)} tokens.")

        if args.command == 'lex':
            output_content = "\n".join([str(t) for t in tokens])

        elif args.command == 'parse':
            if args.verbose:
                print(f"Verbose: Passing {len(tokens)} tokens to parser...")
            # 2. Parsing
            parser = Parser(tokens)
            ast = parser.parse()

            if args.verbose:
                print(f"Verbose: AST generated successfully.")

            # 3. Visualization
            if args.format == 'text':
                printer = ASTPrinter()
                output_content = printer.print(ast)
            elif args.format == 'dot':
                printer = DotPrinter()
                ast.accept(printer)
                output_content = printer.get_output()
            elif args.format == 'json':
                printer = ASTPrinter(output_type='json')
                output_content = printer.print(ast)

        else:
            print(f"Error: Unknown command '{args.command}'")
            sys.exit(1)

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output_content)
            print(f"Output written to {args.output}")
        else:
            print(output_content)

    except FileNotFoundError:
        print(f"Error: File '{args.input}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()