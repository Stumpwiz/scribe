from src.scribe.cli.build_minutes import OPEN_APPENDIX_ORDER, build_open_appendix_reports
from src.scribe.report_inventory import ordered_reports_for_cycle, reports_for_cycle


BASE = {"dining": "dining.pdf", "wingD": "wingD.pdf"}


def test_nominating_committee_is_expected_only_in_september() -> None:
    september = reports_for_cycle(BASE, "2026-09")
    august = reports_for_cycle(BASE, "2026-08")

    assert september["nominatingCommittee"] == "nominatingCommittee.pdf"
    assert "nominatingCommittee" not in august
    assert august == BASE


def test_database_derived_nominating_slot_is_removed_outside_september() -> None:
    dynamic = {**BASE, "nominatingCommittee": "nominatingCommittee.pdf"}

    assert reports_for_cycle(dynamic, "2026-08") == BASE


def test_september_appendix_order_inserts_only_nominating_committee() -> None:
    september = ordered_reports_for_cycle(OPEN_APPENDIX_ORDER, "2026-09")
    august = ordered_reports_for_cycle(OPEN_APPENDIX_ORDER, "2026-08")

    assert august == OPEN_APPENDIX_ORDER
    assert [office for office in september if office != "nominatingCommittee"] == OPEN_APPENDIX_ORDER
    index = september.index("nominatingCommittee")
    assert september[index - 1:index + 2] == [
        "specialEventsAndTrips",
        "nominatingCommittee",
        "director",
    ]


def test_open_manifest_includes_nominating_only_for_september(tmp_path) -> None:
    png_dir = tmp_path / "png"
    png_dir.mkdir()
    (png_dir / "nominatingCommittee.png").write_bytes(b"png")
    entry = {
        "status": "ok",
        "placeholder_used": False,
        "png_files": ["nominatingCommittee.png"],
    }

    september, _ = build_open_appendix_reports(
        {"cycle": "2026-09", "offices": {"nominatingCommittee": entry}},
        tmp_path,
    )
    august, _ = build_open_appendix_reports(
        {"cycle": "2026-08", "offices": {"nominatingCommittee": entry}},
        tmp_path,
    )

    assert [report["office"] for report in september] == ["nominatingCommittee"]
    assert september[0]["title"] == "Nominating Committee Report"
    assert august == []
