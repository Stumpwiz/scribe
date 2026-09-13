import os
from pathlib import Path
import pytest


@pytest.fixture
def env_setup(monkeypatch, request):
    """
    Set common environment variables for DRY_RUN tests.
    Allows overriding RUN_ID via indirect parametrization, e.g.:
      @pytest.mark.parametrize("env_setup", ["myrunid"], indirect=True)
    Returns the run_id used.
    """
    run_id = getattr(request, "param", "abcd1234")
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("RUN_ID", run_id)
    monkeypatch.setenv("EMAIL_FROM", "user7@example.com")
    monkeypatch.setenv("DEFAULT_FALLBACK_EMAIL", "user8@example.com")
    return run_id


@pytest.fixture
def dummy_pdf(tmp_path: Path) -> Path:
    """Create and return a small dummy PDF file path."""
    p = tmp_path / "dummy.pdf"
    p.write_bytes(b"%PDF-1.4\n% Dummy agenda PDF for tests\n")
    return p


@pytest.fixture
def output_dirs():
    """
    Ensure standard output directories exist and yield them (agendas_dir, reminders_dir).
    After the test finishes (even on failure), clean up any files created under
    src/scribe/output while preserving the directory structure.
    """
    project_src = Path(__file__).resolve().parents[1] / "src" / "scribe"
    output_root = project_src / "output"
    agendas_dir = output_root / "agendas"
    reminders_dir = output_root / "reminders"

    # Ensure known dirs exist; future subfolders may be created by code under output/
    agendas_dir.mkdir(parents=True, exist_ok=True)
    reminders_dir.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=True, exist_ok=True)

    # Provide the directories to tests
    yield agendas_dir, reminders_dir

    # Teardown: remove files from all output subfolders (agendas, reminders, logs, test, etc.)
    def _clean_dir(root: Path):
        try:
            # Use glob to iterate direct children, then recurse into subfolders
            for entry in root.glob("*"):
                try:
                    if entry.is_file():
                        try:
                            entry.unlink()
                        except FileNotFoundError:
                            pass
                        except Exception:
                            # Ignore deletion errors during cleanup
                            pass
                    elif entry.is_dir():
                        # Clean files in subdirectories recursively, but do not remove dirs themselves
                        _clean_dir(entry)
                except Exception:
                    # Continue on any unexpected error to avoid blocking teardown
                    pass
        except Exception:
            pass

    _clean_dir(output_root)


@pytest.fixture
def monkeypatch_tools(monkeypatch, dummy_pdf: Path, tmp_path: Path, output_dirs, request):
    """
    Monkeypatch the agenda generator and notification tools to predictable behaviors.
    Usage:
      - default: success True with dummy_pdf and log "ok"
      - override via indirect parametrization providing a dict, e.g.:
        @pytest.mark.parametrize("monkeypatch_tools", [{"agenda_success": False, "agenda_log": "Template not found"}], indirect=True)
    Returns a dict with keys: agendas_dir, reminders_dir, dummy_pdf.
    """
    params = getattr(request, "param", {}) or {}
    agenda_success = params.get("agenda_success", True)
    agenda_log = params.get("agenda_log", "ok")

    from scribe.tools import meeting_agenda_generator_tool as magt
    from scribe.tools import meeting_notification_tool as mnt

    def fake_agenda_run(self, meeting_info):
        if agenda_success:
            return {
                "success": True,
                "pdfPath": str(dummy_pdf),
                "logPath": str(tmp_path / "compile.log"),
                "log": agenda_log,
            }
        else:
            return {
                "success": False,
                "pdfPath": None,
                "log": agenda_log,
            }

    monkeypatch.setattr(magt.MeetingAgendaGeneratorTool, "_run", fake_agenda_run)

    def fake_notification_run(self, **kwargs):
        meeting_type = kwargs.get("meeting_type", "regular")
        meeting_date = kwargs.get("meeting_date", "unknown-date")
        draft_name = f"20260101_120000_{meeting_type}_meeting_{meeting_date}.txt"
        draft_path = reminders_dir / draft_name
        draft_content = kwargs.get("content") or f"Draft for {meeting_type} meeting on {meeting_date}"
        draft_path.write_text(draft_content, encoding="utf-8")
        agenda_result = kwargs.get("agenda_result") or {}
        recipients = kwargs.get("recipients") or []
        return {
            "success": True,
            "status": "dry_run",
            "message": "Dry run complete. No email sent.",
            "draft_path": str(draft_path),
            "recipient_count": len(recipients),
            "attachment_path": agenda_result.get("pdfPath") or "",
            "recipients": recipients,
        }

    monkeypatch.setattr(mnt.MeetingNotificationTool, "_run", fake_notification_run)

    agendas_dir, reminders_dir = output_dirs
    return {"agendas_dir": agendas_dir, "reminders_dir": reminders_dir, "dummy_pdf": dummy_pdf}


@pytest.fixture
def send_workflow():
    from scribe.tasks.reminder_tasks import send_meeting_notification_workflow
    return send_meeting_notification_workflow


@pytest.fixture
def stub_task_factory():
    class _StubTask:
        def __init__(self, context):
            self.context = context

    def factory(context: dict):
        return _StubTask(context)

    return factory
