import argparse
import json
import sys

from lexer.lexer import Lexer
from parser.parser import Parser
from parser.printer import ASTPrinter, DotPrinter
from semantic.analyzer import SemanticAnalyzer
from semantic.symbol_table import SymbolKind, SymbolTable
from ir.ir_generator import IRGenerator
from ir.optimizer import IROptimizer
from codegen.x86_generator import X86Generator


def print_symbol_table(symbol_table: SymbolTable, scope=None, indent=0):
    """Recursive symbol table dump."""
    if scope is None:
        scope = symbol_table.current_scope
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

        if sym.kind == SymbolKind.FUNCTION and sym.extra:
            for p in sym.extra:
                print(f"{prefix}      - {p.name}: {p.param_type} (parameter, line {p.line})")


def parse_source(source_code: str, verbose: bool = False):
    lexer = Lexer(source_code)
    tokens = lexer.scan_tokens()
    if verbose:
        print(f"Verbose: Scanned {len(tokens)} tokens.")
    parser = Parser(tokens)
    ast = parser.parse()
    if verbose:
        print("Verbose: AST generated successfully.")
    return tokens, ast


def analyze_ast(ast):
    analyzer = SemanticAnalyzer()
    decorated_ast = analyzer.analyze(ast)
    return analyzer, decorated_ast, analyzer.get_errors()


def build_ir(ast, optimize: bool = False):
    analyzer, decorated_ast, errors = analyze_ast(ast)
    if errors:
        return analyzer, decorated_ast, errors, None, None
    generator = IRGenerator(analyzer.symbol_table, None)
    ir_program = generator.generate(decorated_ast)
    optimizer = None
    if optimize:
        optimizer = IROptimizer()
        optimizer.optimize(ir_program)
    return analyzer, decorated_ast, [], ir_program, optimizer


def main():
    parser_args = argparse.ArgumentParser(description="MiniCompiler")
    parser_args.add_argument("command", help="Command to run: lex, parse, check, symbols, ir, compile")
    parser_args.add_argument("--input", required=True, help="Input source file")
    parser_args.add_argument("--output", "--output-file", help="Output file (optional)")
    parser_args.add_argument(
        "--format", "--ast-format",
        choices=["text", "dot", "json"],
        default="text",
        help="Output format for AST/IR",
    )
    parser_args.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser_args.add_argument("--stats", action="store_true", help="Print IR/codegen statistics")
    parser_args.add_argument("--optimize", action="store_true", help="Reserved for optimization stretch goals")
    parser_args.add_argument("--target", default="x86_64", choices=["x86_64"], help="Code generation target")
    parser_args.add_argument("--syntax", default="nasm", choices=["nasm"], help="Assembly syntax")

    args = parser_args.parse_args()
    output_content = ""

    try:
        with open(args.input, "r", encoding="utf-8") as f:
            source_code = f.read()

        lexer = Lexer(source_code)
        tokens = lexer.scan_tokens()
        if args.verbose and args.command in ["parse", "check", "symbols", "ir", "compile"]:
            print(f"Verbose: Scanned {len(tokens)} tokens.")

        ast = None
        if args.command in ["parse", "check", "symbols", "ir", "compile"]:
            parser = Parser(tokens)
            ast = parser.parse()
            if args.verbose:
                print("Verbose: AST generated successfully.")

        if args.command == "lex":
            output_content = "\n".join(str(t) for t in tokens)

        elif args.command == "parse":
            if args.format == "text":
                output_content = ASTPrinter().print(ast)
            elif args.format == "dot":
                printer = DotPrinter()
                ast.accept(printer)
                output_content = printer.get_output()
            elif args.format == "json":
                output_content = ASTPrinter(output_type="json").print(ast)

        elif args.command == "check":
            analyzer, decorated_ast, errors = analyze_ast(ast)
            error_messages = [str(err) for err in errors]
            if args.format == "json":
                output_content = json.dumps({"errors": error_messages}, indent=2)
            elif error_messages:
                output_content = "\n".join(error_messages) + f"\n\nSemantic analysis failed with {len(errors)} error(s)."
            else:
                output_content = "Semantic analysis passed! No errors found."

        elif args.command == "symbols":
            analyzer, decorated_ast, errors = analyze_ast(ast)
            if args.format == "json":
                output_content = json.dumps({"status": "Symbol table JSON dump is not implemented"}, indent=2)
            else:
                import io
                old_stdout = sys.stdout
                sys.stdout = io.StringIO()
                print_symbol_table(analyzer.symbol_table)
                output_content = sys.stdout.getvalue()
                sys.stdout = old_stdout

        elif args.command == "ir":
            analyzer, decorated_ast, errors, ir_program, optimizer = build_ir(ast, optimize=args.optimize)
            if errors:
                output_content = "\n".join(str(err) for err in errors) + f"\n\nIR generation skipped because semantic analysis failed with {len(errors)} error(s)."
            else:
                if args.format == "dot":
                    output_content = ir_program.to_dot()
                elif args.format == "json":
                    output_content = ir_program.to_json()
                else:
                    output_content = ir_program.to_text()
                if args.stats:
                    output_content += "\n" + ir_program.statistics_text() + "\n"
                    if optimizer:
                        output_content += "\n" + optimizer.stats.to_text() + "\n"

        elif args.command == "compile":
            analyzer, decorated_ast, errors, ir_program, optimizer = build_ir(ast, optimize=args.optimize)
            if errors:
                output_content = "\n".join(str(err) for err in errors) + f"\n\nCode generation skipped because semantic analysis failed with {len(errors)} error(s)."
                if args.output:
                    with open(args.output, "w", encoding="utf-8") as f:
                        f.write(output_content)
                    print(f"Output written to {args.output}")
                else:
                    print(output_content)
                sys.exit(1)

            generator = X86Generator(target=args.target, syntax=args.syntax)
            output_content = generator.generate(ir_program)
            if args.stats:
                output_content += "\n; Codegen statistics:\n"
                output_content += f"; instructions lowered: {generator.instruction_count}\n"
                output_content += f"; register allocator spills: {generator.regalloc.spill_count}\n"
                if optimizer:
                    output_content += "; " + optimizer.stats.to_text().replace("\n", "\n; ") + "\n"

        else:
            print(f"Error: Unknown command '{args.command}'")
            sys.exit(1)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
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
