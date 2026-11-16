"""Built-in example projects with known bugs, tests, and reference solutions."""
import json
from dataclasses import dataclass
from pathlib import Path

from coach import config
from coach.workspace import Workspace


@dataclass
class Example:
    key: str
    title: str
    description: str
    path: Path

    def workspace(self) -> Workspace:
        return Workspace.from_example(self.path)

    def solution_files(self) -> dict[str, str]:
        """The example's files with the reference solution swapped in."""
        files = dict(self.workspace().files)
        for path in (self.path / "solution").glob("*.py"):
            files[path.name] = path.read_text()
        return files


def list_examples(root: Path = config.EXAMPLES_DIR) -> list[Example]:
    examples = []
    for meta_path in sorted(root.glob("*/example.json")):
        meta = json.loads(meta_path.read_text())
        examples.append(Example(meta_path.parent.name, meta["title"], meta["description"], meta_path.parent))
    # Show the Project 1 game first.
    return sorted(examples, key=lambda e: (e.key != "number_guessing_game", e.title))


def get_example(key: str) -> Example:
    for example in list_examples():
        if example.key == key:
            return example
    raise KeyError(f"Unknown example: {key}")
