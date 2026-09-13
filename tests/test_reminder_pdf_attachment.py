import asyncio
from pathlib import Path

from scribe.tasks import reminder_tasks


class StubAgendaTool:
    def __init__(self, pdf_path):
        self._pdf_path = pdf_path
    def _run(self, meeting_info, **kwargs):
        # Pretend agenda generation succeeded and returned a PDF path
        return {"success": True, "pdfPath": str(self._pdf_path), "logPath": "", "log": "ok"}


class MockTask:
    def __init__(self, context):
        self.context = context


class MockAgent:
    name = "ReminderAgentTest"


def test_send_meeting_notification_includes_pdf_attachment(tmp_path):
    # Arrange: create a dummy PDF file that the agenda tool will "generate"
    dummy_pdf = tmp_path / "dummy.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4\n% Test PDF content\n")

    # Patch MeetingAgendaGeneratorTool inside the reminder_tasks module
    original_agenda_tool_cls = reminder_tasks.MeetingAgendaGeneratorTool
    reminder_tasks.MeetingAgendaGeneratorTool = lambda: StubAgendaTool(dummy_pdf)

    # Capture arguments passed to MeetingNotificationTool._run
    captured = {}
    original_notification_run = reminder_tasks.MeetingNotificationTool._run

    def stub_notification_run(self, **kwargs):
        captured.update(kwargs)
        agenda_result = kwargs.get("agenda_result") or {}
        return {
            "success": True,
            "status": "dry_run",
            "message": "Dry run complete. No email sent.",
            "draft_path": str(tmp_path / "draft.txt"),
            "recipient_count": len(kwargs.get("recipients") or []),
            "attachment_path": agenda_result.get("pdfPath") or "",
            "recipients": kwargs.get("recipients") or [],
        }

    reminder_tasks.MeetingNotificationTool._run = stub_notification_run

    try:
        # Prepare context
        context = {
            "meetingDate": "2026-05-07",
            "meetingType": "regular",
            "meetingTime": "7:30 PM",
            "location": "Conference Room A",
            "email_recipients": ["test@example.com"],
        }
        task = MockTask(context)
        agent = MockAgent()

        # Act: run the async workflow
        result = asyncio.get_event_loop().run_until_complete(
            reminder_tasks.send_meeting_notification_workflow(None, agent, task)
        )

        # Assert: canonical PDF path was forwarded to notification tool.
        assert result.get("success") is True
        assert result.get("status") == "dry_run"
        agenda_result = captured.get("agenda_result")
        assert isinstance(agenda_result, dict)
        attachment_path = agenda_result.get("pdfPath")
        assert attachment_path is not None
        assert attachment_path.endswith(".pdf")
        assert Path(attachment_path).exists()
        assert Path(attachment_path).resolve() == dummy_pdf.resolve()
        assert result.get("attachment_path") == str(dummy_pdf)
    finally:
        # Restore patches
        reminder_tasks.MeetingAgendaGeneratorTool = original_agenda_tool_cls
        reminder_tasks.MeetingNotificationTool._run = original_notification_run
