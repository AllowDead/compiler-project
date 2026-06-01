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
        self._declare_builtin_externals()
        for decl in ast.declarations:
            if isinstance(decl, ExternFunctionDeclNode):
                self._declare_extern_function(decl)
            elif isinstance(decl, FunctionDeclNode):
                self._declare_function(decl)
            elif isinstance(decl, StructDeclNode):
                self._declare_struct(decl)
        for decl in ast.declarations:
            decl.accept(self)
        self.symbol_table.exit_scope()
        return ast

    def get_errors(self):
        return self.errors

    def _declare_builtin_externals(self):
        builtins = {
            "printf": FunctionType(INT_TYPE, [STRING_TYPE], variadic=True, external=True),
            "puts": FunctionType(INT_TYPE, [STRING_TYPE], external=True),
            "getchar": FunctionType(INT_TYPE, [], external=True),
            "scanf": FunctionType(INT_TYPE, [STRING_TYPE], variadic=True, external=True),
            "malloc": FunctionType(PointerType(VOID_TYPE), [INT_TYPE], external=True),
            "free": FunctionType(VOID_TYPE, [PointerType(VOID_TYPE)], external=True),
            "memcpy": FunctionType(PointerType(VOID_TYPE), [PointerType(VOID_TYPE), PointerType(VOID_TYPE), INT_TYPE], external=True),
            "memset": FunctionType(PointerType(VOID_TYPE), [PointerType(VOID_TYPE), INT_TYPE, INT_TYPE], external=True),
            "strlen": FunctionType(INT_TYPE, [STRING_TYPE], external=True),
            "strcpy": FunctionType(PointerType(VOID_TYPE), [PointerType(VOID_TYPE), STRING_TYPE], external=True),
            "strcmp": FunctionType(INT_TYPE, [STRING_TYPE, STRING_TYPE], external=True),
            "pow": FunctionType(FLOAT_TYPE, [FLOAT_TYPE, FLOAT_TYPE], external=True),
            "sqrt": FunctionType(FLOAT_TYPE, [FLOAT_TYPE], external=True),
            "sin": FunctionType(FLOAT_TYPE, [FLOAT_TYPE], external=True),
            "cos": FunctionType(FLOAT_TYPE, [FLOAT_TYPE], external=True),
        }
        for name, ftype in builtins.items():
            if not self.symbol_table.lookup_local(name):
                self.symbol_table.insert(Symbol(name, ftype, SymbolKind.FUNCTION, 0, 0, extra=[]))

    def _resolve_type_name(self, type_name: str, line: int, col: int) -> Type:
        text = str(type_name)
        if text.endswith("[]"):
            return PointerType(self._resolve_type_name(text[:-2], line, col))
        if text.endswith("*"):
            return PointerType(self._resolve_type_name(text[:-1], line, col))
        if "[" in text and text.endswith("]"):
            import re
            dims = [int(x) for x in re.findall(r"\[(\d+)\]", text)]
            base = re.sub(r"\[\d+\]", "", text)
            return ArrayType(self._resolve_type_name(base, line, col), dims)
        if text == "int": return INT_TYPE
        if text == "float": return FLOAT_TYPE
        if text == "bool": return BOOL_TYPE
        if text == "void": return VOID_TYPE
        if text == "char": return BaseType(TypeEnum.INT)
        if text == "string": return STRING_TYPE
        if text == "ptr": return PointerType(VOID_TYPE)
        sym = self.symbol_table.lookup(text)
        if sym and sym.kind == SymbolKind.STRUCT:
            return sym.type
        self.errors.append(SemanticError("unknown type", line, col, f"Type '{type_name}' not found."))
        return ERROR_TYPE

    def _decorate_array_type(self, node: VarDeclNode, base_type: str) -> str:
        if getattr(node, "array_dimensions", None):
            return base_type + "".join(f"[{d}]" for d in node.array_dimensions if d is not None)
        return base_type

    def _declare_function(self, node: FunctionDeclNode):
        if self.symbol_table.lookup_local(node.name):
            self.errors.append(SemanticError("duplicate declaration", node.line, node.column, f"Function '{node.name}' already declared.")); return
        param_types = [self._resolve_type_name(p.param_type, node.line, node.column) for p in node.params]
        ret_type = self._resolve_type_name(node.return_type, node.line, node.column)
        symbol = Symbol(node.name, FunctionType(ret_type, param_types), SymbolKind.FUNCTION, node.line, node.column, extra=node.params)
        self.symbol_table.insert(symbol); node.symbol = symbol

    def _declare_extern_function(self, node: ExternFunctionDeclNode):
        existing = self.symbol_table.lookup_local(node.name)
        if existing and getattr(existing.type, "external", False):
            existing.type = FunctionType(self._resolve_type_name(node.return_type, node.line, node.column), [self._resolve_type_name(p.param_type, p.line, p.column) for p in node.params], node.variadic, True)
            existing.extra = node.params
            node.symbol = existing
            return
        if existing:
            self.errors.append(SemanticError("duplicate declaration", node.line, node.column, f"Function '{node.name}' already declared.")); return
        symbol = Symbol(node.name, FunctionType(self._resolve_type_name(node.return_type, node.line, node.column), [self._resolve_type_name(p.param_type, p.line, p.column) for p in node.params], node.variadic, True), SymbolKind.FUNCTION, node.line, node.column, extra=node.params)
        self.symbol_table.insert(symbol); node.symbol = symbol

    def _declare_struct(self, node: StructDeclNode):
        if self.symbol_table.lookup_local(node.name):
            self.errors.append(SemanticError("duplicate declaration", node.line, node.column, f"Struct '{node.name}' already declared.")); return
        fields = {f.name: self._resolve_type_name(self._decorate_array_type(f, f.var_type), f.line, f.column) for f in node.fields}
        struct_type = StructType(node.name, fields)
        symbol = Symbol(node.name, struct_type, SymbolKind.STRUCT, node.line, node.column, extra=fields)
        self.symbol_table.insert(symbol); node.symbol = symbol

    def visit_program(self, node: ProgramNode): pass
    def visit_extern_function_decl(self, node: ExternFunctionDeclNode): pass
    def visit_struct_decl(self, node: StructDeclNode): pass

    def visit_function_decl(self, node: FunctionDeclNode):
        if isinstance(node, ExternFunctionDeclNode): return
        func_sym = self.symbol_table.lookup_local(node.name)
        if not func_sym: return
        self.current_function_return_type = func_sym.type.return_type
        self.symbol_table.enter_scope(f"function_{node.name}")
        for p in node.params:
            p_type = self._resolve_type_name(p.param_type, p.line, p.column)
            param_sym = Symbol(p.name, p_type, SymbolKind.PARAMETER, p.line, p.column)
            self.symbol_table.insert(param_sym); p.symbol = param_sym
        node.body.accept(self)
        self.symbol_table.exit_scope(); self.current_function_return_type = VOID_TYPE

    def visit_var_decl(self, node: VarDeclNode):
        full_type = self._decorate_array_type(node, node.var_type)
        var_type = self._resolve_type_name(full_type, node.line, node.column)
        if self.symbol_table.lookup_local(node.name):
            self.errors.append(SemanticError("duplicate declaration", node.line, node.column, f"Variable '{node.name}' already declared in this scope.")); var_type = ERROR_TYPE
        if isinstance(node.initializer, list):
            if var_type.type_enum != TypeEnum.ARRAY:
                self.errors.append(SemanticError("type mismatch", node.line, node.column, "Array initializer requires array declaration."))
            else:
                if len(node.initializer) > var_type.dimensions[0]:
                    self.errors.append(SemanticError("array bounds", node.line, node.column, "Too many elements in array initializer."))
                for init in node.initializer:
                    init_type = init.accept(self)
                    if not init_type.is_assignable_to(var_type.element_type):
                        self.errors.append(SemanticError("type mismatch", init.line, init.column, f"Cannot initialize array element {var_type.element_type} with {init_type}."))
        elif node.initializer:
            init_type = node.initializer.accept(self)
            if not init_type.is_assignable_to(var_type):
                self.errors.append(SemanticError("type mismatch", node.initializer.line, node.initializer.column, f"Cannot assign {init_type} to {var_type}."))
        symbol = Symbol(node.name, var_type, SymbolKind.VARIABLE, node.line, node.column)
        self.symbol_table.insert(symbol); node.symbol = symbol; node.inferred_type = var_type

    def visit_block(self, node: BlockNode):
        self.symbol_table.enter_scope("block")
        for stmt in node.statements:
            if stmt: stmt.accept(self)
        self.symbol_table.exit_scope()

    def visit_if_stmt(self, node: IfStmtNode):
        cond_type = node.condition.accept(self); self._expect_type(node.condition, cond_type, BOOL_TYPE, "Condition must be a boolean")
        node.then_branch.accept(self)
        if node.else_branch: node.else_branch.accept(self)
    def visit_while_stmt(self, node: WhileStmtNode):
        cond_type = node.condition.accept(self); self._expect_type(node.condition, cond_type, BOOL_TYPE, "Condition must be a boolean")
        node.body.accept(self)
    def visit_for_stmt(self, node: ForStmtNode):
        self.symbol_table.enter_scope("for")
        if node.init: node.init.accept(self)
        if node.condition:
            cond_type = node.condition.accept(self); self._expect_type(node.condition, cond_type, BOOL_TYPE, "Condition must be a boolean")
        if node.update: node.update.accept(self)
        node.body.accept(self)
        self.symbol_table.exit_scope()
    def visit_return_stmt(self, node: ReturnStmtNode):
        if node.value:
            ret_type = node.value.accept(self)
            if not ret_type.is_assignable_to(self.current_function_return_type):
                self.errors.append(SemanticError("invalid return type", node.line, node.column, f"Function expects {self.current_function_return_type}, but returning {ret_type}."))
        node.inferred_type = VOID_TYPE
    def visit_expr_stmt(self, node: ExprStmtNode): node.expr.accept(self)

    def visit_literal_expr(self, node: LiteralExprNode) -> Type:
        if isinstance(node.value, bool): node.inferred_type = BOOL_TYPE
        elif isinstance(node.value, int): node.inferred_type = INT_TYPE
        elif isinstance(node.value, float): node.inferred_type = FLOAT_TYPE
        elif isinstance(node.value, str): node.inferred_type = STRING_TYPE
        else: node.inferred_type = ERROR_TYPE
        return node.inferred_type

    def visit_identifier_expr(self, node: IdentifierExprNode) -> Type:
        symbol = self.symbol_table.lookup(node.name)
        if not symbol:
            self.errors.append(SemanticError("undeclared variable", node.line, node.column, f"Variable '{node.name}' not found.")); node.inferred_type = ERROR_TYPE; return ERROR_TYPE
        node.symbol = symbol
        if symbol.type.type_enum == TypeEnum.ARRAY:
            node.inferred_type = symbol.type.decay_to_pointer()
        else:
            node.inferred_type = symbol.type
        return node.inferred_type

    def visit_array_access_expr(self, node: ArrayAccessExprNode) -> Type:
        base_type = node.array.accept(self)
        idx_type = node.index.accept(self)
        self._expect_type(node.index, idx_type, INT_TYPE, "Array index must be int")
        if base_type.type_enum == TypeEnum.ARRAY:
            result = base_type.element_type
        elif base_type.type_enum == TypeEnum.POINTER:
            result = base_type.pointee
        else:
            self.errors.append(SemanticError("type mismatch", node.line, node.column, f"Cannot index non-array type {base_type}.")); result = ERROR_TYPE
        node.inferred_type = result
        return result

    def visit_binary_expr(self, node: BinaryExprNode) -> Type:
        left_type = node.left.accept(self); right_type = node.right.accept(self); result_type = ERROR_TYPE
        if node.operator in ['+', '-', '*', '/', '%']:
            if left_type.type_enum == TypeEnum.FLOAT or right_type.type_enum == TypeEnum.FLOAT: result_type = FLOAT_TYPE
            elif left_type.type_enum == TypeEnum.INT and right_type.type_enum == TypeEnum.INT: result_type = INT_TYPE
            else: self.errors.append(SemanticError("type mismatch", node.line, node.column, f"Cannot apply '{node.operator}' to {left_type} and {right_type}."))
        elif node.operator in ['==', '!=', '<', '<=', '>', '>=']:
            if left_type.is_assignable_to(right_type) or right_type.is_assignable_to(left_type): result_type = BOOL_TYPE
            else: self.errors.append(SemanticError("type mismatch", node.line, node.column, f"Cannot compare {left_type} and {right_type}."))
        elif node.operator in ['&&', '||']:
            if left_type.type_enum == TypeEnum.BOOL and right_type.type_enum == TypeEnum.BOOL: result_type = BOOL_TYPE
            else: self.errors.append(SemanticError("type mismatch", node.line, node.column, f"Logical operators require bools, got {left_type} and {right_type}."))
        elif node.operator == '.':
            if left_type.type_enum == TypeEnum.STRUCT and isinstance(node.right, IdentifierExprNode):
                result_type = left_type.fields.get(node.right.name, ERROR_TYPE)
                if result_type == ERROR_TYPE: self.errors.append(SemanticError("invalid member", node.right.line, node.right.column, f"Struct {left_type.name} has no field '{node.right.name}'."))
            else: self.errors.append(SemanticError("invalid member access", node.line, node.column, "Left side of '.' must be a struct."))
        node.inferred_type = result_type; return result_type

    def visit_unary_expr(self, node: UnaryExprNode) -> Type:
        operand_type = node.right.accept(self); result_type = ERROR_TYPE
        if node.operator == '-':
            if operand_type.type_enum in (TypeEnum.INT, TypeEnum.FLOAT): result_type = operand_type
            else: self.errors.append(SemanticError("type mismatch", node.line, node.column, f"Unary '-' requires numeric type, got {operand_type}."))
        elif node.operator == '!':
            if operand_type.type_enum == TypeEnum.BOOL: result_type = BOOL_TYPE
            else: self.errors.append(SemanticError("type mismatch", node.line, node.column, f"Unary '!' requires bool, got {operand_type}."))
        node.inferred_type = result_type; return result_type

    def visit_call_expr(self, node: CallExprNode) -> Type:
        if not isinstance(node.callee, IdentifierExprNode):
            self.errors.append(SemanticError("invalid call", node.line, node.column, "Can only call functions by name.")); node.inferred_type = ERROR_TYPE; return ERROR_TYPE
        func_sym = self.symbol_table.lookup(node.callee.name)
        if not func_sym or func_sym.kind != SymbolKind.FUNCTION:
            self.errors.append(SemanticError("undeclared function", node.callee.line, node.callee.column, f"Function '{node.callee.name}' not found.")); node.inferred_type = ERROR_TYPE; return ERROR_TYPE
        node.callee.symbol = func_sym; func_type = func_sym.type
        fixed = len(func_type.param_types)
        if (not func_type.variadic and len(node.arguments) != fixed) or (func_type.variadic and len(node.arguments) < fixed):
            self.errors.append(SemanticError("argument count mismatch", node.line, node.column, f"Function '{node.callee.name}' expects {'at least ' if func_type.variadic else ''}{fixed} arguments, got {len(node.arguments)}."))
        for i, arg in enumerate(node.arguments[:fixed]):
            arg_type = arg.accept(self); expected = func_type.param_types[i]
            if expected.type_enum == TypeEnum.POINTER and arg_type.type_enum == TypeEnum.ARRAY: arg_type = arg_type.decay_to_pointer()
            if not arg_type.is_assignable_to(expected):
                self.errors.append(SemanticError("argument type mismatch", arg.line, arg.column, f"Argument {i + 1} expects {expected}, got {arg_type}."))
        for arg in node.arguments[fixed:]: arg.accept(self)
        node.inferred_type = func_type.return_type; return node.inferred_type

    def visit_assignment_expr(self, node: AssignmentExprNode) -> Type:
        if isinstance(node.target, ArrayAccessExprNode):
            target_type = node.target.accept(self)
        elif isinstance(node.target, IdentifierExprNode):
            var_sym = self.symbol_table.lookup(node.target.name)
            if not var_sym: node.inferred_type = ERROR_TYPE; return ERROR_TYPE
            node.target.symbol = var_sym; target_type = var_sym.type
        else:
            self.errors.append(SemanticError("invalid assignment target", node.line, node.column, "Can only assign to variables or array elements.")); node.inferred_type = ERROR_TYPE; return ERROR_TYPE
        value_type = node.value.accept(self)
        if not value_type.is_assignable_to(target_type):
            self.errors.append(SemanticError("type mismatch in assignment", node.line, node.column, f"Cannot assign {value_type} to {target_type}."))
        node.inferred_type = target_type; return target_type

    def _expect_type(self, node, actual: Type, expected: Type, message: str):
        if not actual.is_assignable_to(expected):
            self.errors.append(SemanticError("type mismatch", node.line, node.column, f"{message}, got {actual}."))
