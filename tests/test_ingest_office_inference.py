import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.scribe.tools.email_service import EmailService


def _attachment(name: str, attachment_id: str = "att-1") -> dict:
    return {"filename": name, "mime_type": "application/pdf", "size": 123, "attachment_id": attachment_id}


def _stage_preview_for_attachments(
        monkeypatch,
        tmp_path: Path,
        attachments: list[dict],
        *,
        subject: str = "July reports",
        from_addr: str = "user2@example.com",
) -> dict:
    monkeypatch.setattr(EmailService, "_get_gmail_service", staticmethod(lambda: object()))
    monkeypatch.setattr(EmailService, "_get_label_id_if_exists", staticmethod(lambda service, label_name: None))
    monkeypatch.setattr(EmailService, "_list_message_ids", staticmethod(lambda service, query, max_results: ["msg-1"]))
    monkeypatch.setattr(
        EmailService,
        "_get_message_full_for_attachments",
        staticmethod(
            lambda service, message_id: {
                "message_id": message_id,
                "thread_id": "thread-1",
                "label_ids": [],
                "internal_date": datetime.now(timezone.utc).isoformat(),
                "from": from_addr,
                "subject": subject,
                "snippet": "Attached are the reports.",
                "attachments": attachments,
            }
        ),
    )

    return EmailService.stage_attachments_v2(
        max_results=10,
        dry_run=True,
        query="ignored",
        cycle="2026-07",
        out_root=str(tmp_path),
    )


def test_infer_wing_c_forwarded_from_geo() -> None:
    office, reason = EmailService._infer_office_stem_with_reason(
        from_addr="user2@example.com",
        subject="Wing C Report",
        snippet="The Liffey C wing report is attached as wingC.pdf",
        attachments=[_attachment("wingC.pdf")],
    )
    assert office == "wingC"
    assert reason in {"subject_alias", "body_and_attachment_alias", "attachment_alias", "body_alias"}


def test_infer_management_report_forwarded_subject() -> None:
    office, reason = EmailService._infer_office_stem_with_reason(
        from_addr="user2@example.com",
        subject="Fw: [EXTERNAL] Residents' Council Meeting - Management Report",
        snippet="",
        attachments=[_attachment("Residents Council Mtg - Management Report 2.5.2026.pdf")],
    )
    assert office == "director"
    assert reason in {"subject_alias", "attachment_alias", "body_and_attachment_alias"}


def test_infer_director_from_canonical_attachment_filename_variants() -> None:
    filenames = [
        "director.pdf",
        "Director Report.pdf",
        "Director's Report.pdf",
        "Executive Director Report.pdf",
        "Executive Director's Report.pdf",
    ]

    for filename in filenames:
        office = EmailService._infer_office_stem_from_attachment_filename(filename)
        assert office == "director", filename


def test_director_filename_takes_precedence_over_secretary_sender_fallback(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        EmailService,
        "_sender_office_stem_from_db",
        staticmethod(lambda from_addr: "secretary"),
    )
    result = _stage_preview_for_attachments(
        monkeypatch,
        tmp_path,
        [_attachment("director.pdf")],
        subject="August report",
        from_addr="secretary@example.com",
    )

    staged = result["processed"][0]["attachments"]
    assert staged[0]["office"] == "director"
    assert staged[0]["office_inference_reason"] == "attachment_filename_alias"


def test_nominating_committee_filename_precedes_sender_fallback(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        EmailService,
        "_sender_office_stem_from_db",
        staticmethod(lambda from_addr: "buildingMaintenance"),
    )
    result = _stage_preview_for_attachments(
        monkeypatch,
        tmp_path,
        [_attachment("Nominating Committee Report. 090326.docx")],
        subject="September report",
    )

    staged = result["processed"][0]["attachments"]
    assert staged[0]["office"] == "nominatingCommittee"
    assert staged[0]["office_inference_reason"] == "attachment_filename_alias"


def test_nominating_committee_subject_is_canonical() -> None:
    office, reason = EmailService._infer_office_stem_with_reason(
        from_addr="maintenance-chair@example.com",
        subject="Nominating Committee Report",
        snippet="Please see the attached report.",
        attachments=[_attachment("090326.docx")],
    )

    assert office == "nominatingCommittee"
    assert reason == "subject_alias"


def test_unrelated_director_filename_is_not_an_executive_director_report() -> None:
    office = EmailService._infer_office_stem_from_attachment_filename("Board of Directors Notes.pdf")

    assert office is None


def test_infer_library_committee_report() -> None:
    office, reason = EmailService._infer_office_stem_with_reason(
        from_addr="user2@example.com",
        subject="Library Committee Report",
        snippet="The library report is attached as Library Committee.pdf",
        attachments=[_attachment("Library Committee.pdf")],
    )
    assert office == "library"
    assert reason in {"subject_alias", "body_and_attachment_alias", "attachment_alias", "body_alias"}


def test_infer_environment_landscape_abbreviated_report_subjects() -> None:
    subjects = [
        "July E/L Report",
        "July E:L Report",
        "July Env/Land Report",
        "July Environment/Landscape Report",
        "July Environment & Landscape Report",
    ]

    for subject in subjects:
        office, reason = EmailService._infer_office_stem_with_reason(
            from_addr="user2@example.com",
            subject=subject,
            snippet="Please see the attached report.",
            attachments=[_attachment("E:L Liaison Report for May 20206.pdf")],
        )
        assert office == "environmentLandscape", subject
        assert reason == "subject_alias", subject


