"""AI Debugging Coach - Streamlit app.

Run with:  streamlit run app.py
"""
import streamlit as st
from dotenv import load_dotenv

from coach import config
from coach.agent import STATUS_LABELS, DebugSession, SessionError
from coach.examples import list_examples
from coach.llm import LLMError, create_llm, llm_status, local_models
from coach.report import build_report, reliability_rows, split_code
from coach.workspace import Workspace, WorkspaceError

load_dotenv()
st.set_page_config(page_title="AI Debugging Coach", page_icon="🩺", layout="wide")

STATUS_STYLE = {
    "fixed": st.success,
    "partially_fixed": st.warning,
    "unverified": st.info,
    "needs_user_input": st.info,
    "unable_to_fix": st.error,
}
FINDING_BADGE = {"confirmed": "🟢 Confirmed", "likely": "🟡 Likely", "unknown": "⚪ Unknown"}


def run_action(label, fn, *args):
    """Run a workflow step with a spinner, turning failures into friendly messages."""
    try:
        with st.spinner(label):
            fn(*args)
    except (LLMError, SessionError, WorkspaceError) as e:
        st.session_state.error = str(e)
    st.rerun()


# ----- sidebar ------------------------------------------------------------

with st.sidebar:
    st.header("🩺 AI Debugging Coach")
    st.caption("Understand, fix, and verify Python bugs.")

    active: DebugSession | None = st.session_state.get("session")

    st.subheader("Settings")
    model = config.MODEL
    if config.PROVIDER == "ollama":
        downloaded = local_models() or []
        choices = sorted(set(downloaded) | {config.MODEL})
        model = st.selectbox(
            "Model", choices, index=choices.index(config.MODEL), disabled=active is not None,
            help="Models downloaded with `ollama pull`. Bigger models (e.g. qwen2.5-coder:7b) "
                 "fix harder bugs but need more memory and time.",
        )
        st.caption("Free, runs locally with Ollama.")
    else:
        st.caption(f"Model: `{model}` (Claude API) · effort `{config.EFFORT}`")

    model_ready, model_message = llm_status(model)
    if model_ready:
        st.success(model_message, icon="🤖")
    else:
        st.error(model_message, icon="🤖")

    auto_mode = st.toggle(
        "Run automatically", value=False,
        help="Off: you review and approve each patch before tests run. "
             "On: the coach runs the whole loop by itself (still only in a sandbox).",
    )
    max_attempts = st.slider(
        "Max repair attempts", 1, config.MAX_ATTEMPTS, config.MAX_ATTEMPTS, disabled=active is not None,
        help="The most patches the coach may try before stopping. It is a limit, not a countdown.",
    )
    if active is not None:
        st.caption(f"Attempts used: **{len(active.attempts)} of {active.max_attempts}**. "
                   "Model and attempt limit are fixed for this session; click Start over to change them.")

    if st.button("Start over", width="stretch"):
        st.session_state.pop("session", None)
        st.rerun()

    with st.expander("Guardrails"):
        st.markdown(
            "- Only `pytest` is ever run, with fixed arguments\n"
            "- Tests run in a temporary sandbox copy; your files are never changed\n"
            f"- Tests time out after {config.TEST_TIMEOUT_SECONDS} s\n"
            "- Test files are protected from edits\n"
            "- A patch must name the function it changes and may only edit inside it\n"
            f"- At most {config.MAX_ATTEMPTS} repair attempts\n"
            "- A patch is kept only if it fixes tests without breaking passing ones\n"
            "- \"Fixed\" is decided by test results, never by the AI"
        )

st.title("🩺 AI Debugging Coach")

if "error" in st.session_state:
    st.error(st.session_state.pop("error"))

session: DebugSession | None = st.session_state.get("session")

# ----- input --------------------------------------------------------------

