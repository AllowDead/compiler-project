import json
from .ast_nodes import *


class ASTPrinter(Visitor):
    def __init__(self, output_type='text'):
        self.output_type = output_type
        self.indent_level = 0
        self.result = []

    def print(self, node: ASTNode) -> str:
        node.accept(self)
        return "\n".join(self.result)

    def indent(self):
        return "  " * self.indent_level

    # --- Declarations ---

    def visit_program(self, node: ProgramNode):
        if self.output_type == 'json':
            obj = {"type": "Program", "declarations": [self._to_json(d) for d in node.declarations]}
            self.result.append(json.dumps(obj, indent=2))
            return

        self.result.append(f"Program [line {node.line}]:")
        self.indent_level += 1
        for decl in node.declarations:
            decl.accept(self)
        self.indent_level -= 1

    def visit_function_decl(self, node: FunctionDeclNode):
        self.result.append(f"{self.indent()}FunctionDecl: {node.name} -> {node.return_type} [line {node.line}]:")

        self.indent_level += 1
        self.result.append(f"{self.indent()}Parameters:")
        self.indent_level += 1
        for p in node.params:
            p.accept(self)
        self.indent_level -= 1

        self.result.append(f"{self.indent()}Body [line {node.line}]:")
        self.indent_level += 1
        node.body.accept(self)
        self.indent_level -= 2

    def visit_struct_decl(self, node: StructDeclNode):
        self.result.append(f"{self.indent()}StructDecl: {node.name} [line {node.line}]:")
        self.indent_level += 1
        self.result.append(f"{self.indent()}Fields:")
        self.indent_level += 1
        for f in node.fields:
            f.accept(self)
        self.indent_level -= 2

    def visit_var_decl(self, node: VarDeclNode):
        init = f" = {self._expr_str(node.initializer)}" if node.initializer else ""
        # По спецификации VIS-1 тег строки в конце
        self.result.append(f"{self.indent()}VarDecl: {node.var_type} {node.name}{init}; [line {node.line}]")

    def visit_param(self, node: ParamNode):
        self.result.append(f"{self.indent()}Param: {node.param_type} {node.name} [line {node.line}]")

    # --- Statements ---

    def visit_block(self, node: BlockNode):
        # Хитрость для X-Y: ищем самую глубокую строку внутри блока
        end_line = node.line
        for stmt in node.statements:
            if hasattr(stmt, 'line') and stmt.line > end_line:
                end_line = stmt.line

        if end_line == node.line:
            self.result.append(f"{self.indent()}Block [line {node.line}]:")
        else:
            self.result.append(f"{self.indent()}Block [line {node.line}-{end_line}]:")

        self.indent_level += 1
        for stmt in node.statements:
            stmt.accept(self)
        self.indent_level -= 1

    def visit_expr_stmt(self, node: ExprStmtNode):
        self.result.append(f"{self.indent()}ExprStmt: {self._expr_str(node.expr)}; [line {node.line}]")

    def visit_if_stmt(self, node: IfStmtNode):
        # Считаем конечную строку (в Then или Else ветке)
        end_line = node.line
        if node.then_branch and hasattr(node.then_branch, 'line'):
            end_line = max(end_line, node.then_branch.line)
        if node.else_branch and hasattr(node.else_branch, 'line'):
            end_line = max(end_line, node.else_branch.line)

        if end_line == node.line:
            self.result.append(f"{self.indent()}IfStmt [line {node.line}]:")
        else:
            self.result.append(f"{self.indent()}IfStmt [line {node.line}-{end_line}]:")

        self.indent_level += 1
        self.result.append(f"{self.indent()}Condition: {self._expr_str(node.condition)}")
        self.result.append(f"{self.indent()}Then:")
        node.then_branch.accept(self)
        if node.else_branch:
            self.result.append(f"{self.indent()}Else:")
            node.else_branch.accept(self)
        self.indent_level -= 1

    def visit_while_stmt(self, node: WhileStmtNode):
        # Считаем конечную строку в теле цикла
        end_line = node.body.line if node.body and hasattr(node.body, 'line') else node.line

        if end_line == node.line:
            self.result.append(f"{self.indent()}WhileStmt [line {node.line}]:")
        else:
            self.result.append(f"{self.indent()}WhileStmt [line {node.line}-{end_line}]:")

        self.indent_level += 1
        self.result.append(f"{self.indent()}Condition: {self._expr_str(node.condition)}")
        node.body.accept(self)
        self.indent_level -= 1

    def visit_for_stmt(self, node: ForStmtNode):
        # Считаем конечную строку в теле цикла
        end_line = node.body.line if node.body and hasattr(node.body, 'line') else node.line

        if end_line == node.line:
            self.result.append(f"{self.indent()}ForStmt [line {node.line}]:")
        else:
            self.result.append(f"{self.indent()}ForStmt [line {node.line}-{end_line}]:")

        self.indent_level += 1
        self.result.append(f"{self.indent()}Init: {self._stmt_str(node.init)}")
        self.result.append(f"{self.indent()}Cond: {self._expr_str(node.condition)}")
        self.result.append(f"{self.indent()}Update: {self._expr_str(node.update)}")
        node.body.accept(self)
        self.indent_level -= 1

    def visit_return_stmt(self, node: ReturnStmtNode):
        val = self._expr_str(node.value) if node.value else ""
        # По спецификации VIS-1 тег строки в конце
        self.result.append(f"{self.indent()}Return: {val} [line {node.line}]")

    # --- Expressions (Возвращают строки, теги line не добавляем для читаемости) ---

    def visit_binary_expr(self, node: BinaryExprNode):
        return f"({self._expr_str(node.left)} {node.operator} {self._expr_str(node.right)})"

    def visit_unary_expr(self, node: UnaryExprNode):
        return f"({node.operator} {self._expr_str(node.right)})"

    def visit_literal_expr(self, node: LiteralExprNode):
        return str(node.value)

    def visit_identifier_expr(self, node: IdentifierExprNode):
        return node.name

    def visit_call_expr(self, node: CallExprNode):
        args = ", ".join([self._expr_str(a) for a in node.arguments])
        return f"{node.callee.accept(self)}({args})"

    def visit_assignment_expr(self, node: AssignmentExprNode):
        return f"({node.target.accept(self)} {node.operator} {self._expr_str(node.value)})"

    # --- Helpers ---

    def _expr_str(self, node):
        if node is None: return "null"
        return node.accept(self)

    def _stmt_str(self, node):
        if node is None: return "null"
        return "Statement"

    def _to_json(self, node):
        """Рекурсивно преобразует AST ноду в словарь для JSON."""
        if node is None: return None
        if isinstance(node, list): return [self._to_json(item) for item in node]
        if isinstance(node, (str, int, float, bool)): return node

        data = {"type": node.__class__.__name__}

        if isinstance(node, FunctionDeclNode):
            data["name"] = node.name
            data["return_type"] = node.return_type
            data["params"] = self._to_json(node.params)
            data["body"] = self._to_json(node.body)
        elif isinstance(node, StructDeclNode):
            data["name"] = node.name
            data["fields"] = self._to_json(node.fields)
        elif isinstance(node, ParamNode):
            data["param_type"] = node.param_type
            data["name"] = node.name
        elif isinstance(node, VarDeclNode):
            data["var_type"] = node.var_type
            data["name"] = node.name
            data["initializer"] = self._to_json(node.initializer)
        elif isinstance(node, BlockNode):
            data["statements"] = self._to_json(node.statements)
        elif isinstance(node, ExprStmtNode):
            data["expr"] = self._to_json(node.expr)
        elif isinstance(node, IfStmtNode):
            data["condition"] = self._to_json(node.condition)
            data["then_branch"] = self._to_json(node.then_branch)
            data["else_branch"] = self._to_json(node.else_branch)
        elif isinstance(node, WhileStmtNode):
            data["condition"] = self._to_json(node.condition)
            data["body"] = self._to_json(node.body)
        elif isinstance(node, ForStmtNode):
            data["init"] = self._to_json(node.init)
            data["condition"] = self._to_json(node.condition)
            data["update"] = self._to_json(node.update)
            data["body"] = self._to_json(node.body)
        elif isinstance(node, ReturnStmtNode):
            data["value"] = self._to_json(node.value)
        elif isinstance(node, BinaryExprNode):
            data["left"] = self._to_json(node.left)
            data["operator"] = node.operator
            data["right"] = self._to_json(node.right)
        elif isinstance(node, UnaryExprNode):
            data["operator"] = node.operator
            data["right"] = self._to_json(node.right)
        elif isinstance(node, LiteralExprNode):
            data["value"] = node.value
        elif isinstance(node, IdentifierExprNode):
            data["name"] = node.name
        elif isinstance(node, CallExprNode):
            data["callee"] = self._to_json(node.callee)
            data["arguments"] = self._to_json(node.arguments)
        elif isinstance(node, AssignmentExprNode):
            data["target"] = self._to_json(node.target)
            data["operator"] = node.operator
            data["value"] = self._to_json(node.value)
        else:
            return str(node)

        return data


