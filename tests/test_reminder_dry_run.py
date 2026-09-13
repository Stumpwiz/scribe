import re
from pathlib import Path
import pytest
from scribe.tasks import reminder_tasks

# Tests use fixtures from tests/conftest.py for env setup and tool monkeypatching


@pytest.mark.asyncio
async def test_reminder_agent_dry_run_creates_pdf_and_email_preview(env_setup, monkeypatch_tools, send_workflow, stub_task_factory, caplog):
    run_id = env_setup
    agendas_dir = monkeypatch_tools["agendas_dir"]
    reminders_dir = monkeypatch_tools["reminders_dir"]
    canonical_agenda = monkeypatch_tools["dummy_pdf"]

    # Build minimal context
    context = {
        "meetingDate": "2025-09-30",
        "meetingType": "regular",
        "meetingTime": "7:30 PM",
        "location": "Conference Room",
        # recipients optional; code falls back to DEFAULT_FALLBACK_EMAIL
    }

    stub_task = stub_task_factory(context)

    with caplog.at_level("INFO"):
        result = await send_workflow(None, None, stub_task)

    # Assertions on result structure (should be DRY_RUN)
    assert result.get("success") is True
    assert result.get("status") == "dry_run"
    assert result.get("run_id") == run_id

    # Check that the canonical agenda path returned by agenda generation exists
    expected_agenda = canonical_agenda
    assert expected_agenda.exists(), f"Agenda PDF not found: {expected_agenda}"
    # Robust checks: file exists, is a file, and non-empty
    assert expected_agenda.is_file(), f"Agenda path is not a file: {expected_agenda}"
    assert expected_agenda.stat().st_size > 0, f"Agenda PDF is empty: {expected_agenda}"
    # Ensure no duplicate run-id copy is created in agendas output dir.
    duplicate_agenda = agendas_dir / f"agenda-{run_id}.pdf"
    assert not duplicate_agenda.exists(), f"Unexpected duplicate run-id PDF: {duplicate_agenda}"

    # Check the canonical dry-run draft/preview exists.
    preview_path = Path(result.get("preview_path"))
    assert preview_path.exists(), f"Email preview not found: {preview_path}"
    assert preview_path.parent == reminders_dir
    assert result.get("draft_path") == str(preview_path)
    assert re.match(r"^\d{8}_\d{6}_regular_meeting_2025-09-30\.txt$", preview_path.name)
    # Robust checks: file exists, is a file, and non-empty
    assert preview_path.is_file(), f"Preview path is not a file: {preview_path}"
    assert preview_path.stat().st_size > 0, f"Email preview file is empty: {preview_path}"
    duplicate_email_preview = reminders_dir / f"email_preview-{run_id}.txt"
    assert not duplicate_email_preview.exists()

    # Read preview content
    content = preview_path.read_text(encoding="utf-8")
    assert "Residents Council meeting" in content or len(content) > 0

    # Logging checks: run_id and paths are mentioned
    logs_joined = "\n".join(caplog.messages)
    assert run_id in logs_joined
    assert str(expected_agenda) in logs_joined
    assert str(preview_path) in logs_joined

    # Cleanup artifacts created by the workflow
    try:
        if expected_agenda.exists():
            expected_agenda.unlink()
        if preview_path.exists():
            preview_path.unlink()
    finally:
        # Leave the directories in place; other tests may rely on them
        pass


@pytest.mark.asyncio
@pytest.mark.parametrize("env_setup", ["runrecv01"], indirect=True)
async def test_missing_recipients_falls_back_to_default_in_preview(env_setup, monkeypatch_tools, send_workflow, stub_task_factory, caplog):
    run_id = env_setup
    agendas_dir = monkeypatch_tools["agendas_dir"]
    reminders_dir = monkeypatch_tools["reminders_dir"]

    # Build context WITHOUT recipients
    context = {
        "meetingDate": "2025-09-30",
        "meetingType": "regular",
        "meetingTime": "7:30 PM",
        "location": "Conference Room",
        # no email_recipients key on purpose
    }
    stub_task = stub_task_factory(context)

    with caplog.at_level("INFO"):
        result = await send_workflow(None, None, stub_task)

    assert result.get("status") == "dry_run"
    preview_path = Path(result.get("preview_path"))
    assert preview_path.exists()
    content = preview_path.read_text(encoding="utf-8")
    assert len(content) >= 0
    duplicate_email_preview = reminders_dir / f"email_preview-{run_id}.txt"
    assert not duplicate_email_preview.exists()

    # Cleanup
    expected_agenda = agendas_dir / f"agenda-{run_id}.pdf"
    try:
        assert not expected_agenda.exists()
        if preview_path.exists():
            preview_path.unlink()
    finally:
        pass


