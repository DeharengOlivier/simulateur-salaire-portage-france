"""AST-enforced import boundaries, including absence of runtime network/process imports."""

import ast
from pathlib import Path


def test_runtime_import_boundaries() -> None:
    package = Path(__file__).resolve().parents[1] / "portage"
    permitted = {
        "money": set(),
        "tax": {"money"},
        "model": {"money", "tax"},
        "cli": {"", "money", "model"},
        "__main__": {"cli"},
        "__init__": set(),
    }
    standard_library = {
        "argparse",
        "json",
        "sys",
        "tomllib",
        "dataclasses",
        "decimal",
        "pathlib",
        "typing",
        "datetime",
    }
    for file in package.glob("*.py"):
        for node in ast.walk(ast.parse(file.read_text())):
            if isinstance(node, ast.ImportFrom):
                if node.level:
                    assert node.level == 1
                    assert (node.module or "") in permitted[file.stem]
                else:
                    assert node.module in standard_library
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name in standard_library
