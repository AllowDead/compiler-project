Структура проекта

├── .gitignore
├── docs
│   ├── grammar.md
│   └── language_spec.md
├── print_tree.py
├── pyproject.toml
├── README.md
├── src
│   ├── __init__.py
│   ├── ir
│   │   ├── __init__.py
│   │   ├── basic_block.py
│   │   ├── control_flow.py
│   │   ├── ir_generator.py
│   │   └── ir_instructions.py
│   ├── lexer
│   │   ├── __init__.py
│   │   ├── lexer.py
│   │   └── token.py
│   ├── main.py
│   ├── parser
│   │   ├── __init__.py
│   │   ├── ast_nodes.py
│   │   ├── parser.py
│   │   └── printer.py
│   ├── semantic
│   │   ├── analyzer.py
│   │   ├── errors.py
│   │   ├── symbol_table.py
│   │   └── type_system.py
│   └── utils
│       ├── __init__.py
│       └── error.py
└── tests
    ├── __init__.py
    ├── ir
    │   ├── __init__.py
    │   ├── generation
    │   │   ├── __init__.py
    │   │   ├── test_control_flow.py
    │   │   ├── test_expressions.py
    │   │   ├── test_functions.py
    │   │   └── test_ir_generation.py
    │   ├── utils.py
    │   └── validation
    │       ├── __init__.py
    │       ├── test_ir_validation.py
    │       ├── test_structural.py
    │       └── test_type_consistency.py
    ├── lexer
    ├── parser
    │   ├── invalid
    │   └── valid
    ├── semantic
    │   └── unit
    │       └── test_semantic_units.py
    └── test_runner
        ├── run_ir_tests.py
        ├── run_parser_tests.py
        ├── run_semantic_tests.py
        └── run_tests.py

Запуск лексера

python -m src.main lex --input examples/hello.src

Запуск тестов

python -m pytest tests/

python tests/test_runner/run_tests.py


Запуск парсера

Текстовый формат (по умолчанию):

python -m src.main parse --input examples/factorial.src

Формат JSON:

python -m src.main parse --input examples/factorial.src --ast-format json --output ast.json

Формат Graphviz DOT (для визуализации):

python -m src.main parse --input examples/factorial.src --ast-format dot --output ast.dot
dot -Tpng ast.dot -o ast.png # Требуется установленный Graphviz

Запуск семантического анализа

python -m src.semantic.analyzer --input examples/hello.src

Запуск IR 

```bash
python -m src.main ir --input examples/program.src
```

Формат Graphviz DOT (для визуализации):

```bash
python -m src.main ir --input examples/program.src --format dot --output cfg.dot
```

Формат JSON:

```bash
python -m src.main ir --input examples/program.src --format json --output program.ir.json
```

Статистика:

```bash
python -m src.main ir --input examples/program.src --stats
```

Тестирование

python tests/test_runner/run_lexer_tests.py

python tests/test_runner/run_parser_tests.py

python -m pytest tests/semantic/unit/

python tests/test_runner/run_semantic_tests.py