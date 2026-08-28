import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "app" / "main.py"


def _function_calls(function_name: str) -> set[str]:
    tree = ast.parse(MAIN.read_text(encoding="utf-8"))
    function = next(
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    )
    return {
        node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Attribute, ast.Name))
    }


def test_heavy_optional_packages_are_lazy_imports():
    tree = ast.parse(MAIN.read_text(encoding="utf-8"))
    top_level = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    imported = {
        alias.name.split(".")[0]
        for node in top_level
        for alias in node.names
    }
    assert "matplotlib" not in imported
    assert "word_export" not in imported


def test_hidden_diagnoses_tab_is_not_built_at_startup():
    assert "_build_diagnoses_tab" not in _function_calls("_build_ui")


def test_all_symptom_variables_are_not_built_at_startup():
    assert "_init_symptom_vars" not in _function_calls("_build_symptoms_tab")
