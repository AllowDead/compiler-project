import sys

sys.path.insert(0, 'src')

from parser.ast_nodes import *
from .type_system import *
from .symbol_table import *
from .errors import SemanticError


class SemanticAnalyzer:
    def __init__(self):
        self.symbol_table = SymbolTable()
        self.errors = []
        self.current_function_return_type = VOID_TYPE

    def analyze(self, ast: ProgramNode) -> ProgramNode:
        self.symbol_table.enter_scope("global")

        # Pass 1: Объявляем все функции и структуры (для прямых ссылок)
        for decl in ast.declarations:
            if isinstance(decl, FunctionDeclNode):
                self._declare_function(decl)
            elif isinstance(decl, StructDeclNode):
                self._declare_struct(decl)

        # Pass 2: Проверяем тела функций и глобальные переменные
        for decl in ast.declarations:
            decl.accept(self)

        self.symbol_table.exit_scope()
        return ast

    def get_errors(self):
        return self.errors

    # --- Declaration Helpers ---

    def _declare_function(self, node: FunctionDeclNode):
        existing = self.symbol_table.lookup_local(node.name)
        if existing:
            self.errors.append(SemanticError("duplicate declaration", node.line, node.column,
                                             f"Function '{node.name}' already declared."))
            return

        # Определяем типы параметров (временные заглушки, если типы еще не проверены)
        param_types = []
        for p in node.params:
            param_types.append(self._resolve_type_name(p.param_type, node.line, node.column))

        ret_type = self._resolve_type_name(node.return_type, node.line, node.column)
        func_type = FunctionType(ret_type, param_types)

        symbol = Symbol(node.name, func_type, SymbolKind.FUNCTION, node.line, node.column, extra=node.params)
        self.symbol_table.insert(symbol)
        node.symbol = symbol

    def _declare_struct(self, node: StructDeclNode):
        existing = self.symbol_table.lookup_local(node.name)
        if existing:
            self.errors.append(SemanticError("duplicate declaration", node.line, node.column,
                                             f"Struct '{node.name}' already declared."))
            return

        # Собираем типы полей
        fields = {}
        for f in node.fields:
            fields[f.name] = self._resolve_type_name(f.var_type, f.line, f.column)

        struct_type = StructType(node.name, fields)
        symbol = Symbol(node.name, struct_type, SymbolKind.STRUCT, node.line, node.column, extra=fields)
        self.symbol_table.insert(symbol)
        node.symbol = symbol

    def _resolve_type_name(self, type_name: str, line: int, col: int) -> Type:
        if type_name == "int":
            return INT_TYPE
        elif type_name == "float":
            return FLOAT_TYPE
        elif type_name == "bool":
            return BOOL_TYPE
        elif type_name == "void":
            return VOID_TYPE
        elif type_name == "string":
            return STRING_TYPE
        else:
            # Проверяем, является ли это определенным структурой
            sym = self.symbol_table.lookup(type_name)
            if sym and sym.kind == SymbolKind.STRUCT:
                return sym.type
            self.errors.append(SemanticError("unknown type", line, col, f"Type '{type_name}' not found."))
            return ERROR_TYPE

    # --- Visitor Methods ---

    def visit_program(self, node: ProgramNode):
        pass  # Handled in analyze()

    def visit_function_decl(self, node: FunctionDeclNode):
        func_sym = self.symbol_table.lookup_local(node.name)
        if not func_sym: return  # Был удален из-за дубликата

        self.current_function_return_type = func_sym.type.return_type
        self.symbol_table.enter_scope(f"function_{node.name}")

        # Добавляем параметры в локальную область видимости
        for p in node.params:
            p_type = self._resolve_type_name(p.param_type, p.line, p.column)
            param_sym = Symbol(p.name, p_type, SymbolKind.PARAMETER, p.line, p.column)
            self.symbol_table.insert(param_sym)
            p.symbol = param_sym

        node.body.accept(self)
        self.symbol_table.exit_scope()
        self.current_function_return_type = VOID_TYPE

    def visit_struct_decl(self, node: StructDeclNode):
        pass  # Обработано в _declare_struct

    def visit_var_decl(self, node: VarDeclNode):
        var_type = self._resolve_type_name(node.var_type, node.line, node.column)

        existing = self.symbol_table.lookup_local(node.name)
        if existing:
            self.errors.append(SemanticError("duplicate declaration", node.line, node.column,
                                             f"Variable '{node.name}' already declared in this scope."))
            var_type = ERROR_TYPE

        if node.initializer:
            init_type = node.initializer.accept(self)
            if not init_type.is_assignable_to(var_type):
                self.errors.append(SemanticError("type mismatch", node.initializer.line, node.initializer.column,
                                                 f"Cannot assign {init_type} to {var_type}."))

        symbol = Symbol(node.name, var_type, SymbolKind.VARIABLE, node.line, node.column)
        self.symbol_table.insert(symbol)
        node.symbol = symbol
        node.inferred_type = var_type

    def visit_block(self, node: BlockNode):
        self.symbol_table.enter_scope("block")
        for stmt in node.statements:
            if stmt: stmt.accept(self)
        self.symbol_table.exit_scope()

    def visit_if_stmt(self, node: IfStmtNode):
        cond_type = node.condition.accept(self)
        self._expect_type(node.condition, cond_type, BOOL_TYPE, "Condition must be a boolean")
        node.then_branch.accept(self)
        if node.else_branch: node.else_branch.accept(self)

    def visit_while_stmt(self, node: WhileStmtNode):
        cond_type = node.condition.accept(self)
        self._expect_type(node.condition, cond_type, BOOL_TYPE, "Condition must be a boolean")
        node.body.accept(self)

    def visit_for_stmt(self, node: ForStmtNode):
        if node.init: node.init.accept(self)
        if node.condition:
            cond_type = node.condition.accept(self)
            self._expect_type(node.condition, cond_type, BOOL_TYPE, "Condition must be a boolean")
        if node.update: node.update.accept(self)
        node.body.accept(self)

    def visit_return_stmt(self, node: ReturnStmtNode):
        if node.value:
            ret_type = node.value.accept(self)
            if not ret_type.is_assignable_to(self.current_function_return_type):
                self.errors.append(SemanticError("invalid return type", node.line, node.column,
                                                 f"Function expects {self.current_function_return_type}, but returning {ret_type}."))
        node.inferred_type = VOID_TYPE

    def visit_expr_stmt(self, node: ExprStmtNode):
        node.expr.accept(self)

    # --- Expression Visitors (Возвращают Type) ---

    def visit_literal_expr(self, node: LiteralExprNode) -> Type:
        # bool must be checked before int because Python bool is a subclass of int.
        if isinstance(node.value, bool):
            node.inferred_type = BOOL_TYPE
        elif isinstance(node.value, int):
            node.inferred_type = INT_TYPE
        elif isinstance(node.value, float):
            node.inferred_type = FLOAT_TYPE
        elif isinstance(node.value, str):
            node.inferred_type = STRING_TYPE
        else:
            node.inferred_type = ERROR_TYPE
        return node.inferred_type

    def visit_identifier_expr(self, node: IdentifierExprNode) -> Type:
        symbol = self.symbol_table.lookup(node.name)
        if not symbol:
            self.errors.append(
                SemanticError("undeclared variable", node.line, node.column, f"Variable '{node.name}' not found."))
            node.inferred_type = ERROR_TYPE
            return ERROR_TYPE

        node.symbol = symbol
        node.inferred_type = symbol.type
        return node.inferred_type

    def visit_binary_expr(self, node: BinaryExprNode) -> Type:
        left_type = node.left.accept(self)
        right_type = node.right.accept(self)

        result_type = ERROR_TYPE

        if node.operator in ['+', '-', '*', '/', '%']:
            # Арифметика: int+int=int, иначе float
            if left_type.type_enum == TypeEnum.FLOAT or right_type.type_enum == TypeEnum.FLOAT:
                result_type = FLOAT_TYPE
            elif left_type.type_enum == TypeEnum.INT and right_type.type_enum == TypeEnum.INT:
                result_type = INT_TYPE
            else:
                self.errors.append(SemanticError("type mismatch", node.line, node.column,
                                                 f"Cannot apply '{node.operator}' to {left_type} and {right_type}."))

        elif node.operator in ['==', '!=', '<', '<=', '>', '>=']:
            # Сравнение: возвращает bool
            if left_type.is_assignable_to(right_type) or right_type.is_assignable_to(left_type):
                result_type = BOOL_TYPE
            else:
                self.errors.append(SemanticError("type mismatch", node.line, node.column,
                                                 f"Cannot compare {left_type} and {right_type}."))

        elif node.operator in ['&&', '||']:
            # Логика: строго bool
            if left_type.type_enum == TypeEnum.BOOL and right_type.type_enum == TypeEnum.BOOL:
                result_type = BOOL_TYPE
            else:
                self.errors.append(SemanticError("type mismatch", node.line, node.column,
                                                 f"Logical operators require bools, got {left_type} and {right_type}."))

        elif node.operator == '.':
            # Доступ к полю структуры
            if left_type.type_enum == TypeEnum.STRUCT and isinstance(node.right, IdentifierExprNode):
                struct_type = left_type
                field_name = node.right.name
                if field_name in struct_type.fields:
                    result_type = struct_type.fields[field_name]
                else:
                    self.errors.append(SemanticError("invalid member", node.right.line, node.right.column,
                                                     f"Struct {struct_type.name} has no field '{field_name}'."))
            else:
                self.errors.append(SemanticError("invalid member access", node.line, node.column,
                                                 f"Left side of '.' must be a struct."))

        node.inferred_type = result_type
        return result_type

    def visit_unary_expr(self, node: UnaryExprNode) -> Type:
        operand_type = node.right.accept(self)
        result_type = ERROR_TYPE

        if node.operator == '-':
            if operand_type.type_enum in (TypeEnum.INT, TypeEnum.FLOAT):
                result_type = operand_type
            else:
                self.errors.append(SemanticError("type mismatch", node.line, node.column,
                                                 f"Unary '-' requires numeric type, got {operand_type}."))
        elif node.operator == '!':
            if operand_type.type_enum == TypeEnum.BOOL:
                result_type = BOOL_TYPE
            else:
                self.errors.append(SemanticError("type mismatch", node.line, node.column,
                                                 f"Unary '!' requires bool, got {operand_type}."))

        node.inferred_type = result_type
        return result_type

    def visit_call_expr(self, node: CallExprNode) -> Type:
        if not isinstance(node.callee, IdentifierExprNode):
            self.errors.append(
                SemanticError("invalid call", node.line, node.column, "Can only call functions by name."))
            node.inferred_type = ERROR_TYPE
            return ERROR_TYPE

        func_sym = self.symbol_table.lookup(node.callee.name)
        if not func_sym or func_sym.kind != SymbolKind.FUNCTION:
            self.errors.append(SemanticError("undeclared function", node.callee.line, node.callee.column,
                                             f"Function '{node.callee.name}' not found."))
            node.inferred_type = ERROR_TYPE
            return ERROR_TYPE

        node.callee.symbol = func_sym  # Декорируем
        func_type = func_sym.type

        # Проверка количества аргументов
        if len(node.arguments) != len(func_type.param_types):
            self.errors.append(SemanticError("argument count mismatch", node.line, node.column,
                                             f"Function '{node.callee.name}' expects {len(func_type.param_types)} arguments, got {len(node.arguments)}."))
        else:
            # Проверка типов аргументов
            for i, arg in enumerate(node.arguments):
                arg_type = arg.accept(self)
                expected_type = func_type.param_types[i]
                if not arg_type.is_assignable_to(expected_type):
                    self.errors.append(SemanticError("argument type mismatch", arg.line, arg.column,
                                                     f"Argument {i + 1} expects {expected_type}, got {arg_type}."))

        node.inferred_type = func_type.return_type
        return node.inferred_type

    def visit_assignment_expr(self, node: AssignmentExprNode) -> Type:
        # LHS должна быть переменной
        if not isinstance(node.target, IdentifierExprNode):
            self.errors.append(
                SemanticError("invalid assignment target", node.line, node.column, "Can only assign to variables."))
            node.inferred_type = ERROR_TYPE
            return ERROR_TYPE

        var_sym = self.symbol_table.lookup(node.target.name)
        if not var_sym:
            node.inferred_type = ERROR_TYPE
            return ERROR_TYPE  # Ошибка уже брошена в visit_identifier_expr

        node.target.symbol = var_sym
        target_type = var_sym.type

        # Вычисляем RHS
        value_type = node.value.accept(self)

        if not value_type.is_assignable_to(target_type):
            self.errors.append(SemanticError("type mismatch in assignment", node.line, node.column,
                                             f"Cannot assign {value_type} to {target_type}."))

        node.inferred_type = target_type
        return target_type

    # --- Helpers ---
    def _expect_type(self, node, actual: Type, expected: Type, message: str):
        if not actual.is_assignable_to(expected):
            self.errors.append(SemanticError("type mismatch", node.line, node.column, f"{message}, got {actual}."))