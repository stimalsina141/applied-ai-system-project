"""In-memory project files, patch application, and diffs.

Patches are never written to the user's files. They are applied to an
in-memory copy, shown as a diff, and only executed inside a temporary
sandbox directory by the test runner.
"""
import ast
import difflib
import json
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from coach import config
from coach.schemas import PatchProposal


class WorkspaceError(Exception):
    """The input files are not acceptable."""


class PatchError(Exception):
    """A proposed patch broke a guardrail or could not be applied."""


def is_test_file(path: str) -> bool:
    p = PurePosixPath(path)
    return p.name.startswith("test_") or p.name.endswith("_test.py") or "tests" in p.parts or p.name == "conftest.py"


def check_path(path: str) -> str:
    """Reject paths that could escape the project directory."""
    p = PurePosixPath(path.replace("\\", "/"))
    if p.is_absolute() or ".." in p.parts or not p.parts or p.suffix != ".py":
        raise WorkspaceError(f"Unsafe or unsupported file path: {path!r}")
    return str(p)


@dataclass
class Workspace:
    files: dict[str, str]
    editable: set[str]
    name: str = "pasted code"
    symptom: str = ""
    error: str = ""
    expected: dict = field(default_factory=dict)

    def __post_init__(self):
        self.files = {check_path(path): content for path, content in self.files.items()}
        self.editable = {check_path(path) for path in self.editable}
        if not self.files:
            raise WorkspaceError("No code was provided.")
        if len(self.files) > config.MAX_FILES:
            raise WorkspaceError(f"Too many files (limit {config.MAX_FILES}).")
        if sum(len(c) for c in self.files.values()) > config.MAX_TOTAL_CODE_CHARS:
            raise WorkspaceError("The code is too long for this version of the coach.")
        unknown = self.editable - set(self.files)
        if unknown:
            raise WorkspaceError(f"Editable files not provided: {', '.join(sorted(unknown))}")
        protected = {path for path in self.editable if is_test_file(path)}
        if protected:
            raise WorkspaceError(f"Test files cannot be marked editable: {', '.join(sorted(protected))}")
        if not self.editable:
            raise WorkspaceError("At least one non-test file must be editable.")

    @property
    def test_files(self) -> list[str]:
        return [path for path in self.files if is_test_file(path)]

    @classmethod
    def from_paste(cls, code: str, tests: str = "", filename: str = "solution.py",
                   symptom: str = "", error: str = "") -> "Workspace":
        filename = check_path(filename.strip() or "solution.py")
        if is_test_file(filename):
            raise WorkspaceError("The code file name cannot look like a test file.")
        if not code.strip():
            raise WorkspaceError("Paste some Python code to debug.")
        files = {filename: code}
        if tests.strip():
            files[f"test_{PurePosixPath(filename).stem}.py"] = tests
        return cls(files=files, editable={filename}, symptom=symptom, error=error)

    @classmethod
    def from_example(cls, example_dir: Path) -> "Workspace":
        meta = json.loads((example_dir / "example.json").read_text())
        files = {}
        for path in sorted(example_dir.rglob("*.py")):
            rel = path.relative_to(example_dir).as_posix()
            if rel.startswith("solution/"):
                continue
            files[rel] = path.read_text()
        return cls(
            files=files,
            editable=set(meta["editable"]),
            name=meta["title"],
            symptom=meta.get("symptom", ""),
            error=meta.get("error", ""),
            expected=meta.get("expected", {}),
        )


