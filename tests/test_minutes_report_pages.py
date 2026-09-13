import re
from pathlib import Path

from src.scribe.cli.build_minutes import (
    TEMPLATE_DIR,
    officer_report_inputs,
    render_template,
    report_pages_from_manifest,
)


def _pages(prefix: str, count: int) -> list[str]:
    return [f"{prefix}-{page}.png" for page in range(1, count + 1)]


def _report_block(tex: str, label: str) -> str:
    match = re.search(
        rf"\\reportbegin\{{[^}}]+\}}\{{{re.escape(label)}\}}(?P<body>.*?)\\reportend",
        tex,
        flags=re.DOTALL,
    )
    assert match is not None
    return match.group("body")


def _report_pages(tex: str, label: str) -> list[str]:
    return re.findall(r"\\reportpage\{([^}]+)\}", _report_block(tex, label))


def test_report_pages_from_manifest_allows_zero_pages():
    manifest = {"offices": {"empty": {"png_files": []}}}

    assert report_pages_from_manifest(manifest, "empty", ["stale-fallback.png"]) == []
    assert report_pages_from_manifest(manifest, "missing", ["fallback.png"]) == ["fallback.png"]


def test_regular_minutes_report_pages_are_manifest_driven(tmp_path: Path):
    cycle_root = tmp_path / "2026-07"
    cycle_root.mkdir()
    manifest = {
        "offices": {
            "president": {"png_files": ["president.png"]},
            "vicePresident": {"png_files": _pages("vicePresident", 7)},
            "buildingMaintenance": {"png_files": _pages("buildingMaintenance", 12)},
            "director": {"png_files": _pages("director", 9)},
            "wingF": {"png_files": ["wingF.png"]},
        }
    }

    tex_path = render_template(
        template_path=TEMPLATE_DIR / "minutes_regular.tex.j2",
        cycle_root=cycle_root,
        minutes_type="regular",
        logo_filename="logo.pdf",
        meeting_dates={
            "meetingDate": "July 9, 2026",
            "lastMeetingDate": "June 5, 2026",
            "nextMeetingDate": "August 6, 2026",
        },
        manifest=manifest,
        appendix_reports=[],
    )
    tex = tex_path.read_text(encoding="utf-8")

    assert _report_pages(tex, "president") == ["president.png"]
    assert _report_pages(tex, "vicePresident") == _pages("vicePresident", 7)
    assert _report_pages(tex, "buildingMaintenance") == _pages("buildingMaintenance", 12)
    assert _report_pages(tex, "director") == _pages("director", 9)
    assert _report_pages(tex, "wingF") == ["wingF.png"]
    assert "[director-8]" not in tex
    assert "[director-9]" not in tex


def test_regular_minutes_inputs_existing_officer_fragments_only(tmp_path: Path):
    cycle_root = tmp_path / "2026-07"
    report_dir = cycle_root / "officer_reports"
    report_dir.mkdir(parents=True)
    (report_dir / "president.tex").write_text("President narrative paragraph.\n", encoding="utf-8")
    (report_dir / "secretary.tex").write_text("Secretary narrative paragraph.\n", encoding="utf-8")
    manifest = {"offices": {}}

    tex_path = render_template(
        template_path=TEMPLATE_DIR / "minutes_regular.tex.j2",
        cycle_root=cycle_root,
        minutes_type="regular",
        logo_filename="logo.pdf",
        meeting_dates={
            "meetingDate": "July 9, 2026",
            "lastMeetingDate": "June 5, 2026",
            "nextMeetingDate": "August 6, 2026",
        },
        manifest=manifest,
        appendix_reports=[],
    )
    tex = tex_path.read_text(encoding="utf-8")

    assert officer_report_inputs(cycle_root) == {
        "president": "officer_reports/president.tex",
        "secretary": "officer_reports/secretary.tex",
    }
    assert re.search(
        r"\\subsection\*\{President\}\s+"
        r'\\input\{"officer_reports/president\.tex"\}\s+'
        r"President Luke Yackley's report appears in Appendix \\ref\{app:president\}",
        tex,
    )
    assert re.search(
        r"\\subsection\*\{Secretary\}\s+"
        r'\\input\{"officer_reports/secretary\.tex"\}\s+'
        r"Secretary George Wright's report appears in Appendix \\ref\{app:secretary\}",
        tex,
    )
    assert re.search(
        r"\\subsection\*\{Treasurer\}\s+"
        r"Treasurer Charles Blair's report appears in Appendix \\ref\{app:treasurer\}",
        tex,
    )
    assert "officer_reports/treasurer.tex" not in tex


def test_officer_report_headings_and_inputs_render_in_all_minutes_templates(tmp_path: Path):
    for template_name, minutes_type, secretary_text in [
        ("minutes_regular.tex.j2", "regular", "Secretary George Wright's report appears"),
        ("minutes_open.tex.j2", "open", "George Wright's report appears"),
        ("minutes_association.tex.j2", "association", "Secretary George Wright had no report."),
    ]:
        cycle_root = tmp_path / minutes_type / "2026-07"
        report_dir = cycle_root / "officer_reports"
        report_dir.mkdir(parents=True)
        (report_dir / "secretary.tex").write_text("Secretary narrative paragraph.\n", encoding="utf-8")

        tex_path = render_template(
            template_path=TEMPLATE_DIR / template_name,
            cycle_root=cycle_root,
            minutes_type=minutes_type,
            logo_filename="logo.pdf",
            meeting_dates={
                "meetingDate": "July 9, 2026",
                "lastMeetingDate": "June 5, 2026",
                "nextMeetingDate": "August 6, 2026",
            },
            manifest={"offices": {}},
            appendix_reports=[],
        )
        tex = tex_path.read_text(encoding="utf-8")

        for heading in ["President", "Vice President", "Treasurer", "Secretary", "Administrative Assistant"]:
            heading_tex = f"\\item[{heading}.]" if minutes_type == "open" else f"\\subsection*{{{heading}}}"
            assert heading_tex in tex
        secretary_heading = r"\\item\[Secretary\.\]" if minutes_type == "open" else r"\\subsection\*\{Secretary\}"
        assert re.search(
            secretary_heading + r'\s+\\input\{"officer_reports/secretary\.tex"\}.*?'
            + re.escape(secretary_text),
            tex,
            flags=re.DOTALL,
        )
