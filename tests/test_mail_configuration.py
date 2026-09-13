import json
import base64
import sys
import types
from email import message_from_bytes
from unittest.mock import MagicMock

import pytest

from src.scribe.tools.email_service import EmailService
from src.scribe.tools.email_classifier_tool import EmailClassifierTool
from src.scribe.tools.meeting_notification_tool import MeetingNotificationTool
from src.scribe.tools.recipient_loader_tool import RecipientLoaderTool


@pytest.mark.parametrize("sender", ["reminders@example.com", "second-mailbox@example.com"])
def test_reminder_recognition_uses_configured_sender(monkeypatch, sender):
    monkeypatch.setenv("EMAIL_FROM", sender)
    args = {"cycle": "2030-04", "subject": "Open meeting reminder", "snippet": ""}
    assert EmailService._should_exclude_from_staging(from_addr=f"Secretary <{sender.upper()}>", **args)
    assert not EmailService._should_exclude_from_staging(from_addr="unrelated@example.com", **args)
    monkeypatch.delenv("EMAIL_FROM")
    assert not EmailService._should_exclude_from_staging(from_addr=sender, **args)


@pytest.mark.parametrize("submission,sender,expected", [
    ("reports@example.com", "sender@example.com", "reports@example.com"),
    (None, "sender@example.com", "sender@example.com"),
    (None, None, "reports@example.com"),
])
def test_reminder_template_uses_configured_submission_address(monkeypatch, submission, sender, expected):
    for key, value in [("REPORT_SUBMISSION_EMAIL", submission), ("EMAIL_FROM", sender)]:
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    rendered = MeetingNotificationTool().render_email_from_template("2030-04-04", "regular")
    assert f"Send them to {expected}." in rendered["body"]
    assert f"please email {expected}." in rendered["body"]
    assert "user2@example.com" not in rendered["body"]


def test_private_recipient_directory_overrides_examples(monkeypatch, tmp_path):
    monkeypatch.setenv("RECIPIENTS_DIR", str(tmp_path))
    (tmp_path / "council_members.json").write_text(json.dumps(["officer@example.com"]))
    (tmp_path / "committee_chairs.json").write_text(json.dumps(["chair@example.com"]))
    result = RecipientLoaderTool()._run("open")
    assert result["success"]
    assert [r["email"] for r in result["recipients"]] == ["officer@example.com", "chair@example.com"]
    classifier = EmailClassifierTool()
    assert classifier._load_recipients(None) == ({"officer@example.com"}, {"chair@example.com"})
    # Explicit paths still take priority over environment configuration.
    other = tmp_path / "other"
    other.mkdir()
    assert classifier._load_recipients(str(other)) == (set(), set())


def test_private_structured_recipients_and_example_fallback(monkeypatch, tmp_path):
    monkeypatch.setenv("RECIPIENTS_DIR", str(tmp_path))
    person = {"name": "Example Officer", "email": "officer@example.com", "role": "officer"}
    (tmp_path / "council_members.json").write_text(json.dumps([person]))
    assert RecipientLoaderTool()._run("regular")["recipients"] == [person]
    monkeypatch.delenv("RECIPIENTS_DIR")
    result = RecipientLoaderTool()._run("open")
    assert result["success"]
    assert result["recipients"]
    assert all(r["email"].endswith("@example.com") for r in result["recipients"])


def test_outgoing_mail_uses_configured_sender_with_mock_transport(monkeypatch):
    monkeypatch.setenv("EMAIL_FROM", "configured-sender@example.com")
    monkeypatch.delenv("DEV_OVERRIDE_EMAIL", raising=False)
    transport = MagicMock()
    transport.users.return_value.messages.return_value.send.return_value.execute.return_value = {"id": "mock-id"}
    monkeypatch.setattr(EmailService, "_get_gmail_service", staticmethod(lambda: transport))
    result = EmailService._send_email(["recipient@example.com"], "Test", "Example body", [])
    assert result["success"]
    raw = transport.users.return_value.messages.return_value.send.call_args.kwargs["body"]["raw"]
    message = message_from_bytes(base64.urlsafe_b64decode(raw))
    assert message["From"] == "configured-sender@example.com"
    assert message["To"] == "recipient@example.com"


def test_database_recipients_and_configured_fallback_remain_authoritative(monkeypatch):
    # Mock the database boundary without importing the separately installed Clerk app.
    class DatabaseQueryTool:
        def get_residents_council_officers_mailing_list(self):
            return ["officer@example.com"]

        def get_committee_chairs(self):
            return ["chair@example.com"]

    module = types.ModuleType("scribe.tools.database_query_tool")
    module.DatabaseQueryTool = DatabaseQueryTool
    monkeypatch.setitem(sys.modules, module.__name__, module)
    tool = MeetingNotificationTool()
    assert tool.get_recipients("regular", audit=False) == ["officer@example.com"]
    assert set(tool.get_recipients("open", audit=False)) == {"officer@example.com", "chair@example.com"}
    monkeypatch.setattr(DatabaseQueryTool, "get_residents_council_officers_mailing_list", lambda self: [])
    monkeypatch.setenv("DEFAULT_FALLBACK_EMAIL", "configured-fallback@example.com")
    assert tool.get_recipients("regular", audit=False) == ["configured-fallback@example.com"]
