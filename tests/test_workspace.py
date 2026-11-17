import pytest

from coach.workspace import (
    PatchError, Workspace, WorkspaceError, apply_patch, changed_functions, make_diff, static_checks,
)
from conftest import CALC, patch


@pytest.mark.parametrize("path", ["/etc/passwd.py", "../outside.py", "a/../../b.py", "notes.txt"])
def test_unsafe_paths_are_rejected(path):
    with pytest.raises(WorkspaceError):
        Workspace(files={path: "x = 1\n"}, editable={path})


def test_test_files_cannot_be_editable():
    with pytest.raises(WorkspaceError):
        Workspace(files={"test_x.py": "", "x.py": ""}, editable={"test_x.py"})


def test_from_paste_creates_code_and_test_files():
    ws = Workspace.from_paste("x = 1\n", "def test_x(): pass\n", filename="game.py")
    assert set(ws.files) == {"game.py", "test_game.py"}
    assert ws.editable == {"game.py"}
    assert ws.test_files == ["test_game.py"]


def test_from_paste_requires_code():
    with pytest.raises(WorkspaceError):
        Workspace.from_paste("   ")


def test_apply_patch_returns_new_copy():
    files = {"calc.py": CALC}
    result = apply_patch(files, {"calc.py"}, patch("a - b", "a + b"))
    assert "a + b" in result["calc.py"]
    assert files["calc.py"] == CALC


def test_edit_must_be_inside_declared_function():
    # The patch claims to edit add() but its new code defines double() instead.
    p = patch("a - b", "a + b")
    p.edits[0].new_code = "def double(x):\n    return x + x\n"
    with pytest.raises(PatchError, match="must be the complete function, starting with `def add\\(`"):
        apply_patch({"calc.py": CALC}, {"calc.py"}, p)
    # Extra code after the function is rejected too.
    p.edits[0].new_code = "def add(a, b):\n    return a + b\n\nimport os\n"
    with pytest.raises(PatchError, match="nothing else"):
        apply_patch({"calc.py": CALC}, {"calc.py"}, p)


def test_only_the_declared_function_changes():
    source = "class Cart:\n    @property\n    def total(self):\n        return 1\n\n    def size(self):\n        return 0\n"
    p = patch("a - b", "a + b")
    p.targets[0].file, p.targets[0].function = "cart.py", "Cart.total"
    p.edits[0].file, p.edits[0].function = "cart.py", "Cart.total"
    p.edits[0].new_code = "def total(self):\n    return 2\n"
    result = apply_patch({"cart.py": source}, {"cart.py"}, p)["cart.py"]
    assert result == source.replace("return 1", "return 2")  # indentation and decorator kept


def test_edit_function_must_be_declared_as_target():
    p = patch("a - b", "a + b")
    p.edits[0] = p.edits[0].model_copy(update={"function": "double"})
    with pytest.raises(PatchError, match="not declared as a target"):
        apply_patch({"calc.py": CALC}, {"calc.py"}, p)


def test_target_function_must_exist():
    p = patch("a - b", "a + b")
    p.targets[0].function = p.edits[0].function = "subtract"
    with pytest.raises(PatchError, match="does not exist"):
        apply_patch({"calc.py": CALC}, {"calc.py"}, p)


def test_new_code_with_syntax_error_is_rejected():
    with pytest.raises(PatchError, match="syntax error"):
        apply_patch({"calc.py": CALC}, {"calc.py"}, patch("a - b", "a +"))


def test_patch_must_identify_targets():
    p = patch("a - b", "a + b")
    p.targets = []
    with pytest.raises(PatchError, match="did not identify"):
        apply_patch({"calc.py": CALC}, {"calc.py"}, p)


def test_diff_counts_lines():
    after = apply_patch({"calc.py": CALC}, {"calc.py"}, patch("a - b", "a + b"))
    [diff] = make_diff({"calc.py": CALC}, after)
    assert (diff.added, diff.removed) == (1, 1)
    assert "-    return a - b" in diff.unified


def test_changed_functions_finds_touched_function():
    after = apply_patch({"calc.py": CALC}, {"calc.py"}, patch("a - b", "a + b"))
    assert changed_functions({"calc.py": CALC}, after) == {"calc.py": {"add"}}


def test_static_checks_flag_unused_import_and_broad_except():
    code = "import os\nimport random\n\ntry:\n    random.random()\nexcept Exception:\n    pass\n"
    issues = [f["issue"] for f in static_checks({"a.py": code}, {"a.py"})]
    assert "Unused import: os" in issues
    assert any("except Exception" in i for i in issues)
    assert not any("random" in i for i in issues)