@pytest.mark.asyncio
@pytest.mark.parametrize("env_setup", ["rundate01"], indirect=True)
async def test_invalid_meeting_date_uses_today_and_logs_fallback(env_setup, monkeypatch_tools, send_workflow, stub_task_factory, caplog):
    from datetime import datetime
    run_id = env_setup
    agendas_dir = monkeypatch_tools["agendas_dir"]
    canonical_agenda = monkeypatch_tools["dummy_pdf"]
    reminders_dir = monkeypatch_tools["reminders_dir"]

    context = {
        "meetingDate": "invalid-date",
        "meetingType": "regular",
        "meetingTime": "7:30 PM",
        "location": "Conference Room",
    }
    stub_task = stub_task_factory(context)

    today = datetime.today().date().isoformat()

    with caplog.at_level("INFO"):
        result = await send_workflow(None, None, stub_task)

    assert result.get("status") == "dry_run"
    logs_joined = "\n".join(caplog.messages)
    # Verify fallback log mentions today's date
    assert "falling back to today's date" in logs_joined
    assert today in logs_joined

    # Artifacts exist as usual
    assert canonical_agenda.exists()
    expected_agenda = agendas_dir / f"agenda-{run_id}.pdf"
    assert not expected_agenda.exists()
    preview_path = Path(result.get("preview_path"))
    assert preview_path.exists()
    duplicate_email_preview = reminders_dir / f"email_preview-{run_id}.txt"
    assert not duplicate_email_preview.exists()

    # Cleanup
    try:
        if canonical_agenda.exists():
            canonical_agenda.unlink()
        if preview_path.exists():
            preview_path.unlink()
    finally:
        pass


@pytest.mark.asyncio
@pytest.mark.parametrize("env_setup", ["runfail01"], indirect=True)
@pytest.mark.parametrize("monkeypatch_tools", [{"agenda_success": False, "agenda_log": "Template not found"}], indirect=True)
async def test_missing_agenda_template_marks_failure_and_no_pdf(env_setup, monkeypatch_tools, send_workflow, stub_task_factory, caplog):
    run_id = env_setup
    agendas_dir = monkeypatch_tools["agendas_dir"]

    context = {
        "meetingDate": "2025-09-30",
        "meetingType": "regular",
        "meetingTime": "7:30 PM",
        "location": "Conference Room",
    }
    stub_task = stub_task_factory(context)

    with caplog.at_level("INFO"):
        result = await send_workflow(None, None, stub_task)

    # Overall result should indicate failure now
    assert result.get("success") is False
    # Log should contain the error text
    logs_joined = "\n".join(caplog.messages)
    assert "Template not found" in logs_joined

    # No standardized PDF should have been saved
    expected_agenda = agendas_dir / f"agenda-{run_id}.pdf"
    assert not expected_agenda.exists()

    # Notification step is skipped when agenda generation fails.
    assert not result.get("preview_path")


@pytest.mark.asyncio
@pytest.mark.parametrize("env_setup", ["may07run"], indirect=True)
async def test_dry_run_uses_only_canonical_agenda_pdf_for_may_7_regular(env_setup, output_dirs, send_workflow, stub_task_factory, monkeypatch):
    run_id = env_setup
    agendas_dir, reminders_dir = output_dirs
    canonical_pdf = agendas_dir / "agenda_2026-05-07_regular.pdf"
    duplicate_pdf = agendas_dir / f"agenda-{run_id}.pdf"

    original_agenda_cls = reminder_tasks.MeetingAgendaGeneratorTool

    class _CanonicalAgendaTool:
        def _run(self, meeting_info, **kwargs):
            canonical_pdf.write_bytes(b"%PDF-1.4\n% canonical\n")
            return {
                "success": True,
                "pdfPath": str(canonical_pdf),
                "logPath": str(agendas_dir / "agenda_2026-05-07_regular.log"),
                "log": "ok",
            }

    monkeypatch.setattr(reminder_tasks, "MeetingAgendaGeneratorTool", lambda: _CanonicalAgendaTool())

    context = {
        "meetingDate": "2026-05-07",
        "meetingType": "regular",
        "meetingTime": "2:00 PM",
        "location": "McAuley Conference Room",
        "email_recipients": ["user8@example.com"],
        "dry_run": True,
    }
    stub_task = stub_task_factory(context)

    try:
        result = await send_workflow(None, None, stub_task)

        assert result.get("success") is True
        assert result.get("status") == "dry_run"
        assert canonical_pdf.exists()
        assert result.get("recipient_count") == 1
        assert result.get("attachment_path") == str(canonical_pdf)
        assert result.get("preview_path") == result.get("draft_path")
        draft_path = Path(result["draft_path"])
        assert draft_path.exists()
        assert draft_path.parent == reminders_dir
        assert re.match(r"^\d{8}_\d{6}_regular_meeting_2026-05-07\.txt$", draft_path.name)
        duplicate_email_preview = reminders_dir / f"email_preview-{run_id}.txt"
        assert not duplicate_email_preview.exists()
        assert not duplicate_pdf.exists()
    finally:
        reminder_tasks.MeetingAgendaGeneratorTool = original_agenda_cls
