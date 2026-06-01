from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Optional

# === Base Classes ===

class ASTNode(ABC):
    def __init__(self, line: int, column: int):
        self.line = line
        self.column = column

    @abstractmethod
    def accept(self, visitor: 'Visitor'):
        pass

class Visitor(ABC):
    @abstractmethod
    def visit_program(self, node: 'ProgramNode'): pass
    @abstractmethod
    def visit_function_decl(self, node: 'FunctionDeclNode'): pass
    def visit_extern_function_decl(self, node: 'ExternFunctionDeclNode'): pass
    @abstractmethod
    def visit_struct_decl(self, node: 'StructDeclNode'): pass
    @abstractmethod
    def visit_var_decl(self, node: 'VarDeclNode'): pass
    @abstractmethod
    def visit_param(self, node: 'ParamNode'): pass
    @abstractmethod
    def visit_block(self, node: 'BlockNode'): pass
    @abstractmethod
    def visit_expr_stmt(self, node: 'ExprStmtNode'): pass
    @abstractmethod
    def visit_if_stmt(self, node: 'IfStmtNode'): pass
    @abstractmethod
    def visit_while_stmt(self, node: 'WhileStmtNode'): pass
    @abstractmethod
    def visit_for_stmt(self, node: 'ForStmtNode'): pass
    @abstractmethod
    def visit_return_stmt(self, node: 'ReturnStmtNode'): pass
    @abstractmethod
    def visit_binary_expr(self, node: 'BinaryExprNode'): pass
    @abstractmethod
    def visit_unary_expr(self, node: 'UnaryExprNode'): pass
    @abstractmethod
    def visit_literal_expr(self, node: 'LiteralExprNode'): pass
    @abstractmethod
    def visit_identifier_expr(self, node: 'IdentifierExprNode'): pass
    @abstractmethod
    def visit_call_expr(self, node: 'CallExprNode'): pass
    @abstractmethod
    def visit_assignment_expr(self, node: 'AssignmentExprNode'): pass
    def visit_array_access_expr(self, node: 'ArrayAccessExprNode'): pass

# === Declaration Nodes ===

class ProgramNode(ASTNode):
    def __init__(self, line: int, column: int, declarations: List['DeclarationNode']):
        super().__init__(line, column)
        self.declarations = declarations
    def accept(self, visitor: Visitor): return visitor.visit_program(self)

class FunctionDeclNode(ASTNode):
    def __init__(self, line: int, column: int, name: str, params, return_type: str, body):
        super().__init__(line, column)
        self.name = name
        self.params = params
        self.return_type = return_type
        self.body = body
    def accept(self, visitor: Visitor): return visitor.visit_function_decl(self)

class ExternFunctionDeclNode(ASTNode):
    def __init__(self, line: int, column: int, name: str, params, return_type: str, variadic: bool = False):
        super().__init__(line, column)
        self.name = name
        self.params = params
        self.return_type = return_type
        self.variadic = variadic
        self.body = None
    def accept(self, visitor: Visitor):
        if hasattr(visitor, 'visit_extern_function_decl'):
            return visitor.visit_extern_function_decl(self)
        return visitor.visit_function_decl(self)

class StructDeclNode(ASTNode):
    def __init__(self, line: int, column: int, name: str, fields: List):
        super().__init__(line, column)
        self.name = name
        self.fields = fields
    def accept(self, visitor: Visitor): return visitor.visit_struct_decl(self)

class VarDeclNode(ASTNode):
    def __init__(self, line: int, column: int, var_type: str, name: str, initializer, array_dimensions=None):
        super().__init__(line, column)
        self.var_type = var_type
        self.name = name
        self.initializer = initializer
        self.array_dimensions = array_dimensions or []
    def accept(self, visitor: Visitor): return visitor.visit_var_decl(self)

# === Statement Nodes ===

class BlockNode(ASTNode):
    def __init__(self, line: int, column: int, statements: List['StatementNode']):
        super().__init__(line, column)
        self.statements = statements
    def accept(self, visitor: Visitor): return visitor.visit_block(self)

