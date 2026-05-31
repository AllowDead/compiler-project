from pathlib import Path
from tree_format import format_tree

# Настройки фильтрации
IGNORE_DIRS = {'.venv', '__pycache__', '.git', '.idea', 'node_modules', 'minicompiler.egg-info', 'v', '.pytest_cache'}
IGNORE_FILES = {'.pyc', '.tokens', '.expected', '.src', '__init__.py', 'print_tree.py'}


def has_valid_content(path: Path) -> bool:
    """Проверяет, есть ли в папке хоть что-то, кроме игнорируемых файлов"""
    try:
        for entry in path.iterdir():
            if entry.is_dir() and entry.name not in IGNORE_DIRS:
                return True
            if entry.is_file() and entry.suffix not in IGNORE_FILES:
                return True
    except PermissionError:
        pass
    return False


def get_children(path: Path):
    # Если это файл, у него нет детей (предотвращает краш от iterdir())
    if not path.is_dir():
        return []

    children = []
    try:
        for entry in sorted(path.iterdir()):
            # 1. Пропускаем системные папки
            if entry.is_dir() and entry.name in IGNORE_DIRS:
                continue

            # 2. Пропускаем игнорируемые файлы (.src, .tokens и т.д.)
            if entry.is_file() and entry.suffix in IGNORE_FILES:
                continue

            # 3. Скрываем пустые папки (например, valid/, если там только .src)
            if entry.is_dir() and not has_valid_content(entry):
                continue

            children.append(entry)
    except (PermissionError, NotADirectoryError):
        pass

    return children


def format_node(path: Path):
    """Возвращает имя файла или папки для отрисовки"""
    return path.name


if __name__ == "__main__":
    root = Path('.')
    print(format_tree(root, format_node, get_children))