if session is None:
    st.write("Give the coach some broken Python code. It will explain what is wrong, "
             "propose a small fix, and check it with tests.")
    source = st.radio("Code source", ["Built-in example", "Paste my own code"], horizontal=True)

    if source == "Built-in example":
        example = st.selectbox("Example", list_examples(), format_func=lambda e: e.title)
        workspace = example.workspace()
        st.caption(example.description)
        with st.expander(f"View files ({len(workspace.files)})"):
            for path, content in workspace.files.items():
                label = "test file (protected)" if path in workspace.test_files else "editable"
                st.markdown(f"**`{path}`** · {label}")
                st.code(content, language="python", line_numbers=True)
        workspace.symptom = st.text_area("What is going wrong?", workspace.symptom, key=f"symptom-{example.key}")
        workspace.error = st.text_area("Error message or traceback (optional)", workspace.error,
                                       key=f"error-{example.key}")
    else:
        workspace = None
        col1, col2 = st.columns(2)
        with col1:
            filename = st.text_input("File name", "solution.py")
            code = st.text_area("Python code", height=320, placeholder="def add(a, b):\n    return a - b")
        with col2:
            tests = st.text_area(
                "Pytest tests (optional, but needed to verify a fix)", height=180,
                placeholder="from solution import add\n\ndef test_add():\n    assert add(2, 3) == 5",
            )
            error = st.text_area("Error message or traceback (optional)", height=100)
        symptom = st.text_area("What is going wrong?", placeholder="add(2, 3) returns -1 instead of 5.")

    if st.button("Start debugging", type="primary", disabled=not model_ready):
        try:
            if workspace is None:
                workspace = Workspace.from_paste(code, tests, filename=filename, symptom=symptom, error=error)
            new_session = DebugSession(workspace, create_llm(model), max_attempts=max_attempts)
        except WorkspaceError as e:
            st.error(str(e))
            st.stop()
        st.session_state.session = new_session
        run_action("Inspecting the code and diagnosing the bug...",
                   new_session.run_auto if auto_mode else new_session.start)
    st.stop()

# ----- session view -------------------------------------------------------

ws = session.workspace
st.caption(f"Debugging **{ws.name}** · session `{session.id}`")

if session.done:
    STATUS_STYLE[session.status](f"**{STATUS_LABELS[session.status]}.** {session.stop_reason}")

# 1. Inspect
st.header("1. Inspect")
if session.baseline:
    st.write(f"**Before any changes:** {session.baseline.headline()}")
    if session.baseline.cases:
        with st.expander("Test results before the fix"):
            st.dataframe(
                [{"Test": c.name, "Result": c.outcome, "Message": c.message} for c in session.baseline.cases],
                width="stretch", hide_index=True,
            )

# 2. Diagnosis and 3. Explanation
d = session.diagnosis
if d:
    st.header("2. Diagnosis")
    st.write(d.problem_summary)
    st.markdown(f"**Root cause:** {d.root_cause}")
    st.markdown(f"**Confidence:** {d.confidence}")
    for f in d.findings:
        with st.container(border=True):
            st.markdown(f"{FINDING_BADGE[f.status]} · `{f.file}` · `{f.function}` · lines {f.lines}")
            st.write(f.summary)
            st.caption(f"Evidence: {f.evidence}")
    if d.questions_for_user:
        st.info("**The coach needs more information:**\n\n" + "\n".join(f"- {q}" for q in d.questions_for_user))

    st.header("3. Explanation")
    st.markdown(f"**Concept:** {d.concept}")
    explanation, explanation_code = split_code(d.explanation)
    example_prose, example_code = split_code(d.small_example)
    st.write(explanation)
    code = "\n\n".join(c for c in (explanation_code, example_code) if c)
    if session.done and (code or example_prose):
        st.markdown("**Example**")
        if example_prose:
            st.write(example_prose)
        if code:
            st.code(code, language="python")
    elif code or example_prose:
        st.caption("💡 The code example is hidden until the fix has been tested, "
                   "so you can try to work out the fix yourself first.")

# 4. Patches and test results
if session.attempts or (session.phase == "diagnosed" and not session.done):
    st.header("4. Fix, test, and review")

