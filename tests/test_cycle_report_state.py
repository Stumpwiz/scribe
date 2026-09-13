import json

import pytest
from reportlab.pdfgen import canvas

from src.scribe import report_state
from src.scribe.cli import build_minutes, collect_pdfs, format_all, run_cycle


@pytest.fixture
def state_root(tmp_path, monkeypatch):
    root = tmp_path / "inputs"
    monkeypatch.setattr(report_state, "STATE_ROOT", root)
    return root


def write_state(root, cycle, offices):
    path = root / cycle / "report_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"offices": {o: {"appendix": "none"} for o in offices}}))
    return path


def write_pdf(path, pages=1):
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(path))
    for page in range(pages):
        pdf.drawString(72, 720, f"{path.stem}: report page {page + 1}")
        pdf.showPage()
    pdf.save()


def test_optional_state_is_cycle_scoped(state_root):
    assert report_state.load_omitted_offices("2030-04", {"finance", "library"}) == set()
    write_state(state_root, "2030-04", ["finance"])
    assert report_state.load_omitted_offices("2030-04", {"finance", "library"}) == {"finance"}
    assert report_state.load_omitted_offices("2030-05", {"finance", "library"}) == set()


@pytest.mark.parametrize("state", [
    [], {"offices": []}, {"offices": {"typo": {"appendix": "none"}}},
    {"offices": {"finance": {"appendix": "never"}}},
    {"offices": {"finance": {"appendix": "none", "delivered_at_meeting": True}}},
    {"offices": {}, "extra": True},
])
def test_invalid_state_fails_before_collection_or_formatting_writes(state_root, tmp_path, monkeypatch, state):
    path = write_state(state_root, "2030-04", [])
    path.write_text(json.dumps(state))
    mapping = tmp_path / "map.json"
    mapping.write_text(json.dumps({"finance": "finance.pdf"}))
    output = tmp_path / "outputs"
    inputs = tmp_path / "pdf"
    inputs.mkdir()
    monkeypatch.setattr(collect_pdfs, "load_committee_chair_mapping", lambda: {})
    monkeypatch.setattr(format_all, "load_committee_chair_mapping", lambda: {})
    monkeypatch.setattr(format_all, "OUTPUT_ROOT", output)
    assert collect_pdfs.main([
        "--cycle", "2030-04", "--map", str(mapping), "--output-root", str(output),
    ]) == 2
    with pytest.raises(SystemExit) as exc:
        format_all.main(["--cycle", "2030-04", "--map", str(mapping), "--input-dir", str(inputs)])
    assert exc.value.code == 2
    assert not output.exists()