class DotPrinter(Visitor):
    def __init__(self):
        self.buffer = []
        self.counter = 0
        self.buffer.append("digraph AST {")
        self.buffer.append("  node [shape=box];")

        self.colors = {
            "Program": "black",
            # Declarations
            "Fn:": "orange", "Struct:": "orange", "Param:": "orange", "Var:": "darkgreen",
            # Statements
            "Block": "gray", "If": "green", "While": "green", "For": "green", "Return": "green",
            # Expressions
            "Op:": "lightblue", "Unary:": "lightblue", "Lit:": "cyan", "Id:": "cyan",
            "Call:": "lightblue", "Assign:": "lightblue"
        }

    def get_output(self):
        self.buffer.append("}")
        return "\n".join(self.buffer)

    def _node(self, label):
        nid = f"n{self.counter}"
        self.counter += 1
        # Экранируем кавычки
        label = label.replace('"', '\\"')

        # Определяем цвет по префиксу названия
        color = "black"  # цвет по умолчанию
        for key, c in self.colors.items():
            if label.startswith(key):
                color = c
                break

        # Добавляем атрибут color в DOT
        self.buffer.append(f'  {nid} [label="{label}", color="{color}"];')
        return nid

    def _edge(self, parent, child, label=""):
        l = f' [label="{label}"]' if label else ""
        self.buffer.append(f'  {parent} -> {child}{l};')

    # --- Visitors ---

    def visit_program(self, node):
        pid = self._node("Program")
        for decl in node.declarations:
            did = decl.accept(self)
            self._edge(pid, did)
        return pid

    def visit_function_decl(self, node):
        label = f"Fn: {node.name}()\nReturns: {node.return_type}"
        pid = self._node(label)
        if node.body:
            bid = node.body.accept(self)
            self._edge(pid, bid, "body")
        return pid

    def visit_struct_decl(self, node):
        pid = self._node(f"Struct: {node.name}")
        for field in node.fields:
            fid = field.accept(self)
            self._edge(pid, fid)
        return pid

    def visit_param(self, node):
        return self._node(f"Param: {node.name}: {node.param_type}")

    def visit_block(self, node):
        pid = self._node("Block")
        for stmt in node.statements:
            sid = stmt.accept(self)
            self._edge(pid, sid)
        return pid

    def visit_var_decl(self, node):
        label = f"Var: {node.name}: {node.var_type}"
        pid = self._node(label)
        if node.initializer:
            iid = node.initializer.accept(self)
            self._edge(pid, iid, "init")
        return pid

    def visit_expr_stmt(self, node):
        return node.expr.accept(self)

    def visit_if_stmt(self, node):
        pid = self._node("If")
        cid = node.condition.accept(self)
        self._edge(pid, cid, "cond")
        tid = node.then_branch.accept(self)
        self._edge(pid, tid, "then")
        if node.else_branch:
            eid = node.else_branch.accept(self)
            self._edge(pid, eid, "else")
        return pid

    def visit_while_stmt(self, node):
        pid = self._node("While")
        cid = node.condition.accept(self)
        self._edge(pid, cid, "cond")
        bid = node.body.accept(self)
        self._edge(pid, bid, "body")
        return pid

    def visit_for_stmt(self, node):
        pid = self._node("For")
        # Для простоты рисуем только основные части
        if node.init:
            self._edge(pid, node.init.accept(self), "init")
        if node.condition:
            self._edge(pid, node.condition.accept(self), "cond")
        if node.update:
            self._edge(pid, node.update.accept(self), "update")
        self._edge(pid, node.body.accept(self), "body")
        return pid

    def visit_return_stmt(self, node):
        pid = self._node("Return")
        if node.value:
            vid = node.value.accept(self)
            self._edge(pid, vid)
        return pid

    def visit_binary_expr(self, node):
        pid = self._node(f"Op: {node.operator}")
        lid = node.left.accept(self)
        self._edge(pid, lid, "left")
        rid = node.right.accept(self)
        self._edge(pid, rid, "right")
        return pid

    def visit_unary_expr(self, node):
        pid = self._node(f"Unary: {node.operator}")
        rid = node.right.accept(self)
        self._edge(pid, rid)
        return pid

    def visit_literal_expr(self, node):
        val_str = str(node.value)
        if isinstance(val_str, str) and len(val_str) > 20:
            val_str = val_str[:20] + "..."
        return self._node(f"Lit: {val_str}")

    def visit_identifier_expr(self, node):
        return self._node(f"Id: {node.name}")

    def visit_call_expr(self, node):
        pid = self._node(f"Call: {node.callee.name}")
        for i, arg in enumerate(node.arguments):
            aid = arg.accept(self)
            self._edge(pid, aid, f"arg{i}")
        return pid

    def visit_assignment_expr(self, node):
        pid = self._node(f"Assign: {node.operator}")
        tid = node.target.accept(self)
        self._edge(pid, tid, "target")
        vid = node.value.accept(self)
        self._edge(pid, vid, "value")
        return pid