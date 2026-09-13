from pathlib import Path

from reportlab.pdfgen import canvas

from src.scribe.cli.format_all import process_office
from src.scribe.tools.formatter_service import FormatterService


def _write_pdf(path: Path, pages: int) -> None:
    c = canvas.Canvas(str(path))
    for page in range(1, pages + 1):
        c.drawString(72, 720, f"Report page {page}")
        c.showPage()
    c.save()


def _write_pdf_with_trailing_blank(path: Path) -> None:
    c = canvas.Canvas(str(path))
    c.drawString(72, 720, "Report page 1")
    c.showPage()
    c.showPage()
    c.save()


def _write_pdf_with_trailing_artifact(path: Path) -> None:
    c = canvas.Canvas(str(path))
    c.drawString(72, 720, "Report page 1")
    c.showPage()
    c.setFillColorRGB(0, 0, 0)
    c.rect(72, 720, 0.5, 0.5, stroke=0, fill=1)
    c.showPage()
    c.save()


def _write_pdf_with_sparse_trailing_text(path: Path) -> None:
    c = canvas.Canvas(str(path))
    c.drawString(72, 720, "Report page 1")
    c.showPage()
    c.drawString(72, 720, "Approved.")
    c.showPage()
    c.save()


def _process_pdf(tmp_path: Path, office: str, pdf_name: str):
    input_dir = tmp_path / "pdf"
    png_dir = tmp_path / "png"
    return process_office(
        office=office,
        source_pdf_name=pdf_name,
        input_dir=input_dir,
        png_dir=png_dir,
        placeholder_available=False,
        cycle_placeholder=tmp_path / "placeholder.pdf",
        dpi=36,
        trim_whitespace=False,
        svc=FormatterService(),
    )


def test_one_page_report_manifest_records_exact_written_filename(tmp_path: Path):
    input_dir = tmp_path / "pdf"
    input_dir.mkdir()
    _write_pdf(input_dir / "wingE.pdf", pages=1)

    entry, success, _, _ = _process_pdf(tmp_path, "wingE", "wingE.pdf")

    assert success is True
    assert entry["status"] == "ok"
    assert entry["pages"] == 1
    assert entry["png_files"] == ["wingE.png"]
    assert (tmp_path / "png" / "wingE.png").is_file()
    assert all((tmp_path / "png" / name).is_file() for name in entry["png_files"])


def test_multi_page_report_manifest_records_exact_written_filenames(tmp_path: Path):
    input_dir = tmp_path / "pdf"
    input_dir.mkdir()
    _write_pdf(input_dir / "vicePresident.pdf", pages=2)

    entry, success, _, _ = _process_pdf(tmp_path, "vicePresident", "vicePresident.pdf")

    assert success is True
    assert entry["status"] == "ok"
    assert entry["pages"] == 2
    assert entry["png_files"] == ["vicePresident-1.png", "vicePresident-2.png"]
    assert all((tmp_path / "png" / name).is_file() for name in entry["png_files"])


def test_single_emitted_page_uses_single_page_filename_after_blank_suppression(tmp_path: Path):
    input_dir = tmp_path / "pdf"
    input_dir.mkdir()
    _write_pdf_with_trailing_blank(input_dir / "wingE.pdf")

    entry, success, _, _ = _process_pdf(tmp_path, "wingE", "wingE.pdf")

    assert success is True
    assert entry["status"] == "ok"
    assert entry["pages"] == 1
    assert entry["png_files"] == ["wingE.png"]
    assert (tmp_path / "png" / "wingE.png").is_file()
    assert not (tmp_path / "png" / "wingE-1.png").exists()
    assert all((tmp_path / "png" / name).is_file() for name in entry["png_files"])


def test_tiny_trailing_artifact_is_suppressed_as_blank(tmp_path: Path):
    input_dir = tmp_path / "pdf"
    input_dir.mkdir()
    _write_pdf_with_trailing_artifact(input_dir / "environmentLandscape.pdf")

    entry, success, _, _ = _process_pdf(
        tmp_path,
        "environmentLandscape",
        "environmentLandscape.pdf",
    )

    assert success is True
    assert entry["pages"] == 1
    assert entry["png_files"] == ["environmentLandscape.png"]


def test_sparse_trailing_text_is_not_suppressed(tmp_path: Path):
    input_dir = tmp_path / "pdf"
    input_dir.mkdir()
    _write_pdf_with_sparse_trailing_text(input_dir / "environmentLandscape.pdf")

    entry, success, _, _ = _process_pdf(
        tmp_path,
        "environmentLandscape",
        "environmentLandscape.pdf",
    )

    assert success is True
    assert entry["pages"] == 2
    assert entry["png_files"] == [
        "environmentLandscape-1.png",
        "environmentLandscape-2.png",
    ]


def test_manifest_entry_fails_when_formatter_reports_missing_png(tmp_path: Path):
    class MismatchedFormatter:
        def pdf_to_pngs_v1(self, **kwargs):
            png_dir = Path(kwargs["output_dir"])
            png_dir.mkdir()
            (png_dir / "wingE.png").write_text("actual file", encoding="utf-8")
            return {
                "success": True,
                "pages": 1,
                "images": [str(png_dir / "wingE-1.png")],
            }

    input_dir = tmp_path / "pdf"
    input_dir.mkdir()
    _write_pdf(input_dir / "wingE.pdf", pages=1)

    entry, success, _, _ = process_office(
        office="wingE",
        source_pdf_name="wingE.pdf",
        input_dir=input_dir,
        png_dir=tmp_path / "png",
        placeholder_available=False,
        cycle_placeholder=tmp_path / "placeholder.pdf",
        dpi=36,
        trim_whitespace=False,
        svc=MismatchedFormatter(),
    )

    assert success is False
    assert entry["status"] == "failed"
    assert entry["png_files"] == []
    assert "missing PNG output" in entry["error"]
