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
    # "x * 2" lives in double(), but the patch claims to edit add().
    with pytest.raises(PatchError, match="outside the target function"):
        apply_patch({"calc.py": CALC}, {"calc.py"}, patch("x * 2", "x + x", function="add"))


def test_edit_function_must_be_declared_as_target():
    p = patch("a - b", "a + b")
    p.edits[0] = p.edits[0].model_copy(update={"function": "double"})
    with pytest.raises(PatchError, match="not declared as a target"):
        apply_patch({"calc.py": CALC}, {"calc.py"}, p)


def test_find_text_must_exist_and_be_unique():
    with pytest.raises(PatchError, match="not found"):
        apply_patch({"calc.py": CALC}, {"calc.py"}, patch("a * b", "a + b"))
    with pytest.raises(PatchError, match="must be unique"):
        apply_patch({"calc.py": CALC + "\ndef sub(a, b):\n    return a - b\n"},
                    {"calc.py"}, patch("return a - b", "return a + b"))


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
