"""The evaluation harness itself, run offline with a scripted model."""
import shutil

from coach.agent import DebugSession
from coach.examples import get_example
from coach.workspace import Workspace
from coach.schemas import Diagnosis, Edit, Finding, PatchProposal, Target
from conftest import ScriptedLLM, quality
from eval.run_eval import evaluate_once, summarize, to_markdown


def _word_stats_responses():
    finding = lambda fn: Finding(status="confirmed", summary="bug", evidence="test", file="word_stats.py",
                                 function=fn, lines="1")
    diagnosis = Diagnosis(
        problem_summary="crash", findings=[finding("summary"), finding("word_count")], root_cause="types",
        confidence="high", needs_more_info=False, questions_for_user=[], concept="type conversion",
        explanation="...", small_example="",
    )
    patch = PatchProposal(
        targets=[Target(file="word_stats.py", function="summary", lines="8"),
                 Target(file="word_stats.py", function="word_count", lines="3")],
        plan="Convert to str; split on any whitespace.",
        edits=[Edit(file="word_stats.py", function="summary",
                    new_code='def summary(text):\n    """Return a one-line summary like \'Words: 3\'."""\n'
                             '    return "Words: " + str(word_count(text))\n'),
               Edit(file="word_stats.py", function="word_count",
                    new_code='def word_count(text):\n    """Count the words in a piece of text."""\n'
                             '    return len(text.split())\n')],
        summary="Two one-line changes.", assumptions=[],
    )
    return diagnosis, patch, quality()


def test_evaluate_once_scores_a_fixed_example():
    result = evaluate_once(get_example("word_stats"), ScriptedLLM(*_word_stats_responses()), max_attempts=3)
    assert result["fixed"]
    assert result["diagnosis_recall"] == 1.0
    assert result["diagnosis_precision"] == 1.0
    assert result["attempts"] == 1
    assert result["out_of_scope_changes"] == []


def test_transcript_is_saved(tmp_path):
    evaluate_once(get_example("word_stats"), ScriptedLLM(*_word_stats_responses()), 3, tmp_path)
    [saved] = tmp_path.glob("word_stats-*.md")
    text = saved.read_text()
    assert "## Explanation shown to the learner" in text
    assert "+    return \"Words: \" + str(word_count(text))" in text
    assert "# Debugging Report" in text


def test_example_files_on_disk_are_never_modified(tmp_path):
    source = get_example("word_stats").path
    copy = tmp_path / "word_stats"
    shutil.copytree(source, copy)
    before = {p: p.read_bytes() for p in copy.rglob("*") if p.is_file()}

    session = DebugSession(Workspace.from_example(copy), ScriptedLLM(*_word_stats_responses()))
    session.run_auto()

    assert session.status == "fixed"
    assert {p: p.read_bytes() for p in copy.rglob("*") if p.is_file()} == before


def test_summary_and_consistency():
    results = [evaluate_once(get_example("word_stats"), ScriptedLLM(*_word_stats_responses()), 3)
               for _ in range(2)]
    summary = summarize(results)
    assert summary["fix_rate"] == 1.0
    assert summary["consistency"]["word_stats"] == {"status_agreement": 1.0, "location_agreement": 1.0}
    assert summary["fix_rate_by_confidence"] == {"high": {"runs": 2, "fix_rate": 1.0}}
    assert "| Fix rate (tests pass at the end) | 100% |" in to_markdown(summary, results, "test-model")
