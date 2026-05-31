import sys
import argparse
import json
from lexer.lexer import Lexer
from parser.parser import Parser
from parser.printer import ASTPrinter, DotPrinter
from semantic.analyzer import SemanticAnalyzer
from semantic.symbol_table import SymbolTable, Symbol, SymbolKind


def print_symbol_table(symbol_table: SymbolTable, scope=None, indent=0):
    """Рекурсивный вывод таблицы символов"""
    if scope is None:
        scope = symbol_table.current_scope
        # Для вывода глобальной таблицы после анализа нам нужно найти корень
        while scope.parent:
            scope = scope.parent

    prefix = "  " * indent
    print(f"{prefix}{scope.name}:")
    for name, sym in scope.symbols.items():
        extra_info = ""
        if sym.kind == SymbolKind.FUNCTION:
            extra_info = f" -> {sym.type.return_type}"
        elif sym.kind == SymbolKind.STRUCT:
            fields_str = ", ".join([f"{k}: {v}" for k, v in sym.extra.items()])
            extra_info = f" (fields: {fields_str})"

        print(f"{prefix}  - {name}: {sym.kind.name.lower()}{extra_info} (line {sym.line})")

        # Рекурсия для функций (чтобы показать параметры)
        # В нашей упрощенной реализации параметры лежат в SymbolTable функции,
        # но для вывода мы просто достаем их из extra
        if sym.kind == SymbolKind.FUNCTION and sym.extra:
            for p in sym.extra:
                print(f"{prefix}      - {p.name}: {p.param_type} {p.param_type} (parameter, line {p.line})")


def main():
    parser_args = argparse.ArgumentParser(description="MiniCompiler")
    parser_args.add_argument('command', help="Command to run: lex, parse, check, symbols")
    parser_args.add_argument('--input', required=True, help="Input source file")
    parser_args.add_argument('--output', '--output-file', help="Output file (optional)")
    parser_args.add_argument('--format', '--ast-format', choices=['text', 'dot', 'json'], default='text',
                             help="Output format")
    parser_args.add_argument('--verbose', action='store_true', help="Enable verbose output")

    args = parser_args.parse_args()
    output_content = ""

    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            source_code = f.read()

        # 1. Lexing
        lexer = Lexer(source_code)
        tokens = lexer.scan_tokens()
        if args.verbose and args.command in ['parse', 'check']:
            print(f"Verbose: Scanned {len(tokens)} tokens.")

        # 2. Parsing
        ast = None
        if args.command in ['parse', 'check', 'symbols']:
            parser = Parser(tokens)
            ast = parser.parse()
            if args.verbose:
                print(f"Verbose: AST generated successfully.")

        # 3. Command Execution
        if args.command == 'lex':
            output_content = "\n".join([str(t) for t in tokens])

        elif args.command == 'parse':
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

        elif args.command == 'check':
            analyzer = SemanticAnalyzer()
            decorated_ast = analyzer.analyze(ast)

            errors = analyzer.get_errors()
            error_messages = []
            for err in errors:
                error_messages.append(str(err))

            if args.format == 'json':
                output_content = json.dumps({"errors": error_messages}, indent=2)
            else:
                if error_messages:
                    output_content = "\n".join(error_messages) + "\n\nSemantic analysis failed with " + str(
                        len(errors)) + " error(s)."
                else:
                    output_content = "Semantic analysis passed! No errors found."

            if args.verbose and not error_messages:
                print("Verbose: No type errors found.")

        elif args.command == 'symbols':
            analyzer = SemanticAnalyzer()
            analyzer.analyze(ast)  # Анализ заполнит таблицу

            if args.format == 'json':
                # Заглушка для JSON дампа таблицы
                output_content = json.dumps({"status": "Symbol table dump in JSON not fully implemented in stub"},
                                            indent=2)
            else:
                # Собираем вывод таблицы в строку
                import io
                import sys
                old_stdout = sys.stdout
                sys.stdout = io.StringIO()
                print_symbol_table(analyzer.symbol_table)
                output_content = sys.stdout.getvalue()
                sys.stdout = old_stdout

        else:
            print(f"Error: Unknown command '{args.command}'")
            sys.exit(1)

        # Вывод результата
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output_content)
            if not error_messages:  # Не пишем "успешно", если были ошибки
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