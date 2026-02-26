from enum import Enum, auto
from dataclasses import dataclass

class TokenType(Enum):
    # Keywords
    KW_IF = auto()
    KW_ELSE = auto()
    KW_WHILE = auto()
    KW_FOR = auto()
    KW_INT = auto()
    KW_FLOAT = auto()
    KW_BOOL = auto()
    KW_RETURN = auto()
    KW_TRUE = auto()       # According to LANG-2 treated as keyword
    KW_FALSE = auto()      # According to LANG-2 treated as keyword
    KW_VOID = auto()
    KW_STRUCT = auto()
    KW_FN = auto()

    # Literals
    INT_LITERAL = auto()
    FLOAT_LITERAL = auto()
    STRING_LITERAL = auto()

    # Operators
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    EQ_EQ = auto()
    BANG_EQ = auto()
    LESS = auto()
    LESS_EQ = auto()
    GREATER = auto()
    GREATER_EQ = auto()
    AND = auto()
    OR = auto()
    BANG = auto()
    ASSIGN = auto()

    # Delimiters
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    SEMICOLON = auto()
    COMMA = auto()
    DOT = auto()

    # Special
    IDENTIFIER = auto()
    END_OF_FILE = auto()
    UNKNOWN = auto()

@dataclass
class Token:
    type: TokenType
    lexeme: str
    line: int
    column: int
    literal: object = None

    def __str__(self):
        # Format: LINE:COLUMN TOKEN_TYPE "LEXEME" [LITERAL_VALUE]
        # Example: 1:1 KW_IF "if"
        res = f"{self.line}:{self.column} {self.type.name} \"{self.lexeme}\""
        if self.literal is not None:
            res += f" {self.literal}"
        return res