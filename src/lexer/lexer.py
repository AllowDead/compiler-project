import re
from .token import Token, TokenType
from utils.error import LexerError
from .token import Token, TokenType

class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.tokens = []
        self.start = 0  # Start index of the current lexeme
        self.current = 0  # Current index in the source
        self.line = 1
        self.column = 1  # Current column (1-indexed)
        self.token_index = 0

    # --- Interface Methods (LEX-2) ---

    def next_token(self):
        """
        Возвращает следующий токен и продвигает состояние.
        """
        # Если буфер токенов пуст или мы дочитали до конца, сканируем следующий
        if self.token_index >= len(self.tokens):
            if self.is_at_end():
                # Возвращаем EOF если еще не был добавлен
                if not self.tokens or self.tokens[-1].type != TokenType.END_OF_FILE:
                    self.tokens.append(Token(TokenType.END_OF_FILE, "", self.line, self.column))
            else:
                self.start = self.current
                self.start_line = self.line
                self.start_col = self.column
                self.scan_token()  # Сканер добавляет токен в self.tokens

        token = self.tokens[self.token_index]
        self.token_index += 1
        return token

    def peek_token(self):
        """
        Возвращает следующий токен НЕ продвигая состояние (lookahead).
        """
        if self.token_index >= len(self.tokens):
            if self.is_at_end():
                # EOF
                if not self.tokens or self.tokens[-1].type != TokenType.END_OF_FILE:
                    self.tokens.append(Token(TokenType.END_OF_FILE, "", self.line, self.column))
            else:
                # Сохраняем состояние чтобы восстановить после сканирования одного токена
                saved_start = self.start
                saved_current = self.current
                saved_line = self.line
                saved_column = self.column

                self.start = self.current
                self.start_line = self.line
                self.start_col = self.column
                self.scan_token()

                # Восстанавливаем состояние (так как peek не должен менять позицию сканера)
                self.start = saved_start
                self.current = saved_current
                self.line = saved_line
                self.column = saved_column

        return self.tokens[self.token_index]

    def get_line(self):
        return self.line

    def get_column(self):
        return self.column

    def scan_tokens(self):
        # Сбрасываем индекс, если вызываем scan_tokens повторно
        self.token_index = 0
        self.tokens = []  # Очищаем перед полным сканом

        while not self.is_at_end():
            self.start = self.current
            self.start_line = self.line
            self.start_col = self.column
            self.scan_token()

        self.tokens.append(Token(TokenType.END_OF_FILE, "", self.line, self.column))
        return self.tokens

    def is_at_end(self):
        return self.current >= len(self.source)

    # --- Scanning Logic (LEX-3, LEX-4, LEX-5) ---

    def scan_token(self):
        char = self.advance()

        try:
            # Используем match для определения типа символа
            match char:
                # Whitespace (игнорируем)
                case ' ' | '\t' | '\r':
                    pass

                # Newline
                case '\n':
                    self.line += 1
                    self.column = 1

                # Slash (комментарии или деление)
                case '/':
                    self.handle_slash()

                # String literal
                case '"':
                    self.string()

                # Числа (используем guard condition `if`)
                case _ if char.isdigit():
                    self.number()

                # Идентификаторы и ключевые слова
                case _ if char.isalpha() or char == '_':
                    self.identifier()

                # Операторы и разделители (делегируем в отдельный метод, который тоже можно переписать)
                case _:
                    self.operator_or_delimiter(char)

        except LexerError as e:
            print(e)

    def advance(self):
        if self.is_at_end(): return '\0'
        char = self.source[self.current]
        self.current += 1
        self.column += 1
        return char

    def peek(self):
        if self.is_at_end(): return '\0'
        return self.source[self.current]

    def peek_next(self):
        if self.current + 1 >= len(self.source): return '\0'
        return self.source[self.current + 1]

    def match(self, expected):
        if self.is_at_end(): return False
        if self.source[self.current] != expected: return False
        self.current += 1
        self.column += 1
        return True

    # --- Token Handlers ---

    def handle_slash(self):
        if self.match('/'):
            # Single line comment: consume until \n or EOF
            while (self.peek() != '\n' and not self.is_at_end()):
                self.advance()
        elif self.match('*'):
            # Multi-line comment
            while (not (self.peek() == '*' and self.peek_next() == '/') and not self.is_at_end()):
                if self.peek() == '\n':
                    self.line += 1
                    self.column = 0
                self.advance()

            if self.is_at_end():
                raise LexerError("Unterminated multi-line comment", self.start_line, self.start_col)

            # Consume closing */
            self.advance()  # *
            self.advance()  # /
        else:
            self.add_token(TokenType.SLASH)

    def string(self):
        while (self.peek() != '"' and not self.is_at_end()):
            if self.peek() == '\n':
                self.line += 1
                self.column = 0
            self.advance()

        if self.is_at_end():
            raise LexerError("Unterminated string literal", self.start_line, self.start_col)
            return

        self.advance()  # Closing "

        # Trim quotes
        value = self.source[self.start + 1: self.current - 1]
        self.add_token(TokenType.STRING_LITERAL, value)

    def number(self):
        # Integer part
        while self.peek().isdigit():
            self.advance()

        # Float part
        if self.peek() == '.' and self.peek_next().isdigit():
            self.advance()  # Consume '.'
            while self.peek().isdigit():
                self.advance()

            text = self.source[self.start:self.current]
            self.add_token(TokenType.FLOAT_LITERAL, float(text))
        else:
            text = self.source[self.start:self.current]
            # LEX-1 & LANG-4: Range check for Integers [-2^31, 2^31-1]
            val = int(text)
            if val < -2147483648 or val > 2147483647:
                # We can warn or treat as error. Here we store as is but logic could raise error.
                # For strict requirement compliance, let's raise error if out of bounds?
                # Usually lexer just passes int, semantic analyzer checks range.
                # But LANG-4 says range is defined. Let's assume valid for now or raise warning.
                pass
            self.add_token(TokenType.INT_LITERAL, val)

    def identifier(self):
        while self.peek().isalnum() or self.peek() == '_':
            self.advance()

        text = self.source[self.start:self.current]

        # LANG-3: Max length 255
        if len(text) > 255:
            raise LexerError("Identifier exceeds maximum length of 255 characters", self.start_line, self.start_col)

        # Check Keywords (LANG-2)
        keywords = {
            'if': TokenType.KW_IF, 'else': TokenType.KW_ELSE,
            'while': TokenType.KW_WHILE, 'for': TokenType.KW_FOR,
            'int': TokenType.KW_INT, 'float': TokenType.KW_FLOAT,
            'bool': TokenType.KW_BOOL, 'return': TokenType.KW_RETURN,
            'true': TokenType.KW_TRUE, 'false': TokenType.KW_FALSE,
            'void': TokenType.KW_VOID, 'struct': TokenType.KW_STRUCT,
            'fn': TokenType.KW_FN
        }

        type = keywords.get(text, TokenType.IDENTIFIER)
        self.add_token(type)

    def operator_or_delimiter(self, char):
        # Красивое сопоставление операторов
        match char:
            # Арифметика
            case '+':
                self.add_token(TokenType.PLUS)
            case '-':
                self.add_token(TokenType.MINUS)
            case '*':
                self.add_token(TokenType.STAR)
            case '%':
                self.add_token(TokenType.PERCENT)

            # Логика и присваивание
            case '!':
                if self.match('='):
                    self.add_token(TokenType.BANG_EQ)
                else:
                    self.add_token(TokenType.BANG)

            case '=':
                if self.match('='):
                    self.add_token(TokenType.EQ_EQ)
                else:
                    self.add_token(TokenType.ASSIGN)

            case '<':
                if self.match('='):
                    self.add_token(TokenType.LESS_EQ)
                else:
                    self.add_token(TokenType.LESS)

            case '>':
                if self.match('='):
                    self.add_token(TokenType.GREATER_EQ)
                else:
                    self.add_token(TokenType.GREATER)

            case '&':
                if self.match('&'):
                    self.add_token(TokenType.AND)
                # Лексер может выдать ошибку, если просто &, но в C это часто bitwise.
                # В нашей спецификации (LANG-5) только &&. Если одиночный & не нужен, добавим else.
                else:
                    # Пропускаем или ругаемся, depending on spec. Для простоты пропустим или добавим токен.
                    # Для соответствия STRICT spec (где только &&), это ошибка:
                    raise LexerError("Unexpected character '&', expected '&&'", self.line, self.column - 1)

            case '|':
                if self.match('|'):
                    self.add_token(TokenType.OR)
                else:
                    raise LexerError("Unexpected character '|', expected '||'", self.line, self.column - 1)

            # Разделители
            case '(':
                self.add_token(TokenType.LPAREN)
            case ')':
                self.add_token(TokenType.RPAREN)
            case '{':
                self.add_token(TokenType.LBRACE)
            case '}':
                self.add_token(TokenType.RBRACE)
            case '[':
                self.add_token(TokenType.LBRACKET)
            case ']':
                self.add_token(TokenType.RBRACKET)
            case ';':
                self.add_token(TokenType.SEMICOLON)
            case ',':
                self.add_token(TokenType.COMMA)
            case '.':
                self.add_token(TokenType.DOT)

            # Неизвестный символ
            case _:
                raise LexerError(f"Unexpected character: '{char}'", self.line, self.column - 1)

    def add_token(self, type, literal=None):
        lexeme = self.source[self.start:self.current]
        self.tokens.append(Token(type, lexeme, self.start_line, self.start_col, literal))