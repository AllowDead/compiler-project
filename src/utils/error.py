class LexerError(Exception):
    def __init__(self, message, line, column):
        super().__init__(f"[Line {line}, Column {column}] {message}")
        self.line = line
        self.column = column