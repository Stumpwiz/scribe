from pathlib import Path
import json
import datetime

from scribe.ui import create_app
import scribe.ui.routes.reminder_routes as reminder_routes


def test_gui_dry_run_writes_single_canonical_artifact_set(monkeypatch, output_dirs, tmp_path):
    # Keep the historical fixture independent of today's date and isolate the
    # route's relative business-input writes from the repository's source files.
    class FixtureDate(datetime.date):
        @classmethod
        def today(cls):
            return cls(2026, 5, 1)

    monkeypatch.setattr(datetime, "date", FixtureDate)
    monkeypatch.chdir(tmp_path)
    agendas_dir, reminders_dir = output_dirs
    meeting_date = "2026-05-07"
    meeting_type = "regular"
    canonical_agenda = agendas_dir / f"agenda_{meeting_date}_{meeting_type}.pdf"

    def fake_get_recipients(self, meeting_type_arg, meeting_date=None, audit=True):
        assert meeting_type_arg == "regular"
        assert meeting_date == "2026-05-07"
        audit_path = reminders_dir / "20260101_120000_recipients_2026-05-07.json"
        payload = {
            "meeting_date": meeting_date,
            "meeting_type": meeting_type_arg,
            "recipients": [f"user{i}@example.com" for i in range(1, 12)],
        }
        audit_path.write_text(json.dumps(payload), encoding="utf-8")
        return payload["recipients"]

    def fake_agenda_run(self, meeting_info):
        assert meeting_info["meetingDate"] == "2026-05-07"
        assert meeting_info["meetingType"] == "regular"
        canonical_agenda.write_bytes(b"%PDF-1.4\n% gui\n")
        return {
            "success": True,
            "pdfPath": str(canonical_agenda),
            "logPath": str(agendas_dir / "agenda_2026-05-07_regular.log"),
            "log": "ok",
        }

    def fake_notification_run(self, **kwargs):
        assert kwargs["meeting_date"] == "2026-05-07"
        assert kwargs["meeting_type"] == "regular"
        assert kwargs["dry_run"] is True
        draft_path = reminders_dir / "20260101_120001_regular_meeting_2026-05-07.txt"
        draft_path.write_text("canonical preview", encoding="utf-8")
        return {
            "success": True,
            "status": "dry_run",
            "message": "Dry run complete. No email sent.",
            "draft_path": str(draft_path),
            "recipient_count": 11,
            "attachment_path": str(canonical_agenda),
            "recipients": [f"user{i}@example.com" for i in range(1, 12)],
        }

    monkeypatch.setattr(reminder_routes.MeetingNotificationTool, "get_recipients", fake_get_recipients)
    monkeypatch.setattr(reminder_routes.MeetingAgendaGeneratorTool, "_run", fake_agenda_run)
    monkeypatch.setattr(reminder_routes.MeetingNotificationTool, "_run", fake_notification_run)

    app = create_app()
    client = app.test_client()

    response = client.post(
        "/",
        data={
            "meeting_date": meeting_date,
            "old_business": "",
            "new_business": "",
            "dry_run": "on",
        },
    )
    assert response.status_code == 200

    stale_files = list(reminders_dir.glob("*2025-09-20*"))
    assert stale_files == []

    audit_files = list(reminders_dir.glob("*_recipients_2026-05-07.json"))
    assert len(audit_files) == 1

    canonical_preview_files = list(reminders_dir.glob("*_regular_meeting_2026-05-07.txt"))
    assert len(canonical_preview_files) == 1

    generic_preview_files = list(reminders_dir.glob("*_meeting_notification.txt"))
    assert generic_preview_files == []

    assert canonical_agenda.exists()
