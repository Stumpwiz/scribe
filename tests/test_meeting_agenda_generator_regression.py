import importlib
import sys
from types import ModuleType


if "crewai.tools" not in sys.modules:
    crewai_module = ModuleType("crewai")
    crewai_tools_module = ModuleType("crewai.tools")

    class _BaseTool:
        pass

    crewai_tools_module.BaseTool = _BaseTool
    crewai_module.tools = crewai_tools_module
    sys.modules["crewai"] = crewai_module
    sys.modules["crewai.tools"] = crewai_tools_module


generator_module = importlib.import_module("scribe.tools.meeting_agenda_generator_tool")


def test_meeting_agenda_generator_uses_expected_template_and_context_by_meeting_type(monkeypatch):
    cases = [
        ("2026-04-02", "regular", "agenda_regular.tex.j2"),
        ("2026-06-04", "open", "agenda_open.tex.j2"),
        ("2026-12-03", "association", "agenda_association.tex.j2"),
    ]

    captured_meeting_info = []

    original_builder = generator_module.AgendaContextBuilder.build

    class _StubLaTeXAgendaTool:
        def _run(self, meeting_info):
            captured_meeting_info.append(meeting_info.copy())
            return {"texPath": "/tmp/fake-agenda.tex"}

    class _StubCompilerTool:
        def _run(self, tex_file_path):
            assert tex_file_path == "/tmp/fake-agenda.tex"
            return {"success": True, "pdfPath": "/tmp/fake-agenda.pdf", "logPath": "/tmp/fake.log", "log": "ok"}

    monkeypatch.setattr(generator_module, "LaTeXAgendaTool", _StubLaTeXAgendaTool)
    monkeypatch.setattr(generator_module, "LaTeXCompilerTool", _StubCompilerTool)

    def _passthrough_builder(cls, meeting_info):
        enriched = original_builder(meeting_info)
        enriched["officers"] = [{"label": "President", "incumbent": "Pat Pres"}]
        return enriched

    monkeypatch.setattr(generator_module.AgendaContextBuilder, "build", classmethod(_passthrough_builder))

    tool = generator_module.MeetingAgendaGeneratorTool()
    for meeting_date, _expected_type, _expected_template in cases:
        result = tool._run(
            meeting_info={
                "meetingDate": meeting_date,
                "oldBusinessItems": [],
                "newBusinessItems": [],
            }
        )
        assert result["success"] is True
        assert result["pdfPath"] == "/tmp/fake-agenda.pdf"

    assert len(captured_meeting_info) == 3

    for (meeting_date, expected_type, expected_template), meeting_info in zip(cases, captured_meeting_info):
        assert meeting_info["meetingDate"] == meeting_date
        assert meeting_info["meetingType"] == expected_type
        assert meeting_info["agendaTemplate"].endswith(expected_template)
        assert meeting_info["oldBusinessItems"] == []
        assert meeting_info["newBusinessItems"] == []
        assert meeting_info["officers"] == [{"label": "President", "incumbent": "Pat Pres"}]


def test_meeting_agenda_generator_keeps_template_consistent_with_explicit_type(monkeypatch):
    captured_meeting_info = {}

    class _StubLaTeXAgendaTool:
        def _run(self, meeting_info):
            captured_meeting_info.update(meeting_info)
            return {"texPath": "/tmp/fake-agenda.tex"}

    class _StubCompilerTool:
        def _run(self, tex_file_path):
            assert tex_file_path == "/tmp/fake-agenda.tex"
            return {"success": True, "pdfPath": "/tmp/fake-agenda.pdf", "logPath": "/tmp/fake.log", "log": "ok"}

    monkeypatch.setattr(generator_module, "LaTeXAgendaTool", _StubLaTeXAgendaTool)
    monkeypatch.setattr(generator_module, "LaTeXCompilerTool", _StubCompilerTool)
    monkeypatch.setattr(
        generator_module.AgendaContextBuilder,
        "build",
        classmethod(lambda cls, meeting_info: dict(meeting_info, officers=[])),
    )

    tool = generator_module.MeetingAgendaGeneratorTool()
    result = tool._run(
        meeting_info={
            "meetingDate": "2026-06-04",
            "meetingType": "regular",
            "oldBusinessItems": [],
            "newBusinessItems": [],
        }
    )

    assert result["success"] is True
    assert captured_meeting_info["meetingType"] == "regular"
    assert captured_meeting_info["agendaTemplate"].endswith("agenda_regular.tex.j2")
