from __future__ import annotations

from pathlib import Path

import pytest

from src.scribe.archive import committee_minutes as minutes
from src.scribe.website.committee_modal import CommitteeModalError, find_anchor_patch


SE_HTML = """<!doctype html>
<!-- keep this comment -->
<p>Unrelated explanatory text.</p>
<div class="modal" id="seModal">
  <div class="modal-content">
    <a class="button" href="#">Jun</a>
    <a class="button" href="placeholder.pdf"><span>Jul</span></a>
    <a class="button" href="#">Aug</a>
  </div>
</div>
<div id="fiModal"><a href="#">Jul</a></div>
"""


def make_site(tmp_path: Path, html: str = SE_HTML) -> Path:
    site = tmp_path / "mrra"
    site.mkdir()
    (site / "index.html").write_text(html, encoding="utf-8")
    return site


def make_source(tmp_path: Path) -> Path:
    source = tmp_path / "minutes.docx"
    source.write_bytes(b"docx")
    return source


def fake_convert(source: Path, work_dir: Path) -> Path:
    pdf = work_dir / f"{source.stem}.pdf"
    pdf.write_bytes(b"%PDF-test")
    return pdf


def test_conventional_destination_path(tmp_path: Path) -> None:
    assert minutes.destination_path(tmp_path, "SE", "2026-07") == (
        tmp_path / "documents/Archive/SE/2026/2026-07_SE.pdf"
    )


def test_invalid_committee_code() -> None:
    with pytest.raises(minutes.ArchiveMinutesError, match="Unknown committee"):
        minutes.validate_committee("XX")


@pytest.mark.parametrize("value", ["2026-7", "26-07", "2026-13", "2026-00", "2026-07-01"])
def test_invalid_month(value: str) -> None:
    with pytest.raises(minutes.ArchiveMinutesError, match="exactly YYYY-MM"):
        minutes.validate_month(value)


def test_missing_source_file(tmp_path: Path) -> None:
    with pytest.raises(minutes.ArchiveMinutesError, match="Source DOCX does not exist"):
        minutes.build_plan("SE", "2026-07", tmp_path / "missing.docx", make_site(tmp_path))


def test_missing_site_root_or_index(tmp_path: Path) -> None:
    source = make_source(tmp_path)
    with pytest.raises(minutes.ArchiveMinutesError, match="root does not exist"):
        minutes.build_plan("SE", "2026-07", source, tmp_path / "missing")
    empty_site = tmp_path / "empty"
    empty_site.mkdir()
    with pytest.raises(minutes.ArchiveMinutesError, match="does not contain index.html"):
        minutes.build_plan("SE", "2026-07", source, empty_site)


def test_correct_modal_and_month_anchor_selection() -> None:
    patch = find_anchor_patch(SE_HTML, "seModal", "Jul", "documents/new.pdf")
    assert patch.modal_id == "seModal"
    assert patch.old_href == "placeholder.pdf"
    assert '<div id="fiModal"><a href="#">Jul</a></div>' in patch.apply(SE_HTML)


def test_absent_month_button_fails() -> None:
    with pytest.raises(CommitteeModalError, match="found 0"):
        find_anchor_patch(SE_HTML, "seModal", "May", "new.pdf")


def test_duplicate_month_button_fails() -> None:
    html = SE_HTML.replace("Aug</a>", "Jul</a>")
    with pytest.raises(CommitteeModalError, match="found 2"):
        find_anchor_patch(html, "seModal", "Jul", "new.pdf")


def test_placeholder_replacement_preserves_all_unrelated_html() -> None:
    patch = find_anchor_patch(SE_HTML, "seModal", "Jul", "documents/Archive/SE/2026/2026-07_SE.pdf")
    changed = patch.apply(SE_HTML)
    assert changed == SE_HTML.replace("placeholder.pdf", "documents/Archive/SE/2026/2026-07_SE.pdf")


def test_crlf_html_is_preserved(tmp_path: Path) -> None:
    html = SE_HTML.replace("\n", "\r\n")
    site = make_site(tmp_path, html)
    plan = minutes.build_plan("SE", "2026-07", make_source(tmp_path), site)
    changed = plan.patch.apply(plan.html)
    assert changed == html.replace("placeholder.pdf", plan.relative_href)
    assert changed.count("\r\n") == html.count("\r\n")


def test_refuses_existing_pdf_without_force(tmp_path: Path) -> None:
    site = make_site(tmp_path)
    source = make_source(tmp_path)
    destination = minutes.destination_path(site, "SE", "2026-07")
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"old")
    with pytest.raises(minutes.ArchiveMinutesError, match="--force"):
        minutes.build_plan("SE", "2026-07", source, site)


def test_dry_run_makes_no_persistent_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    site = make_site(tmp_path)
    source = make_source(tmp_path)
    original = (site / "index.html").read_bytes()
    monkeypatch.setattr(minutes, "convert_docx_to_pdf", fake_convert)
    plan = minutes.build_plan("SE", "2026-07", source, site)
    assert minutes.publish(plan, apply=False) is None
    assert not plan.destination.exists()
    assert (site / "index.html").read_bytes() == original


def test_applied_run_creates_pdf_and_updates_only_jul(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    site = make_site(tmp_path)
    source = make_source(tmp_path)
    monkeypatch.setattr(minutes, "convert_docx_to_pdf", fake_convert)
    plan = minutes.build_plan("SE", "2026-07", source, site)
    result = minutes.publish(plan, apply=True)
    assert result == (plan.destination, site / "index.html")
    assert plan.destination.read_bytes() == b"%PDF-test"
    changed = (site / "index.html").read_text(encoding="utf-8")
    assert changed == SE_HTML.replace("placeholder.pdf", plan.relative_href)
    assert '<a class="button" href="#">Jun</a>' in changed
    assert '<a class="button" href="#">Aug</a>' in changed


def test_conversion_failure_leaves_archive_and_html_unchanged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    site = make_site(tmp_path)
    source = make_source(tmp_path)
    original = (site / "index.html").read_bytes()

    def fail(source: Path, work_dir: Path) -> Path:
        raise minutes.ArchiveMinutesError("conversion failed")

    monkeypatch.setattr(minutes, "convert_docx_to_pdf", fail)
    plan = minutes.build_plan("SE", "2026-07", source, site)
    with pytest.raises(minutes.ArchiveMinutesError, match="conversion failed"):
        minutes.publish(plan, apply=True)
    assert not plan.destination.exists()
    assert (site / "index.html").read_bytes() == original


def test_index_changed_after_validation_is_not_overwritten(tmp_path: Path) -> None:
    site = make_site(tmp_path)
    source = make_source(tmp_path)
    plan = minutes.build_plan("SE", "2026-07", source, site)
    (site / "index.html").write_text(SE_HTML + "<!-- concurrent edit -->", encoding="utf-8")
    converted = tmp_path / "converted.pdf"
    converted.write_bytes(b"%PDF-test")
    with pytest.raises(minutes.ArchiveMinutesError, match="changed after validation"):
        minutes.apply_plan(plan, converted)
    assert not plan.destination.exists()
    assert (site / "index.html").read_text(encoding="utf-8").endswith("<!-- concurrent edit -->")