for a in session.attempts:
    icon = {"proposed": "📝", "invalid": "⛔", "rejected": "↩️"}.get(a.state, "✅" if a.kept else "❌")
    with st.expander(f"{icon} Attempt {a.number} of {session.max_attempts}: {a.proposal.plan}",
                     expanded=a is session.attempts[-1]):
        st.markdown("**Targets:** " + ", ".join(
            f"`{t.file}` `{t.function}` (lines {t.lines})" for t in a.proposal.targets))
        if a.state == "invalid":
            st.error(f"Blocked by a guardrail before anything ran: {a.error}")
            continue
        for diff in a.diff:
            st.markdown(f"`{diff.path}` · +{diff.added} −{diff.removed}")
            st.code(diff.unified, language="diff")
        st.markdown(f"**Summary:** {a.proposal.summary}")
        if a.proposal.assumptions:
            st.markdown("**Assumptions:**\n" + "\n".join(f"- {x}" for x in a.proposal.assumptions))

        if a.state == "proposed":
            st.info("Nothing has run yet. Approve to test this patch in a sandbox copy of the project.")
            feedback = st.text_input("Reason for rejecting (optional, helps the next attempt)", key=f"fb-{a.number}")
            c1, c2, _ = st.columns([1, 1, 3])
            if c1.button("✅ Approve and run tests", type="primary", key=f"ok-{a.number}"):
                run_action("Running tests in the sandbox...", session.approve)
            if c2.button("↩️ Reject", key=f"no-{a.number}"):
                run_action("Recording your feedback...", session.reject, feedback)
        elif a.state == "rejected":
            st.warning(f"Rejected: {a.user_feedback or 'no reason given'}")
        elif a.test_run:
            (st.success if a.kept else st.error)(
                f"**Tests:** {a.test_run.headline()} · Patch {'kept' if a.kept else 'discarded'}: {a.keep_reason}")
            with st.expander("Test output"):
                st.code(a.test_run.output or "(no output)", language="text")
            if a.analysis:
                st.markdown("**What the failures mean**")
                for e in a.analysis.explanations:
                    st.markdown(f"- `{e.test_name}`: {e.meaning}")
                st.markdown(f"**Caused by this patch?** {a.analysis.caused_by_patch}")
                st.markdown(f"**Progress:** {a.analysis.progress}")
                st.markdown(f"**Next step:** {a.analysis.next_step}")

if session.phase == "diagnosed" and not session.done:
    last = session.attempts[-1] if session.attempts else None
    feedback = last.user_feedback if last and last.state == "rejected" else ""
    label = "Propose a fix" if not last else f"Try another fix ({session.attempts_left} left)"
    st.caption("Click to generate a patch. Nothing runs until you approve it."
               if not auto_mode else "Run automatically is on: the coach will propose, test and retry by itself.")
    c1, c2, _ = st.columns([1, 1, 3])
    if c1.button(label, type="primary"):
        if auto_mode:
            run_action("Running the repair loop...", session.run_auto)
        else:
            run_action("Planning a minimal fix...", session.propose, feedback)
    if c2.button("Stop here"):
        run_action("Writing the report...", session.finish, "Stopped by the user.")

# 5. Report and 6. Follow-up
if session.done:
    st.header("5. Report")
    st.subheader("Reliability summary")
    st.table([{"Check": c, "Result": r} for c, r in reliability_rows(session)])

    report = build_report(session)
    with st.expander("Full debugging report", expanded=True):
        st.markdown(report)
    c1, c2 = st.columns(2)
    c1.download_button("Download report (.md)", report, file_name=f"debug-report-{session.id}.md")
    changed = [p for p in sorted(ws.editable) if session.current_files[p] != session.original_files[p]]
    for path in changed:
        c2.download_button(f"Download fixed {path}", session.current_files[path],
                           file_name=path.split("/")[-1], key=f"dl-{path}")

    st.header("6. Ask a follow-up question")
    for msg in session.chat:
        st.chat_message(msg["role"]).markdown(msg["content"])
    question = st.chat_input("e.g. What would happen if the user enters a decimal?")
    if question:
        run_action("Thinking...", session.ask, question)

with st.expander("Workflow log"):
    for e in session.log.events:
        st.text(f"{e.time} {e.level:<7} {e.message}")
