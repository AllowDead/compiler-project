import sys

sys.path.insert(0, 'src')  # Для импорта лексера, если запускаем отдельно

from lexer.lexer import Lexer, Token, TokenType
from lexer.token import TokenType as TT
from .ast_nodes import *


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.current = 0

        # --- Interface ---

    def parse(self) -> ProgramNode:
        declarations = []
        while not self.is_at_end():
            # Если на верхнем уровне встретилась лишняя }
            if self.check(TT.RBRACE):
                print(f"[Syntax Error] Line {self.peek().line}, Col {self.peek().column}: Unexpected '}}' at top level.")
                self.advance()  # Съедаем её
                continue

            decl = self.declaration()
            if decl is not None:
                declarations.append(decl)

        return ProgramNode(1, 1, declarations)

    # --- Helpers ---
    def peek(self) -> Token:
        return self.tokens[self.current]

    def previous(self) -> Token:
        return self.tokens[self.current - 1]

    def is_at_end(self) -> bool:
        return self.peek().type == TT.END_OF_FILE

    def advance(self) -> Token:
        if not self.is_at_end():
            self.current += 1
        return self.previous()

    def check_next(self, type) -> bool:
        """Смотрит на токен после текущего (lookahead)."""
        if self.current + 1 >= len(self.tokens): return False
        return self.tokens[self.current + 1].type == type

    def check(self, *types) -> bool:
        """Проверяет, является ли текущий токен одним из перечисленных типов."""
        for t in types:
            if not self.is_at_end() and self.peek().type == t:
                return True
        return False

    def match(self, *types) -> bool:
        for type in types:
            if self.check(type):
                self.advance()
                return True
        return False

    def consume(self, type: TT, message: str) -> Token:
        if self.check(type): return self.advance()
        raise self.error(self.peek(), message)

    def error(self, token: Token, message: str) -> ParseError:
        # Basic Error Reporting (PAR-3)
        print(f"[Syntax Error] Line {token.line}, Col {token.column}: {message}")
        # Panic mode recovery (ERR-1): skip to semicolon or brace
        self.synchronize()
        return ParseError()

    def synchronize(self):
        # Надежная классическая реализация. Без костылей.
        # 1. Съедаем токен, на котором упали.
        self.advance()

        while not self.is_at_end():
            # 2. Если только что съели ; или } - останавливаемся.
            if self.previous().type == TT.SEMICOLON:
                return
            if self.previous().type == TT.RBRACE:
                return

            # 3. Если впереди токен, начинающий новую конструкцию - останавливаемся ПЕРЕД ним.
            if self.peek().type in (TT.KW_FN, TT.KW_STRUCT, TT.KW_INT, TT.KW_FLOAT, TT.KW_BOOL):
                return

            # 4. Иначе едем дальше.
            self.advance()

    # --- Grammar Rules ---

    # Program ::= { Declaration }
    def declaration(self) -> DeclarationNode:
        try:
            # Никаких проверок self.peek() == self.previous() тут быть не должно!
            if self.check(TT.RBRACE) or self.is_at_end():
                return None

            if self.match(TT.KW_FN): return self.function_decl()
            if self.match(TT.KW_STRUCT): return self.struct_decl()

            if self.check(TT.KW_INT, TT.KW_FLOAT, TT.KW_BOOL, TT.KW_VOID):
                return self.var_decl()

            if self.check(TT.IDENTIFIER):
                if self.check_next(TT.IDENTIFIER):
                    return self.var_decl()
                else:
                    return self.statement()

            return self.statement()

        except ParseError:
            return None

    def check_type_start(self):
        return self.check(TT.KW_INT) or self.check(TT.KW_FLOAT) or self.check(TT.KW_BOOL) or self.check(TT.IDENTIFIER)

    # FunctionDecl ::= "fn" name "(" [ params ] ")" [ "->" type ] Block
    def function_decl(self) -> FunctionDeclNode:
        # Сохраняем токен целиком
        name_token = self.consume(TT.IDENTIFIER, "Expect function name.")
        name = name_token.lexeme

        self.consume(TT.LPAREN, "Expect '(' after function name.")
        params = []
        if not self.check(TT.RPAREN):
            params.append(self.param())
            while self.match(TT.COMMA):
                params.append(self.param())
        self.consume(TT.RPAREN, "Expect ')' after parameters.")

        return_type = "void"
        # Стиль вашего файла: ) int { ... }
        if self.check(TT.KW_INT, TT.KW_FLOAT, TT.KW_BOOL, TT.KW_VOID, TT.IDENTIFIER):
            return_type = self.advance().lexeme

        self.consume(TT.LBRACE, "Expect '{' before function body.")

        body = self.block()

        # Используем name_token для координат
        return FunctionDeclNode(name_token.line, name_token.column, name, params, return_type, body)

    def param(self) -> ParamNode:
        # 1. Сначала читаем Имя параметра (например, 'n')
        name_token = self.consume(TT.IDENTIFIER, "Expect parameter name.")
        pname = name_token.lexeme

        # 2. Потом читаем Тип (например, 'int')
        if self.check(TT.KW_INT, TT.KW_FLOAT, TT.KW_BOOL, TT.KW_VOID, TT.IDENTIFIER):
            type_token = self.advance()  # Сохраняем весь токен
            ptype = type_token.lexeme  # Берем из токена только строку ("int")
        else:
            raise self.error(self.peek(), "Expect parameter type after parameter name.")

        # 3. Создаем узел.
        # ВАЖНО: Для координат используем type_token, а не строку ptype!
        return ParamNode(type_token.line, type_token.column, ptype, pname)

    # StructDecl ::= "struct" name "{" { VarDecl } "}"
    def struct_decl(self) -> StructDeclNode:
        # Сохраняем токен целиком
        name_token = self.consume(TT.IDENTIFIER, "Expect struct name.")
        name = name_token.lexeme  # Строка "Point"

        self.consume(TT.LBRACE, "Expect '{' after struct name.")
        fields = []
        while not self.check(TT.RBRACE) and not self.is_at_end():
            fields.append(self.var_decl())
        self.consume(TT.RBRACE, "Expect '}' after struct body.")

        # Используем name_token для координат
        return StructDeclNode(name_token.line, name_token.column, name, fields)

    # VarDecl ::= Type Identifier [ "=" Expr ] ";"
    def var_decl(self) -> VarDeclNode:
        # Исправлено: Позволяем типу быть ключевым словом или идентификатором
        if self.check(TT.KW_INT, TT.KW_FLOAT, TT.KW_BOOL, TT.KW_VOID, TT.IDENTIFIER):
            type_token = self.advance()
            vtype = type_token.lexeme
        else:
            raise self.error(self.peek(), "Expect type name.")

        name = self.consume(TT.IDENTIFIER, "Expect variable name.").lexeme
        initializer = None
        if self.match(TT.ASSIGN):
            initializer = self.expression()
        self.consume(TT.SEMICOLON, "Expect ';' after variable declaration.")
        return VarDeclNode(type_token.line, type_token.column, vtype, name, initializer)

    # Statement ::= Block | If | While | For | Return | ExprStmt | VarDecl
    def statement(self) -> StatementNode:
        if self.match(TT.SEMICOLON): return None
        if self.match(TT.LBRACE): return self.block()
        if self.match(TT.KW_IF): return self.if_statement()
        if self.match(TT.KW_WHILE): return self.while_statement()
        if self.match(TT.KW_FOR): return self.for_statement()
        if self.match(TT.KW_RETURN): return self.return_statement()

        # Check for VarDecl (Type Identifier ...)
        # We already handled Type start in declaration(), but if we come here directly?
        # Actually, logic in declaration() covers this.
        # If we are here, it's an Expression Statement (e.g. "foo();" or "a + b;")
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
        start_token = self.previous()
        self.consume(TT.LPAREN, "Expect '(' after 'if'.")
        condition = self.expression()
        self.consume(TT.RPAREN, "Expect ')' after condition.")
        then_branch = self.statement()
        else_branch = None
        if self.match(TT.KW_ELSE):
            else_branch = self.statement()
        return IfStmtNode(start_token.line, start_token.column, condition, then_branch, else_branch)

    def while_statement(self) -> WhileStmtNode:
        start_token = self.previous()
        self.consume(TT.LPAREN, "Expect '(' after 'while'.")
        condition = self.expression()
        self.consume(TT.RPAREN, "Expect ')' after condition.")
        body = self.statement()
        return WhileStmtNode(start_token.line, start_token.column, condition, body)

    def for_statement(self) -> ForStmtNode:
        start_token = self.previous()
        self.consume(TT.LPAREN, "Expect '(' after 'for'.")

        # Init
        init = None
        if self.match(TT.SEMICOLON):
            init = None
        elif self.check_type_start():
            init = self.var_decl()
        else:
            init = self.expression_statement()

        # Condition
        condition = None
        if not self.check(TT.SEMICOLON):
            condition = self.expression()
        self.consume(TT.SEMICOLON, "Expect ';' after loop condition.")

        # Update
        update = None
        if not self.check(TT.RPAREN):
            update = self.expression()
        self.consume(TT.RPAREN, "Expect ')' after for clauses.")

        body = self.statement()

        # Desugaring is usually done in later stages, here we just store the raw structure
        return ForStmtNode(start_token.line, start_token.column, init, condition, update, body)

    def return_statement(self) -> ReturnStmtNode:
        start_token = self.previous()
        value = None
        if not self.check(TT.SEMICOLON):
            value = self.expression()
        self.consume(TT.SEMICOLON, "Expect ';' after return value.")
        return ReturnStmtNode(start_token.line, start_token.column, value)

    def expression_statement(self) -> ExprStmtNode:
        expr = self.expression()
        self.consume(TT.SEMICOLON, "Expect ';' after expression.")
        return ExprStmtNode(expr.line, expr.column, expr)

    # Expression Precedence (Bottom-Up Implementation via recursive calls)
    def expression(self) -> ExpressionNode:
        return self.assignment()

    def assignment(self) -> ExpressionNode:
        expr = self.logical_or()
        # ИСПРАВЛЕНИЕ: Добавлен забытый TT.PERCENT_EQ
        if self.match(TT.ASSIGN, TT.PLUS_EQ, TT.MINUS_EQ, TT.STAR_EQ, TT.SLASH_EQ, TT.PERCENT_EQ):
            op = self.previous().lexeme
            if not isinstance(expr, IdentifierExprNode):
                pass
            value = self.assignment()
            return AssignmentExprNode(expr.line, expr.column, expr, op, value)
        return expr

    def logical_or(self) -> ExpressionNode:
        expr = self.logical_and()
        while self.match(TT.OR):
            op = self.previous().lexeme
            right = self.logical_and()
            expr = BinaryExprNode(expr.line, expr.column, expr, op, right)
        return expr

    def logical_and(self) -> ExpressionNode:
        expr = self.equality()
        while self.match(TT.AND):
            op = self.previous().lexeme
            right = self.equality()
            expr = BinaryExprNode(expr.line, expr.column, expr, op, right)
        return expr

    def equality(self) -> ExpressionNode:
        expr = self.relational()
        while self.match(TT.EQ_EQ, TT.BANG_EQ):
            op = self.previous().lexeme
            right = self.relational()
            expr = BinaryExprNode(expr.line, expr.column, expr, op, right)
        return expr

    def relational(self) -> ExpressionNode:
        expr = self.additive()
        while self.match(TT.LESS, TT.LESS_EQ, TT.GREATER, TT.GREATER_EQ):
            op = self.previous().lexeme
            right = self.additive()
            expr = BinaryExprNode(expr.line, expr.column, expr, op, right)
        return expr

    def additive(self) -> ExpressionNode:
        expr = self.multiplicative()
        while self.match(TT.PLUS, TT.MINUS):
            op = self.previous().lexeme
            right = self.multiplicative()
            expr = BinaryExprNode(expr.line, expr.column, expr, op, right)
        return expr

    def multiplicative(self) -> ExpressionNode:
        expr = self.unary()
        while self.match(TT.STAR, TT.SLASH, TT.PERCENT):
            op = self.previous().lexeme
            right = self.unary()
            expr = BinaryExprNode(expr.line, expr.column, expr, op, right)
        return expr

    def unary(self) -> ExpressionNode:
        if self.match(TT.MINUS, TT.BANG):
            op = self.previous().lexeme
            right = self.unary()
            return UnaryExprNode(self.previous().line, self.previous().column, op, right)
        return self.primary()

    def primary(self) -> ExpressionNode:
        # 1. Булевы литералы
        if self.match(TT.KW_FALSE):
            return LiteralExprNode(self.previous().line, self.previous().column, False)
        if self.match(TT.KW_TRUE):
            return LiteralExprNode(self.previous().line, self.previous().column, True)

        # Заглушка (на случай, если KW_INT встретится как значение, а не тип)
        if self.match(TT.KW_INT):
            return LiteralExprNode(self.previous().line, self.previous().column, None)

        # 2. Числовые и строковые литералы
        if self.match(TT.INT_LITERAL):
            return LiteralExprNode(self.previous().line, self.previous().column, int(self.previous().lexeme))
        if self.match(TT.FLOAT_LITERAL):
            return LiteralExprNode(self.previous().line, self.previous().column, float(self.previous().lexeme))
        if self.match(TT.STRING_LITERAL):
            return LiteralExprNode(self.previous().line, self.previous().column, self.previous().lexeme)

        # 3. Идентификаторы (переменные, доступ к полям, вызовы функций)
        if self.match(TT.IDENTIFIER):
            # Создаем узел для текущего идентификатора (например, "origin")
            expr = IdentifierExprNode(self.previous().line, self.previous().column, self.previous().lexeme)

            # Цикл для обработки цепочек: origin.x.y или foo()()
            while True:
                if self.match(TT.DOT):
                    # Доступ к полю: object.property
                    # Читаем имя свойства (например, "x")
                    prop_name = self.consume(TT.IDENTIFIER, "Expect property name after '.'.").lexeme
                    # Создаем узел для свойства
                    right = IdentifierExprNode(self.previous().line, self.previous().column, prop_name)
                    # Создаем бинарный узел (Left . Right)
                    expr = BinaryExprNode(self.previous().line, self.previous().column, expr, ".", right)

                elif self.match(TT.LPAREN):
                    # Вызов функции: foo()
                    expr = self.finish_call(expr)

                else:
                    # Если нет точки и скобки, выражение закончено
                    break

            return expr

        # 4. Скобки (a + b)
        if self.match(TT.LPAREN):
            expr = self.expression()
            self.consume(TT.RPAREN, "Expect ')' after expression.")
            return expr

        # Если ничего не подошло - ошибка
        raise self.error(self.peek(), "Expect expression.")

    def finish_call(self, callee: IdentifierExprNode) -> CallExprNode:
        arguments = []
        if not self.check(TT.RPAREN):
            arguments.append(self.expression())
            while self.match(TT.COMMA):
                arguments.append(self.expression())
        self.consume(TT.RPAREN, "Expect ')' after arguments.")
        return CallExprNode(callee.line, callee.column, callee, arguments)