class ExprStmtNode(ASTNode):
    def __init__(self, line: int, column: int, expr):
        super().__init__(line, column)
        self.expr = expr
    def accept(self, visitor: Visitor): return visitor.visit_expr_stmt(self)

class IfStmtNode(ASTNode):
    def __init__(self, line: int, column: int, condition, then_branch, else_branch):
        super().__init__(line, column)
        self.condition = condition
        self.then_branch = then_branch
        self.else_branch = else_branch
    def accept(self, visitor: Visitor): return visitor.visit_if_stmt(self)

class WhileStmtNode(ASTNode):
    def __init__(self, line: int, column: int, condition, body):
        super().__init__(line, column)
        self.condition = condition
        self.body = body
    def accept(self, visitor: Visitor): return visitor.visit_while_stmt(self)

class ForStmtNode(ASTNode):
    def __init__(self, line: int, column: int, init, condition, update, body):
        super().__init__(line, column)
        self.init = init
        self.condition = condition
        self.update = update
        self.body = body
    def accept(self, visitor: Visitor): return visitor.visit_for_stmt(self)

class ReturnStmtNode(ASTNode):
    def __init__(self, line: int, column: int, value):
        super().__init__(line, column)
        self.value = value
    def accept(self, visitor: Visitor): return visitor.visit_return_stmt(self)

# === Expression Nodes ===

class LiteralExprNode(ASTNode):
    def __init__(self, line: int, column: int, value: Any):
        super().__init__(line, column)
        self.value = value
    def accept(self, visitor: Visitor): return visitor.visit_literal_expr(self)

class IdentifierExprNode(ASTNode):
    def __init__(self, line: int, column: int, name: str):
        super().__init__(line, column)
        self.name = name
    def accept(self, visitor: Visitor): return visitor.visit_identifier_expr(self)

class BinaryExprNode(ASTNode):
    def __init__(self, line: int, column: int, left, operator: str, right):
        super().__init__(line, column)
        self.left = left
        self.operator = operator
        self.right = right
    def accept(self, visitor: Visitor): return visitor.visit_binary_expr(self)

class UnaryExprNode(ASTNode):
    def __init__(self, line: int, column: int, operator: str, right):
        super().__init__(line, column)
        self.operator = operator
        self.right = right
    def accept(self, visitor: Visitor): return visitor.visit_unary_expr(self)

class CallExprNode(ASTNode):
    def __init__(self, line: int, column: int, callee, arguments: List['ExpressionNode']):
        super().__init__(line, column)
        self.callee = callee
        self.arguments = arguments
    def accept(self, visitor: Visitor): return visitor.visit_call_expr(self)

class ArrayAccessExprNode(ASTNode):
    def __init__(self, line: int, column: int, array, index):
        super().__init__(line, column)
        self.array = array
        self.index = index
    def accept(self, visitor: Visitor):
        return visitor.visit_array_access_expr(self)

class AssignmentExprNode(ASTNode):
    def __init__(self, line: int, column: int, target, operator: str, value):
        super().__init__(line, column)
        self.target = target
        self.operator = operator
        self.value = value
    def accept(self, visitor: Visitor): return visitor.visit_assignment_expr(self)

class ParamNode(ASTNode):
    def __init__(self, line: int, column: int, param_type: str, name: str):
        super().__init__(line, column)
        self.param_type = param_type
        self.name = name

    def accept(self, visitor: Visitor):
        return visitor.visit_param(self)

# Type aliases for clarity
DeclarationNode = FunctionDeclNode | ExternFunctionDeclNode | StructDeclNode | VarDeclNode
StatementNode = BlockNode | ExprStmtNode | IfStmtNode | WhileStmtNode | ForStmtNode | ReturnStmtNode | VarDeclNode
ExpressionNode = BinaryExprNode | UnaryExprNode | LiteralExprNode | IdentifierExprNode | CallExprNode | AssignmentExprNode | ArrayAccessExprNode