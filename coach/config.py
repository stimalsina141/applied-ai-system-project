"""Settings for the coach. Values can be overridden with environment variables."""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = PROJECT_ROOT / "examples"
LOG_DIR = Path(os.getenv("COACH_LOG_DIR", PROJECT_ROOT / "logs"))

# "ollama" (default) runs a free model on your own computer; "claude" uses the paid Anthropic API.
PROVIDER = os.getenv("COACH_PROVIDER", "ollama").strip().lower()
# The 3B model fits in the GPU memory of an 8 GB laptop; use qwen2.5-coder:7b with 16 GB or more.
MODEL = os.getenv("COACH_MODEL", "qwen2.5-coder:3b" if PROVIDER == "ollama" else "claude-opus-5-5")
EFFORT = os.getenv("COACH_EFFORT", "medium")  # Claude only
OLLAMA_URL = os.getenv("COACH_OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_CONTEXT_TOKENS = int(os.getenv("COACH_OLLAMA_CONTEXT", "8192"))
MAX_OUTPUT_TOKENS = 16000
API_TIMEOUT_SECONDS = 180
LOCAL_TIMEOUT_SECONDS = 600  # local models on a laptop are much slower

# Guardrails
MAX_ATTEMPTS = int(os.getenv("COACH_MAX_ATTEMPTS", "3"))
TEST_TIMEOUT_SECONDS = int(os.getenv("COACH_TEST_TIMEOUT", "30"))
MAX_FILES = 10
MAX_TOTAL_CODE_CHARS = 60_000
MAX_TEST_OUTPUT_CHARS = 6_000