def test_stage_attachments_classifies_dining_and_d_wing_independently(monkeypatch, tmp_path: Path) -> None:
    result = _stage_preview_for_attachments(
        monkeypatch,
        tmp_path,
        [
            _attachment("Dining Committee Report - 7.21.26.docx", "att-1"),
            _attachment("D Wing Report - 8.6.26.docx", "att-2"),
        ],
        subject="Dining Committee reports",
    )

    staged = result["processed"][0]["attachments"]
    assert [item["office"] for item in staged] == ["dining", "wingD"]
    assert Path(staged[0]["saved_path"]).parent == tmp_path / "2026-07" / "originals" / "dining"
    assert Path(staged[1]["saved_path"]).parent == tmp_path / "2026-07" / "originals" / "wingD"


def test_dining_attachment_can_differ_from_wing_d_message_summary(monkeypatch, tmp_path: Path) -> None:
    result = _stage_preview_for_attachments(
        monkeypatch,
        tmp_path,
        [_attachment("Dining Committee Report 9:2:26.docx")],
        subject="Wing D Report",
    )

    message = result["processed"][0]
    assert message["office"] == "wingD"
    assert message["office_inference_reason"] == "subject_alias"
    assert message["attachments"][0]["office"] == "dining"
    assert message["attachments"][0]["office_inference_reason"] == "attachment_filename_alias"


def test_stage_attachments_classifies_two_reports_for_the_same_office(monkeypatch, tmp_path: Path) -> None:
    result = _stage_preview_for_attachments(
        monkeypatch,
        tmp_path,
        [
            _attachment("Dining Committee Report.docx", "att-1"),
            _attachment("July Dining Report.pdf", "att-2"),
        ],
        subject="Dining Committee reports",
    )

    staged = result["processed"][0]["attachments"]
    assert [item["office"] for item in staged] == ["dining", "dining"]
    assert all(item["office_inference_reason"] == "attachment_filename_alias" for item in staged)


def test_stage_attachment_uses_subject_when_filename_has_no_office_alias(monkeypatch, tmp_path: Path) -> None:
    result = _stage_preview_for_attachments(
        monkeypatch,
        tmp_path,
        [_attachment("August report.docx")],
        subject="Dining Committee Report",
    )

    staged = result["processed"][0]["attachments"]
    assert staged[0]["office"] == "dining"
    assert staged[0]["office_inference_reason"] == "message_subject_alias"


def test_stage_attachments_classifies_treasurer_and_employee_appreciation_independently(
        monkeypatch,
        tmp_path: Path,
) -> None:
    result = _stage_preview_for_attachments(
        monkeypatch,
        tmp_path,
        [
            _attachment("Treasurer Report.pdf", "att-1"),
            _attachment("Employee Appreciation Report.pdf", "att-2"),
        ],
    )

    staged = result["processed"][0]["attachments"]
    assert [item["office"] for item in staged] == ["treasurer", "employeeAppreciation"]
    assert Path(staged[0]["saved_path"]).parent == tmp_path / "2026-07" / "originals" / "treasurer"
    assert Path(staged[1]["saved_path"]).parent == tmp_path / "2026-07" / "originals" / "employeeAppreciation"


def test_infer_employee_appreciation_from_real_eac_attachment_filename() -> None:
    office = EmailService._infer_office_stem_from_attachment_filename(
        "Treasurer's Liaison Report EA C 7-9-26.docx"
    )
    assert office == "employeeAppreciation"


def test_infer_vice_president_from_consolidated_wings_attachment_filenames() -> None:
    filenames = [
        "August Consol. Wings Report.docx",
        "August Consolidated Wings Report.docx",
    ]

    for filename in filenames:
        office = EmailService._infer_office_stem_from_attachment_filename(filename)
        assert office == "vicePresident", filename


def test_individual_wing_report_is_not_inferred_as_vice_president() -> None:
    office = EmailService._infer_office_stem_from_attachment_filename("August Wing C Report.docx")

    assert office == "wingC"


def test_restage_when_message_is_newer(tmp_path: Path) -> None:
    office_dir = tmp_path / "wingC"
    office_dir.mkdir(parents=True, exist_ok=True)
    staged = office_dir / "wingC.pdf"
    staged.write_bytes(b"old")
    old_ts = datetime.now(timezone.utc) - timedelta(hours=2)
    os.utime(staged, (old_ts.timestamp(), old_ts.timestamp()))

    new_msg_ts = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    assert EmailService._should_restage_labeled_message(office_dir=office_dir, internal_date_iso=new_msg_ts)


def test_no_restage_when_not_newer(tmp_path: Path) -> None:
    office_dir = tmp_path / "library"
    office_dir.mkdir(parents=True, exist_ok=True)
    staged = office_dir / "library.pdf"
    staged.write_bytes(b"current")
    now = datetime.now(timezone.utc)
    os.utime(staged, (now.timestamp(), now.timestamp()))

    older_msg_ts = (now - timedelta(hours=3)).isoformat()
    assert not EmailService._should_restage_labeled_message(office_dir=office_dir, internal_date_iso=older_msg_ts)