def function_spans(source: str) -> dict[str, tuple[int, int]]:
    """Map function names (and Class.method names) to their (first, last) line numbers."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    spans = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = min([node.lineno] + [d.lineno for d in node.decorator_list])
            spans.setdefault(node.name, (start, node.end_lineno))
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        spans[f"{node.name}.{item.name}"] = (item.lineno, item.end_lineno)
    return spans


def _function_name(name: str) -> str:
    return name.strip().removesuffix("()")


def apply_patch(files: dict[str, str], editable: set[str], patch: PatchProposal) -> dict[str, str]:
    """Apply a patch to a copy of `files`, enforcing the coach's guardrails."""
    if not patch.targets:
        raise PatchError("The patch did not identify which function or lines it changes.")
    if not patch.edits:
        raise PatchError("The patch contains no edits.")

    targets = {(t.file, _function_name(t.function)) for t in patch.targets}
    new_files = dict(files)

    for i, edit in enumerate(patch.edits, start=1):
        label = f"Edit {i} ({edit.file}, {edit.function})"
        if edit.file not in files:
            raise PatchError(f"{label}: file does not exist.")
        if is_test_file(edit.file) or edit.file not in editable:
            raise PatchError(f"{label}: this file is protected and cannot be edited.")
        function = _function_name(edit.function)
        if (edit.file, function) not in targets:
            raise PatchError(f"{label}: function was not declared as a target before editing.")
        if not edit.find:
            raise PatchError(f"{label}: `find` text is empty.")

        source = new_files[edit.file]
        count = source.count(edit.find)
        if count == 0:
            raise PatchError(f"{label}: `find` text was not found in the current file.")
        if count > 1:
            raise PatchError(f"{label}: `find` text appears {count} times; it must be unique.")

        if function != "<module>":
            spans = function_spans(source)
            if function not in spans:
                raise PatchError(f"{label}: function {function!r} does not exist in {edit.file}.")
            start, end = spans[function]
            offset = source.index(edit.find)
            first_line = source.count("\n", 0, offset) + 1
            last_line = first_line + edit.find.rstrip("\n").count("\n")
            if first_line < start or last_line > end:
                raise PatchError(f"{label}: edit falls outside the target function {function!r}.")

        new_files[edit.file] = source.replace(edit.find, edit.replace, 1)

    return new_files


@dataclass
class FileDiff:
    path: str
    unified: str
    added: int
    removed: int


def make_diff(before: dict[str, str], after: dict[str, str]) -> list[FileDiff]:
    diffs = []
    for path in sorted(set(before) | set(after)):
        old, new = before.get(path, ""), after.get(path, "")
        if old == new:
            continue
        lines = list(difflib.unified_diff(
            old.splitlines(keepends=True), new.splitlines(keepends=True),
            fromfile=f"a/{path}", tofile=f"b/{path}", n=3,
        ))
        added = sum(1 for l in lines if l.startswith("+") and not l.startswith("+++"))
        removed = sum(1 for l in lines if l.startswith("-") and not l.startswith("---"))
        unified = "".join(l if l.endswith("\n") else l + "\n" for l in lines)
        diffs.append(FileDiff(path, unified, added, removed))
    return diffs


def changed_functions(before: dict[str, str], after: dict[str, str]) -> dict[str, set[str]]:
    """For each changed file, the functions whose lines changed ("<module>" for top-level lines)."""
    result = {}
    for path in after:
        old, new = before.get(path, ""), after[path]
        if old == new:
            continue
        spans = function_spans(new)
        touched = set()
        matcher = difflib.SequenceMatcher(None, old.splitlines(), new.splitlines())
        for tag, _, _, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue
            lines = range(j1 + 1, max(j2, j1 + 1) + 1)
            for line in lines:
                owners = [name for name, (s, e) in spans.items() if s <= line <= e and "." not in name]
                touched.add(min(owners, key=lambda n: spans[n][1] - spans[n][0]) if owners else "<module>")
        result[path] = touched
    return result


def static_checks(files: dict[str, str], paths: set[str]) -> list[dict]:
    """Cheap, deterministic quality checks: syntax errors, unused imports, broad excepts."""
    findings = []
    for path in sorted(paths):
        try:
            tree = ast.parse(files[path])
        except SyntaxError as e:
            findings.append({"file": path, "line": e.lineno, "issue": f"Syntax error: {e.msg}"})
            continue

        imported = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported[(alias.asname or alias.name).split(".")[0]] = node.lineno
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported[alias.asname or alias.name] = node.lineno
        used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        for name, line in imported.items():
            if name not in used and name != "*":
                findings.append({"file": path, "line": line, "issue": f"Unused import: {name}"})

        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    findings.append({"file": path, "line": node.lineno, "issue": "Bare `except:` catches every error"})
                elif isinstance(node.type, ast.Name) and node.type.id in ("Exception", "BaseException"):
                    findings.append({"file": path, "line": node.lineno,
                                     "issue": f"`except {node.type.id}` is very broad and can hide bugs"})
    return findings