@pytest.mark.parametrize("cycle", ["2030-04", "2030-09"])
@pytest.mark.parametrize("retained", [False, True])
def test_cycle_regeneration_preserves_omissions_placeholders_and_written_reports(
        state_root, tmp_path, monkeypatch, cycle, retained):
    omitted = {"dining", "environmentLandscape", "finance"}
    write_state(state_root, cycle, omitted)
    cycles = tmp_path / "cycles"
    root = cycles / cycle
    (root / "pdf").mkdir(parents=True)
    (root / "png").mkdir()
    mapping = tmp_path / "map.json"
    mapping.write_text(json.dumps({o: f"{o}.pdf" for o in (
        "president", "dining", "environmentLandscape", "library", "wingA", "wingB",
    )}))
    # The policy also applies to an office added by the database, after map resolution.
    for module in (collect_pdfs, format_all):
        monkeypatch.setattr(module, "load_committee_chair_mapping", lambda: {"finance": "finance.pdf"})
    monkeypatch.setattr(format_all, "OUTPUT_ROOT", cycles)
    write_pdf(root / "originals/president/president.pdf", pages=2)
    write_pdf(root / "originals/wingA/wingA.pdf")
    if cycle.endswith("-09"):
        write_pdf(root / "originals/nominatingCommittee/nominatingCommittee.pdf")
    preserved = {}
    if retained:
        for office in omitted:
            for rel in (f"originals/{office}/{office}.docx", f"originals/{office}/{office}.pdf",
                        f"pdf/{office}.pdf", f"png/{office}.png"):
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"Retained asset: must neither be processed nor deleted")
                preserved[path] = path.read_bytes()

    def no_email(*args, **kwargs):
        pytest.fail("Regeneration must not call ingestion")

    monkeypatch.setattr(run_cycle.ingest, "main", no_email)
    argv = ["--cycle", cycle, "--map", str(mapping), "--out-root", str(cycles),
            "--apply", "--skip-stage", "--keep-going", "--dpi", "36"]
    previous = None
    for _ in range(2):
        # Exercise the actual orchestrator. Ordinary missing sources retain the
        # collector's existing exit code; --keep-going lets formatting follow.
        assert run_cycle.main(argv) == 1
        assert collect_pdfs.LAST_RESULT["omitted_offices"] == sorted(omitted)
        assert set(collect_pdfs.LAST_RESULT["missing_offices"]) == {"library:library.pdf", "wingB:wingB.pdf"}
        assert format_all.LAST_RESULT["exit_code"] == 0
        assert format_all.LAST_RESULT["placeholder_count"] == 2
        manifest = json.loads((root / "manifest.json").read_text())
        for office in omitted:
            assert manifest["offices"][office] == {
                "source_pdf": None, "placeholder_used": False, "pages": 0,
                "png_files": [], "status": "omitted",
            }
            if not retained:
                assert not (root / "png" / f"{office}.png").exists()
                assert not (root / "pdf" / f"{office}.pdf").exists()
        assert manifest["offices"]["library"]["placeholder_used"] is True
        assert manifest["offices"]["president"]["placeholder_used"] is False
        assert manifest["offices"]["president"]["pages"] == 2
        assert manifest["offices"]["wingB"]["placeholder_used"] is True
        reports, _ = build_minutes.build_open_appendix_reports(manifest, root)
        expected = ["president", "library"]
        if cycle.endswith("-09"):
            expected.append("nominatingCommittee")
        expected.append("wingA")
        assert [r["office"] for r in reports] == expected
        tex = build_minutes.render_template(
            build_minutes.TEMPLATE_DIR / "minutes_open.tex.j2", root, "open", "logo.pdf", {}, manifest, reports,
        ).read_text()
        assert "Chair Gerry Buckley's report was delivered by Jim Devine." in tex
        assert "Chair Ed Lehwald delivered his report and solicited new committee members." in tex
        for office in ("dining", "environmentLandscape"):
            assert f"app:{office}" not in tex
        appendices = tex.split(r"\appendix", 1)[1]
        for office in omitted | {"wingB"}:
            assert office not in appendices
        assert r"\reportpage{library.png}" in appendices
        for path, data in preserved.items():
            assert path.read_bytes() == data
        effective = {k: v for k, v in manifest.items() if k != "created_at"}
        if previous is not None:
            assert (effective, tex) == previous
        previous = (effective, tex)
        (root / "manifest.json").unlink()  # Recreate from source, not the previous manifest.


@pytest.mark.parametrize("flags", [[], ["--overwrite"], ["--fill-missing-with-placeholder"], ["--dry-run"]])
def test_collector_omission_precedes_conversion_and_placeholder_filling(state_root, tmp_path, monkeypatch, flags):
    write_state(state_root, "2030-04", ["library"])
    mapping = tmp_path / "map.json"
    mapping.write_text(json.dumps({"library": "library.pdf"}))
    root = tmp_path / "cycles/2030-04"
    source = root / "originals/library/library.docx"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"Do not convert")
    (root / "placeholder.pdf").write_bytes(b"Do not copy")
    monkeypatch.setattr(collect_pdfs, "load_committee_chair_mapping", lambda: {})
    monkeypatch.setattr(collect_pdfs, "convert_docx_to_pdf", lambda *a: pytest.fail("Unexpected conversion"))
    assert collect_pdfs.main([
        "--cycle", "2030-04", "--map", str(mapping), "--output-root", str(root.parent), *flags,
    ]) == 0
    assert collect_pdfs.LAST_RESULT["missing_offices"] == []
    assert collect_pdfs.LAST_RESULT["placeholder_filled_offices"] == []
    assert collect_pdfs.LAST_RESULT["omitted_offices"] == ["library"]
    assert not (root / "pdf/library.pdf").exists()
    assert source.read_bytes() == b"Do not convert"
