"""Structured outputs the AI must return at each step of the workflow.

Claude's responses are constrained to these Pydantic models, so the
application logic can validate every field before acting on it.
"""
from typing import Literal

from pydantic import BaseModel, Field

Confidence = Literal["high", "medium", "low"]


class Finding(BaseModel):
    status: Literal["confirmed", "likely", "unknown"] = Field(
        description=(
            "confirmed = directly shown by the code or test output; "
            "likely = a reasonable hypothesis; unknown = needs more information"
        )
    )
    summary: str = Field(description="One sentence describing the problem.")
    evidence: str = Field(
        description="The test failure, error line, or code that supports this finding."
    )
    file: str
    function: str = Field(description='Function name, or "<module>" for top-level code.')
    lines: str = Field(description='Line numbers from the numbered listing, e.g. "31-38".')


class Diagnosis(BaseModel):
    problem_summary: str = Field(description="What the user is experiencing, in one or two sentences.")
    findings: list[Finding]
    root_cause: str = Field(description="Why the bug happens, in plain language.")
    confidence: Confidence
    needs_more_info: bool = Field(
        description="True only if the bug cannot be located without more input from the user."
    )
    questions_for_user: list[str] = Field(
        description="Questions to ask when needs_more_info is true; otherwise empty."
    )
    concept: str = Field(description='The programming concept involved, e.g. "state management".')
    explanation: str = Field(
        description=(
            "Beginner-friendly explanation: the concept, the specific code causing the "
            "problem, and why the observed behavior happens. No fixed code yet."
        )
    )
    small_example: str = Field(
        description="A tiny standalone code example that illustrates the concept, or an empty string."
    )


class Target(BaseModel):
    file: str
    function: str = Field(description='Function to change, or "<module>" for top-level code.')
    lines: str = Field(description="Line numbers being changed, from the numbered listing.")


class Edit(BaseModel):
    file: str
    function: str = Field(description="Must match one of the declared targets.")
    find: str = Field(
        description=(
            "Exact text copied from the current file (without line numbers) to replace. "
            "Include enough lines to be unique."
        )
    )
    replace: str = Field(description="The new text that replaces `find`.")


class PatchProposal(BaseModel):
    targets: list[Target] = Field(
        description="The functions and lines that must change, identified before editing."
    )
    plan: str = Field(description="The minimal repair, in one to three sentences.")
    edits: list[Edit]
    summary: str = Field(
        description='What changed and what did not, e.g. "No scoring or hint logic was changed."'
    )
    assumptions: list[str]


class FailedTestExplanation(BaseModel):
    test_name: str
    meaning: str = Field(description="What this failure tells us, in plain language.")


class FailureAnalysis(BaseModel):
    explanations: list[FailedTestExplanation]
    caused_by_patch: Literal["yes", "no", "partly", "unclear"] = Field(
        description="Did the latest patch cause any of these failures?"
    )
    progress: str = Field(description="What the latest patch did fix, if anything.")
    next_step: str = Field(description="The change that should be attempted next.")
    recommendation: Literal["retry", "needs_user_input", "give_up"]


class QualityIssue(BaseModel):
    category: Literal[
        "duplicated logic",
        "unused code",
        "input validation",
        "naming",
        "exception handling",
        "missing tests",
        "other",
    ]
    description: str
    severity: Literal["minor", "moderate"]


class QualityReview(BaseModel):
    issues: list[QualityIssue]
    suggested_tests: list[str] = Field(
        description="Short descriptions of tests that would protect the changed behavior."
    )
    concept_learned: str = Field(
        description="The main programming lesson from this bug, in one or two sentences."
    )
