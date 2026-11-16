"""Reliability evaluation: how well does the coach actually debug?

Runs the full agentic workflow on every built-in example (each has a known
bug, tests, and a list of the functions that contain the bug) and measures:

- Fix rate:          the tests pass at the end (judged by pytest, not the AI)
- Diagnosis recall:  share of the known buggy functions the diagnosis pointed to
- Diagnosis precision: share of pointed-to functions that really were buggy
- Attempts used and guardrail blocks
- Scope:             whether kept patches changed anything outside declared targets
- Consistency:       with --runs > 1, whether repeated runs agree on status and location

Usage:
    python -m eval.run_eval                     # every example, one run each
    python -m eval.run_eval --runs 3            # measure consistency
    python -m eval.run_eval --examples word_stats grade_calculator
"""
import argparse
import json
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from coach.agent import STATUS_LABELS, DebugSession
from coach.examples import list_examples
from coach.llm import ClaudeLLM, api_key_available

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def evaluate_once(example, llm, max_attempts: int) -> dict:
    workspace = example.workspace()
    expected = set(workspace.expected.get("functions", []))
    session = DebugSession(workspace, llm, max_attempts=max_attempts)
    start = time.monotonic()
    session.run_auto()
    duration = time.monotonic() - start

    pointed = {f.function.removesuffix("()") for f in session.diagnosis.findings} if session.diagnosis else set()
    pointed.discard("<module>")
    found = expected & pointed
    return {
        "example": example.key,
        "session_id": session.id,
        "status": session.status,
        "fixed": session.status == "fixed",
        "tests_before": session.baseline.headline() if session.baseline else None,
        "tests_after": session.current_run.headline() if session.current_run else None,
        "diagnosis_recall": len(found) / len(expected) if expected else None,
        "diagnosis_precision": len(found) / len(pointed) if pointed else 0.0,
        "pointed_functions": sorted(pointed),
        "confidence": session.diagnosis.confidence if session.diagnosis else None,
        "attempts": len(session.attempts),
        "guardrail_blocks": sum(a.state == "invalid" for a in session.attempts),
        "out_of_scope_changes": session.out_of_scope_changes(),
        "seconds": round(duration, 1),
        "stop_reason": session.stop_reason,
    }


def _mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else 0.0


def summarize(results: list[dict]) -> dict:
    by_example = {}
    for r in results:
        by_example.setdefault(r["example"], []).append(r)

    consistency = {}
    for key, runs in by_example.items():
        if len(runs) > 1:
            statuses = Counter(r["status"] for r in runs)
            locations = Counter(tuple(r["pointed_functions"]) for r in runs)
            consistency[key] = {
                "status_agreement": statuses.most_common(1)[0][1] / len(runs),
                "location_agreement": locations.most_common(1)[0][1] / len(runs),
            }

    return {
        "runs": len(results),
        "fix_rate": _mean([r["fixed"] for r in results]),
        "diagnosis_recall": _mean([r["diagnosis_recall"] for r in results]),
        "diagnosis_precision": _mean([r["diagnosis_precision"] for r in results]),
        "mean_attempts": _mean([r["attempts"] for r in results]),
        "guardrail_blocks": sum(r["guardrail_blocks"] for r in results),
        "out_of_scope_runs": sum(bool(r["out_of_scope_changes"]) for r in results),
        "consistency": consistency,
    }


def to_markdown(summary: dict, results: list[dict], model: str) -> str:
    lines = [
        "# Evaluation Results", "",
        f"Model: `{model}` | Runs: {summary['runs']} | Date: {datetime.now():%Y-%m-%d %H:%M}", "",
        "| Metric | Value |", "|---|---|",
        f"| Fix rate (tests pass at the end) | {summary['fix_rate']:.0%} |",
        f"| Diagnosis recall (known buggy functions found) | {summary['diagnosis_recall']:.0%} |",
        f"| Diagnosis precision (pointed-to functions that were buggy) | {summary['diagnosis_precision']:.0%} |",
        f"| Mean attempts used | {summary['mean_attempts']:.2f} |",
        f"| Patches blocked by guardrails | {summary['guardrail_blocks']} |",
        f"| Runs with changes outside declared targets | {summary['out_of_scope_runs']} |",
        "",
        "| Example | Status | Before | After | Recall | Attempts | Seconds |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        recall = f"{r['diagnosis_recall']:.0%}" if r["diagnosis_recall"] is not None else "-"
        lines.append(
            f"| {r['example']} | {STATUS_LABELS.get(r['status'], r['status'])} | {r['tests_before']} | "
            f"{r['tests_after']} | {recall} | {r['attempts']} | {r['seconds']} |"
        )
    if summary["consistency"]:
        lines += ["", "| Example | Same status across runs | Same location across runs |", "|---|---|---|"]
        for key, c in summary["consistency"].items():
            lines.append(f"| {key} | {c['status_agreement']:.0%} | {c['location_agreement']:.0%} |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", type=int, default=1, help="runs per example (use 3+ for consistency)")
    parser.add_argument("--examples", nargs="*", help="example keys to run (default: all)")
    parser.add_argument("--max-attempts", type=int, default=3)
    args = parser.parse_args(argv)

    if not api_key_available():
        print("Error: set ANTHROPIC_API_KEY to run the evaluation (see .env.example).", file=sys.stderr)
        return 2

    examples = [e for e in list_examples() if not args.examples or e.key in args.examples]
    if not examples:
        print("No matching examples.", file=sys.stderr)
        return 2

    llm = ClaudeLLM()
    results = []
    for example in examples:
        for run in range(1, args.runs + 1):
            print(f"[{example.key}] run {run}/{args.runs} ...", file=sys.stderr, flush=True)
            result = evaluate_once(example, llm, args.max_attempts)
            print(f"  -> {STATUS_LABELS.get(result['status'])} in {result['attempts']} attempt(s)", file=sys.stderr)
            results.append(result)

    summary = summarize(results)
    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    (RESULTS_DIR / f"{stamp}.json").write_text(
        json.dumps({"model": llm.model, "summary": summary, "results": results}, indent=2))
    markdown = to_markdown(summary, results, llm.model)
    (RESULTS_DIR / "latest.md").write_text(markdown)
    print(markdown)
    print(f"Saved to {RESULTS_DIR}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
