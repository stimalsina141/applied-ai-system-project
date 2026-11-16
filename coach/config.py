"""Settings for the coach. Values can be overridden with environment variables."""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = PROJECT_ROOT / "examples"
LOG_DIR = Path(os.getenv("COACH_LOG_DIR", PROJECT_ROOT / "logs"))

MODEL = os.getenv("COACH_MODEL", "claude-opus-5-5")
EFFORT = os.getenv("COACH_EFFORT", "medium")
MAX_OUTPUT_TOKENS = 16000
API_TIMEOUT_SECONDS = 180

# Guardrails
MAX_ATTEMPTS = int(os.getenv("COACH_MAX_ATTEMPTS", "3"))
TEST_TIMEOUT_SECONDS = int(os.getenv("COACH_TEST_TIMEOUT", "30"))
MAX_FILES = 10
MAX_TOTAL_CODE_CHARS = 60_000
MAX_TEST_OUTPUT_CHARS = 6_000
