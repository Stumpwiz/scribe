from unittest.mock import MagicMock

import pytest

from src.scribe.tools.email_service import EmailService


def part(filename, mime, disposition="attachment"):
    return {
        "filename": filename,
        "mimeType": mime,
        "headers": [
            {"name": "Content-Disposition", "value": f'{disposition}; filename="{filename}"'},
            {"name": "Content-ID", "value": f"<{filename}>"},
        ],
        "body": {"attachmentId": filename, "size": 100},
    }


@pytest.mark.parametrize("extension,mime", [
    ("pdf", "application/pdf"),
    ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
])
@pytest.mark.parametrize("dry_run", [True, False])
def test_document_with_inline_images_stages_only_document(monkeypatch, tmp_path, extension, mime, dry_run):
    filename = f"Management Report.{extension}"
    payload = {
        "headers": [
            {"name": "From", "value": "forwarder@example.com"},
            {"name": "Subject", "value": "Executive Director report"},
        ],
        "parts": [{"parts": [
            part("signature.jpg", "image/jpeg", "INLINE"),
            part("banner.png", "image/png", "inline"),
        ]}, part(filename, mime)],
    }
    service = MagicMock()
    service.users().messages().get().execute.return_value = {
        "id": "test-message", "threadId": "test-thread", "payload": payload,
        "internalDate": "1788600000000", "labelIds": [],
    }
    monkeypatch.setattr(EmailService, "_get_gmail_service", staticmethod(lambda: service))
    monkeypatch.setattr(EmailService, "_list_message_ids", staticmethod(lambda **kw: ["test-message"]))
    monkeypatch.setattr(EmailService, "_get_label_id_if_exists", staticmethod(lambda **kw: None))
    monkeypatch.setattr(EmailService, "_ensure_label", staticmethod(lambda **kw: "incoming"))
    monkeypatch.setattr(EmailService, "_apply_label", staticmethod(lambda **kw: True))
    downloaded = []

    def download(**kwargs):
        downloaded.append(kwargs["attachment_id"])
        return b"report bytes"

    monkeypatch.setattr(EmailService, "_download_attachment_bytes", staticmethod(download))
    result = EmailService.stage_attachments_v2(
        dry_run=dry_run, cycle="2026-07", out_root=str(tmp_path),
        log_path=str(tmp_path / "ingest.jsonl"), query="test",
    )
    staged = result["processed"][0]["attachments"]
    assert len(staged) == 1
    assert staged[0]["original_filename"] == filename
    assert staged[0]["office"] == "director"
    assert staged[0]["normalized_filename"] == f"director.{extension}"
    assert downloaded == ([] if dry_run else [filename])
    originals = tmp_path / "2026-07" / "originals"
    assert sorted(p.name for p in originals.rglob("*") if p.is_file()) == (
        [] if dry_run else [f"director.{extension}"]
    )


def test_image_only_submission_is_preserved():
    payload = {"parts": [part("Wing C.png", "image/png", "inline")]}
    assert EmailService._extract_attachment_metadata_v2(payload) == EmailService._extract_attachment_metadata(payload)


@pytest.mark.parametrize("disposition", ["attachment", ""])
def test_non_inline_image_is_preserved_alongside_document(disposition):
    payload = {"parts": [
        part("Finance.pdf", "application/pdf"),
        part("Wing C.png", "image/png", disposition),
    ]}
    assert len(EmailService._extract_attachment_metadata_v2(payload)) == 2
