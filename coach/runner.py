"""Controlled test runner.

Guardrails:
- The only command ever executed is `python -m pytest` with fixed arguments.
  Nothing the AI writes is ever run as a shell command.
- Tests run in a fresh temporary directory holding a copy of the files, so
  the user's real files are never touched.
- A timeout stops runaway code (for example an infinite loop).
- API keys are removed from the environment the tests run in.
"""
import os
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from coach import config

_SECRET_ENV_PREFIXES = ("ANTHROPIC_", "OPENAI_", "AWS_", "GOOGLE_", "AZURE_")


@dataclass
class TestCase:
    name: str
    outcome: str  # "passed", "failed", "error", "skipped"
    message: str = ""


@dataclass
class TestRun:
    kind: str  # "pytest" or "syntax" (when there are no tests)
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    duration: float = 0.0
    exit_code: int | None = None
    timed_out: bool = False
    output: str = ""
    cases: list[TestCase] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.errors

    @property
    def problems(self) -> int:
        return self.failed + self.errors + (1 if self.timed_out else 0)

    @property
    def all_passed(self) -> bool:
        return self.kind == "pytest" and self.total > 0 and self.problems == 0 and self.exit_code == 0

    @property
    def passing_names(self) -> set[str]:
        return {c.name for c in self.cases if c.outcome == "passed"}

    @property
    def failing_names(self) -> set[str]:
        return {c.name for c in self.cases if c.outcome in ("failed", "error")}

    def headline(self) -> str:
        if self.kind == "syntax":
            return "No tests provided. Syntax check " + ("passed." if self.exit_code == 0 else "failed.")
        if self.timed_out:
            return f"Tests timed out after {config.TEST_TIMEOUT_SECONDS} seconds."
        if self.total == 0:
            return f"No tests ran (pytest exit code {self.exit_code})."
        parts = [f"{self.passed} passed"]
        if self.failed:
            parts.append(f"{self.failed} failed")
        if self.errors:
            parts.append(f"{self.errors} errors")
        return ", ".join(parts) + f" in {self.duration:.2f}s"


def _safe_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith(_SECRET_ENV_PREFIXES)}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _truncate(text: str) -> str:
    limit = config.MAX_TEST_OUTPUT_CHARS
    if len(text) <= limit:
        return text
    return text[: limit // 3] + "\n\n... (output truncated) ...\n\n" + text[-(2 * limit) // 3:]


def _write_files(root: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        target = (root / rel).resolve()
        if root.resolve() not in target.parents:
            raise ValueError(f"Refusing to write outside the sandbox: {rel}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)


def _parse_junit(report: Path) -> list[TestCase]:
    if not report.exists():
        return []
    cases = []
    for case in ET.parse(report).getroot().iter("testcase"):
        classname = case.get("classname", "")
        name = case.get("name", "")
        module = classname.split(".")[-1] if classname else ""
        full = f"{module}::{name}" if module else name
        outcome, message = "passed", ""
        for child in case:
            if child.tag in ("failure", "error", "skipped"):
                outcome = {"failure": "failed", "error": "error", "skipped": "skipped"}[child.tag]
                message = (child.get("message") or "").strip()[:300]
                break
        cases.append(TestCase(full, outcome, message))
    return cases


def syntax_check(files: dict[str, str], paths) -> TestRun:
    """Used when the user gave no tests: we can only confirm the code compiles."""
    errors = []
    for path in paths:
        try:
            compile(files[path], path, "exec")
        except SyntaxError as e:
            errors.append(f"{path}:{e.lineno}: SyntaxError: {e.msg}")
    return TestRun(kind="syntax", exit_code=1 if errors else 0,
                   output="\n".join(errors) or "All files compile.")


def run_tests(files: dict[str, str], timeout: int = config.TEST_TIMEOUT_SECONDS) -> TestRun:
    with tempfile.TemporaryDirectory(prefix="coach-sandbox-") as tmp:
        root = Path(tmp)
        _write_files(root, files)
        report = root / ".coach-report.xml"
        command = [
            sys.executable, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider",
            "--tb=short", f"--junitxml={report}",
        ]
        start = time.monotonic()
        try:
            proc = subprocess.run(
                command, cwd=root, env=_safe_env(), capture_output=True, text=True,
                timeout=timeout, stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired as e:
            output = (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
            return TestRun(kind="pytest", timed_out=True, duration=time.monotonic() - start,
                           output=_truncate(output + "\n\nTimed out."))
        duration = time.monotonic() - start
        cases = _parse_junit(report)

    run = TestRun(
        kind="pytest",
        passed=sum(c.outcome == "passed" for c in cases),
        failed=sum(c.outcome == "failed" for c in cases),
        errors=sum(c.outcome == "error" for c in cases),
        skipped=sum(c.outcome == "skipped" for c in cases),
        duration=duration,
        exit_code=proc.returncode,
        output=_truncate((proc.stdout + proc.stderr).strip()),
        cases=cases,
    )
    # Collection errors (e.g. a syntax error in the code under test) produce no
    # test cases, but pytest still fails. Count them so they are never "passing".
    if proc.returncode not in (0, 5) and run.total == 0:
        run.errors = 1
    return run


def validate(files: dict[str, str], code_paths, has_tests: bool) -> TestRun:
    return run_tests(files) if has_tests else syntax_check(files, code_paths)
