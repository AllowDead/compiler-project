"""Sprint 7 external-call registry for libc/System V AMD64 integration."""
from dataclasses import dataclass
from typing import Dict, List

@dataclass(frozen=True)
class ExternalFunction:
    name: str
    return_type: str
    param_types: List[str]
    variadic: bool = False
    library: str = "libc"

class ExternalFunctionRegistry:
    def __init__(self):
        self.functions: Dict[str, ExternalFunction] = {}
        for fn in [
            ExternalFunction("printf", "int", ["string"], True),
            ExternalFunction("scanf", "int", ["string"], True),
            ExternalFunction("puts", "int", ["string"]),
            ExternalFunction("getchar", "int", []),
            ExternalFunction("malloc", "void*", ["int"]),
            ExternalFunction("free", "void", ["void*"]),
            ExternalFunction("memcpy", "void*", ["void*", "void*", "int"]),
            ExternalFunction("memset", "void*", ["void*", "int", "int"]),
            ExternalFunction("strlen", "int", ["string"]),
            ExternalFunction("strcpy", "void*", ["void*", "string"]),
            ExternalFunction("strcmp", "int", ["string", "string"]),
            ExternalFunction("pow", "float", ["float", "float"], library="libm"),
            ExternalFunction("sqrt", "float", ["float"], library="libm"),
            ExternalFunction("sin", "float", ["float"], library="libm"),
            ExternalFunction("cos", "float", ["float"], library="libm"),
        ]:
            self.functions[fn.name] = fn

    def get(self, name: str):
        return self.functions.get(name)

    def is_external(self, name: str) -> bool:
        return name in self.functions
