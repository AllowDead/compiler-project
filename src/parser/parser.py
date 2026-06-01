import sys
from typing import List

sys.path.insert(0, 'src')

from lexer.lexer import Lexer, Token, TokenType
from lexer.token import TokenType as TT
from .ast_nodes import *


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.current = 0

    def parse(self) -> ProgramNode:
        declarations = []
        while not self.is_at_end():
            if self.check(TT.RBRACE):
                print(f"[Syntax Error] Line {self.peek().line}, Col {self.peek().column}: Unexpected '}}' at top level.")
                self.advance()
                continue
            decl = self.declaration()
            if decl is not None:
                declarations.append(decl)
        return ProgramNode(1, 1, declarations)

    def peek(self) -> Token: return self.tokens[self.current]
    def previous(self) -> Token: return self.tokens[self.current - 1]
    def is_at_end(self) -> bool: return self.peek().type == TT.END_OF_FILE
    def advance(self) -> Token:
        if not self.is_at_end(): self.current += 1
        return self.previous()
    def check_next(self, type) -> bool:
        return self.current + 1 < len(self.tokens) and self.tokens[self.current + 1].type == type
    def check(self, *types) -> bool:
        return any((not self.is_at_end() and self.peek().type == t) for t in types)
    def match(self, *types) -> bool:
        for type in types:
            if self.check(type):
                self.advance(); return True
        return False
    def consume(self, type: TT, message: str) -> Token:
        if self.check(type): return self.advance()
        raise self.error(self.peek(), message)
    def error(self, token: Token, message: str) -> ParseError:
        print(f"[Syntax Error] Line {token.line}, Col {token.column}: {message}")
        self.synchronize()
        return ParseError()
    def synchronize(self):
        self.advance()
        while not self.is_at_end():
            if self.previous().type in (TT.SEMICOLON, TT.RBRACE): return
            if self.peek().type in (TT.KW_FN, TT.KW_EXTERN, TT.KW_STRUCT, TT.KW_INT, TT.KW_FLOAT, TT.KW_BOOL, TT.KW_CHAR): return
            self.advance()

    def declaration(self) -> DeclarationNode:
        try:
            if self.check(TT.RBRACE) or self.is_at_end(): return None
            if self.match(TT.KW_EXTERN): return self.extern_decl()
            if self.match(TT.KW_FN): return self.function_decl()
            if self.match(TT.KW_STRUCT): return self.struct_decl()
            if self.check_type_start():
                if self.check(TT.IDENTIFIER) and not self.check_next(TT.IDENTIFIER):
                    return self.statement()
                return self.var_decl()
            return self.statement()
        except ParseError:
            return None

    def check_type_start(self):
        return self.check(TT.KW_INT, TT.KW_FLOAT, TT.KW_BOOL, TT.KW_VOID, TT.KW_CHAR, TT.IDENTIFIER)

    def parse_type_name(self, allow_void=True) -> str:
        allowed = [TT.KW_INT, TT.KW_FLOAT, TT.KW_BOOL, TT.KW_CHAR, TT.IDENTIFIER]
        if allow_void:
            allowed.append(TT.KW_VOID)
        if self.check(*allowed):
            tok = self.advance()
            name = tok.lexeme
        else:
            raise self.error(self.peek(), "Expect type name.")
        while self.match(TT.STAR):
            name += "*"
        return name

    def parse_array_dimensions(self):
        dims = []
        while self.match(TT.LBRACKET):
            if self.check(TT.RBRACKET):
                dims.append(None)
            else:
                expr = self.expression()
                if isinstance(expr, LiteralExprNode) and isinstance(expr.value, int):
                    dims.append(expr.value)
                else:
                    dims.append(expr)
            self.consume(TT.RBRACKET, "Expect ']' after array dimension/index.")
        return dims

    def extern_decl(self) -> ExternFunctionDeclNode:
        start = self.previous()
        ret_type = self.parse_type_name(allow_void=True)
        name_tok = self.consume(TT.IDENTIFIER, "Expect external function name.")
        self.consume(TT.LPAREN, "Expect '(' after external function name.")
        params = []
        variadic = False
        if not self.check(TT.RPAREN):
            while True:
                if self.match(TT.DOT):
                    self.consume(TT.DOT, "Expect second '.' in variadic marker.")
                    self.consume(TT.DOT, "Expect third '.' in variadic marker.")
                    variadic = True
                    break
                ptype = self.parse_type_name(allow_void=True)
                if self.match(TT.LBRACKET):
                    self.consume(TT.RBRACKET, "Expect ']' for array parameter.")
                    ptype += "[]"
                pname = f"arg{len(params)}"
                if self.check(TT.IDENTIFIER):
                    pname = self.advance().lexeme
                    if self.match(TT.LBRACKET):
                        self.consume(TT.RBRACKET, "Expect ']' for array parameter.")
                        if not ptype.endswith("[]"):
                            ptype += "[]"
                params.append(ParamNode(name_tok.line, name_tok.column, ptype, pname))
                if not self.match(TT.COMMA):
                    break
        self.consume(TT.RPAREN, "Expect ')' after extern parameters.")
        self.consume(TT.SEMICOLON, "Expect ';' after extern declaration.")
        return ExternFunctionDeclNode(start.line, start.column, name_tok.lexeme, params, ret_type, variadic)

    def function_decl(self) -> FunctionDeclNode:
        name_token = self.consume(TT.IDENTIFIER, "Expect function name.")
        self.consume(TT.LPAREN, "Expect '(' after function name.")
        params = []
        if not self.check(TT.RPAREN):
            params.append(self.param())
            while self.match(TT.COMMA): params.append(self.param())
        self.consume(TT.RPAREN, "Expect ')' after parameters.")
        return_type = "void"
        if self.check_type_start(): return_type = self.parse_type_name(allow_void=True)
        self.consume(TT.LBRACE, "Expect '{' before function body.")
        body = self.block()
        return FunctionDeclNode(name_token.line, name_token.column, name_token.lexeme, params, return_type, body)

    def param(self) -> ParamNode:
        name_token = self.consume(TT.IDENTIFIER, "Expect parameter name.")
        ptype = self.parse_type_name(allow_void=True)
        if self.match(TT.LBRACKET):
            self.consume(TT.RBRACKET, "Expect ']' for array parameter.")
            ptype += "[]"
        return ParamNode(name_token.line, name_token.column, ptype, name_token.lexeme)

    def struct_decl(self) -> StructDeclNode:
        name_token = self.consume(TT.IDENTIFIER, "Expect struct name.")
        self.consume(TT.LBRACE, "Expect '{' after struct name.")
        fields = []
        while not self.check(TT.RBRACE) and not self.is_at_end(): fields.append(self.var_decl())
        self.consume(TT.RBRACE, "Expect '}' after struct body.")
        return StructDeclNode(name_token.line, name_token.column, name_token.lexeme, fields)

    def array_initializer(self):
        values = []
        self.consume(TT.LBRACE, "Expect '{' for array initializer.")
        if not self.check(TT.RBRACE):
            values.append(self.expression())
            while self.match(TT.COMMA):
                if self.check(TT.RBRACE): break
                values.append(self.expression())
        self.consume(TT.RBRACE, "Expect '}' after array initializer.")
        return values

    def var_decl(self) -> VarDeclNode:
        type_token = self.peek()
        vtype = self.parse_type_name(allow_void=True)
        name = self.consume(TT.IDENTIFIER, "Expect variable name.").lexeme
        dims = self.parse_array_dimensions()
        initializer = None
        if self.match(TT.ASSIGN):
            initializer = self.array_initializer() if self.check(TT.LBRACE) else self.expression()
        self.consume(TT.SEMICOLON, "Expect ';' after variable declaration.")
        return VarDeclNode(type_token.line, type_token.column, vtype, name, initializer, dims)

    def statement(self) -> StatementNode:
        if self.match(TT.SEMICOLON): return None
        if self.match(TT.LBRACE): return self.block()
        if self.match(TT.KW_IF): return self.if_statement()
        if self.match(TT.KW_WHILE): return self.while_statement()
        if self.match(TT.KW_FOR): return self.for_statement()
        if self.match(TT.KW_RETURN): return self.return_statement()
        return self.expression_statement()

    def block(self) -> BlockNode:
        start_token = self.previous()
        statements = []
        while not self.check(TT.RBRACE) and not self.is_at_end():
            decl = self.declaration()
            if decl: statements.append(decl)
        self.consume(TT.RBRACE, "Expect '}' after block.")
        return BlockNode(start_token.line, start_token.column, statements)

    def if_statement(self) -> IfStmtNode:
        start_token = self.previous(); self.consume(TT.LPAREN, "Expect '(' after 'if'.")
        condition = self.expression(); self.consume(TT.RPAREN, "Expect ')' after condition.")
        then_branch = self.statement(); else_branch = self.statement() if self.match(TT.KW_ELSE) else None
        return IfStmtNode(start_token.line, start_token.column, condition, then_branch, else_branch)

    def while_statement(self) -> WhileStmtNode:
        start_token = self.previous(); self.consume(TT.LPAREN, "Expect '(' after 'while'.")
        condition = self.expression(); self.consume(TT.RPAREN, "Expect ')' after condition.")
        return WhileStmtNode(start_token.line, start_token.column, condition, self.statement())

    def for_statement(self) -> ForStmtNode:
        start_token = self.previous(); self.consume(TT.LPAREN, "Expect '(' after 'for'.")
        if self.match(TT.SEMICOLON): init = None
        elif self.check_type_start(): init = self.var_decl()
        else: init = self.expression_statement()
        condition = None if self.check(TT.SEMICOLON) else self.expression()
        self.consume(TT.SEMICOLON, "Expect ';' after loop condition.")
        update = None if self.check(TT.RPAREN) else self.expression()
        self.consume(TT.RPAREN, "Expect ')' after for clauses.")
        return ForStmtNode(start_token.line, start_token.column, init, condition, update, self.statement())

    def return_statement(self) -> ReturnStmtNode:
        start_token = self.previous(); value = None if self.check(TT.SEMICOLON) else self.expression()
        self.consume(TT.SEMICOLON, "Expect ';' after return value.")
        return ReturnStmtNode(start_token.line, start_token.column, value)

    def expression_statement(self) -> ExprStmtNode:
        expr = self.expression(); self.consume(TT.SEMICOLON, "Expect ';' after expression.")
        return ExprStmtNode(expr.line, expr.column, expr)

    def expression(self) -> ExpressionNode: return self.assignment()
    def assignment(self) -> ExpressionNode:
        expr = self.logical_or()
        if self.match(TT.ASSIGN, TT.PLUS_EQ, TT.MINUS_EQ, TT.STAR_EQ, TT.SLASH_EQ, TT.PERCENT_EQ):
            op = self.previous().lexeme; value = self.assignment()
            return AssignmentExprNode(expr.line, expr.column, expr, op, value)
        return expr
    def logical_or(self) -> ExpressionNode:
        expr = self.logical_and()
        while self.match(TT.OR): expr = BinaryExprNode(expr.line, expr.column, expr, self.previous().lexeme, self.logical_and())
        return expr
    def logical_and(self) -> ExpressionNode:
        expr = self.equality()
        while self.match(TT.AND): expr = BinaryExprNode(expr.line, expr.column, expr, self.previous().lexeme, self.equality())
        return expr
    def equality(self) -> ExpressionNode:
        expr = self.relational()
        while self.match(TT.EQ_EQ, TT.BANG_EQ): expr = BinaryExprNode(expr.line, expr.column, expr, self.previous().lexeme, self.relational())
        return expr
    def relational(self) -> ExpressionNode:
        expr = self.additive()
        while self.match(TT.LESS, TT.LESS_EQ, TT.GREATER, TT.GREATER_EQ): expr = BinaryExprNode(expr.line, expr.column, expr, self.previous().lexeme, self.additive())
        return expr
    def additive(self) -> ExpressionNode:
        expr = self.multiplicative()
        while self.match(TT.PLUS, TT.MINUS): expr = BinaryExprNode(expr.line, expr.column, expr, self.previous().lexeme, self.multiplicative())
        return expr
    def multiplicative(self) -> ExpressionNode:
        expr = self.unary()
        while self.match(TT.STAR, TT.SLASH, TT.PERCENT): expr = BinaryExprNode(expr.line, expr.column, expr, self.previous().lexeme, self.unary())
        return expr
    def unary(self) -> ExpressionNode:
        if self.match(TT.MINUS, TT.BANG):
            op = self.previous().lexeme; right = self.unary()
            return UnaryExprNode(self.previous().line, self.previous().column, op, right)
        return self.primary()

    def primary(self) -> ExpressionNode:
        if self.match(TT.KW_FALSE): return LiteralExprNode(self.previous().line, self.previous().column, False)
        if self.match(TT.KW_TRUE): return LiteralExprNode(self.previous().line, self.previous().column, True)
        if self.match(TT.INT_LITERAL): return LiteralExprNode(self.previous().line, self.previous().column, int(self.previous().literal if self.previous().literal is not None else self.previous().lexeme))
        if self.match(TT.FLOAT_LITERAL): return LiteralExprNode(self.previous().line, self.previous().column, float(self.previous().literal if self.previous().literal is not None else self.previous().lexeme))
        if self.match(TT.STRING_LITERAL): return LiteralExprNode(self.previous().line, self.previous().column, self.previous().literal if self.previous().literal is not None else self.previous().lexeme)
        if self.match(TT.IDENTIFIER):
            expr = IdentifierExprNode(self.previous().line, self.previous().column, self.previous().lexeme)
            while True:
                if self.match(TT.DOT):
                    prop_name = self.consume(TT.IDENTIFIER, "Expect property name after '.'.").lexeme
                    right = IdentifierExprNode(self.previous().line, self.previous().column, prop_name)
                    expr = BinaryExprNode(self.previous().line, self.previous().column, expr, ".", right)
                elif self.match(TT.LPAREN):
                    expr = self.finish_call(expr)
                elif self.match(TT.LBRACKET):
                    index = self.expression()
                    self.consume(TT.RBRACKET, "Expect ']' after array index.")
                    expr = ArrayAccessExprNode(expr.line, expr.column, expr, index)
                else:
                    break
            return expr
        if self.match(TT.LPAREN):
            expr = self.expression(); self.consume(TT.RPAREN, "Expect ')' after expression."); return expr
        raise self.error(self.peek(), "Expect expression.")

    def finish_call(self, callee) -> CallExprNode:
        arguments = []
        if not self.check(TT.RPAREN):
            arguments.append(self.expression())
            while self.match(TT.COMMA): arguments.append(self.expression())
        self.consume(TT.RPAREN, "Expect ')' after arguments.")
        return CallExprNode(callee.line, callee.column, callee, arguments)
