import pytest

from src.scribe.cli.build_minutes import (
    OPEN_APPENDIX_ORDER, TEMPLATE_DIR, build_open_appendix_reports, is_wing_office, render_template,
)
from src.scribe.report_inventory import ordered_reports_for_cycle


def test_open_appendices_preserve_valid_assets_and_order_for_real_reports(tmp_path):
    png_dir = tmp_path / "png"
    png_dir.mkdir()
    order = ordered_reports_for_cycle(OPEN_APPENDIX_ORDER, "2026-09")
    offices = {}
    for office in reversed(order):
        names = [f"{office}-1.png", f"{office}-2.png"]
        for name in names:
            (png_dir / name).write_bytes(b"png")
        offices[office] = {"status": "ok", "placeholder_used": False, "png_files": names}
    manifest = {"cycle": "2026-09", "offices": offices}
    reports, skipped = build_open_appendix_reports(manifest, tmp_path)
    assert skipped == []
    assert [r["office"] for r in reports] == order
    for report in reports:
        assert report["placeholder_used"] is False
        assert report["png_files"] == offices[report["office"]]["png_files"]
    tex = render_template(
        TEMPLATE_DIR / "minutes_open.tex.j2", tmp_path, "open", "logo.pdf", {}, manifest, reports,
    ).read_text()
    positions = []
    for report in reports:
        positions.append(tex.index("\\reportbegin{" + report["title"] + "}{" + report["label"] + "}"))
        for name in report["png_files"]:
            assert "\\reportpage{" + name + "}" in tex
    assert positions == sorted(positions)


def test_open_appendices_omit_missing_wing_placeholders_while_retaining_non_wing_placeholders(tmp_path):
    png_dir = tmp_path / "png"
    png_dir.mkdir()
    order = ordered_reports_for_cycle(OPEN_APPENDIX_ORDER, "2026-09")
    offices = {}
    for office in order:
        names = [f"{office}.png"]
        for name in names:
            (png_dir / name).write_bytes(b"png")
        # Let's say all are placeholders except wingA and wingD
        is_placeholder = office not in {"wingA", "wingD"}
        offices[office] = {"status": "ok", "placeholder_used": is_placeholder, "png_files": names}
    manifest = {"cycle": "2026-09", "offices": offices}
    reports, skipped = build_open_appendix_reports(manifest, tmp_path)

    # Missing wing reports with placeholder -> omitted from open appendix & recorded in skipped
    for wing in ["wingB", "wingC", "wingE", "wingF", "wingG"]:
        assert f"{wing}: skipped (placeholder wing report omitted from open minutes)" in skipped

    report_offices = [r["office"] for r in reports]

    # Received wing reports -> included
    assert "wingA" in report_offices
    assert "wingD" in report_offices
    for wing in ["wingB", "wingC", "wingE", "wingF", "wingG"]:
        assert wing not in report_offices

    # Missing non-wing reports represented by placeholder -> placeholder still included
    assert "environmentLandscape" in report_offices
    assert "dining" in report_offices
    env_rep = next(r for r in reports if r["office"] == "environmentLandscape")
    assert env_rep["placeholder_used"] is True
    dining_rep = next(r for r in reports if r["office"] == "dining")
    assert dining_rep["placeholder_used"] is True

    # Canonical appendix ordering of included reports remains unchanged
    expected_order = [o for o in order if not (is_wing_office(o) and offices[o]["placeholder_used"])]
    assert report_offices == expected_order

    tex = render_template(
        TEMPLATE_DIR / "minutes_open.tex.j2", tmp_path, "open", "logo.pdf", {}, manifest, reports,
    ).read_text()
    for report in reports:
        assert "\\reportbegin{" + report["title"] + "}{" + report["label"] + "}" in tex
    for wing in ["wingB", "wingC", "wingE", "wingF", "wingG"]:
        assert f"\\reportpage{{{wing}.png}}" not in tex


@pytest.mark.parametrize("placeholder", [False, True])
def test_invalid_assets_remain_excluded(tmp_path, placeholder):
    reports, skipped = build_open_appendix_reports({"offices": {
        "president": {"status": "ok", "placeholder_used": placeholder, "png_files": ["missing.png"]},
        "vicePresident": {"status": "failed", "placeholder_used": placeholder, "png_files": []},
    }}, tmp_path)
    assert reports == []
    assert "president: skipped (no assets present)" in skipped
    assert "vicePresident: skipped (status=failed)" in skipped
