"""Command-line entry point.

    python -m coach --list
    python -m coach --example number_guessing_game
    python -m coach --code buggy.py --tests test_buggy.py --symptom "..."
"""
import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from coach.agent import DebugSession
from coach.examples import get_example, list_examples
from coach.llm import ClaudeLLM, api_key_available
from coach.report import build_report
from coach.workspace import Workspace, WorkspaceError


def main(argv=None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="python -m coach", description="AI Debugging Coach")
    parser.add_argument("--list", action="store_true", help="list the built-in examples")
    parser.add_argument("--example", help="debug a built-in example by key")
    parser.add_argument("--code", type=Path, help="path to a Python file to debug")
    parser.add_argument("--tests", type=Path, help="optional pytest file for --code")
    parser.add_argument("--symptom", default="", help="what is going wrong")
    parser.add_argument("--error", default="", help="error message or traceback")
    parser.add_argument("--max-attempts", type=int, default=3)
    args = parser.parse_args(argv)

    if args.list:
        for ex in list_examples():
            print(f"{ex.key:<24} {ex.title}")
        return 0

    try:
        if args.example:
            workspace = get_example(args.example).workspace()
        elif args.code:
            workspace = Workspace.from_paste(
                args.code.read_text(), args.tests.read_text() if args.tests else "",
                filename=args.code.name, symptom=args.symptom, error=args.error,
            )
        else:
            parser.error("give --example, --code, or --list")
    except (WorkspaceError, KeyError, OSError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    if not api_key_available():
        print("Error: set ANTHROPIC_API_KEY (see .env.example).", file=sys.stderr)
        return 2

    session = DebugSession(workspace, ClaudeLLM(), max_attempts=args.max_attempts)
    print(f"Debugging {workspace.name} (session {session.id})...", file=sys.stderr)
    session.run_auto()
    for a in session.attempts:
        for diff in a.diff:
            print(f"\n--- Attempt {a.number}: {diff.path} ---\n{diff.unified}", file=sys.stderr)
    print(build_report(session))
    return 0 if session.status == "fixed" else 1


if __name__ == "__main__":
    sys.exit(main())
