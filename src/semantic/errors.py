class SemanticError:
    def __init__(self, error_type: str, line: int, col: int, message: str):
        self.error_type = error_type
        self.line = line
        self.col = col
        self.message = message

    def __str__(self):
        return f"semantic error: {self.error_type}\n  --> line {self.line}, col {self.col}\n   |\n   = {self.message}"