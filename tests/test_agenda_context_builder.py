import sys
from dataclasses import dataclass
from types import ModuleType

from scribe.meeting.agenda_context import AgendaContextBuilder


def test_agenda_context_builder_populates_template_keys(monkeypatch):
    def _mock_officers(cls):
        return [{"label": "President", "incumbent": "Test Person"}]

    def _mock_body_rows(cls, office_title, slots):
        return [{"label": slots[0]["label"], "incumbent": f"{office_title} Incumbent"}]

    monkeypatch.setattr(AgendaContextBuilder, "_build_officers", classmethod(_mock_officers))
    monkeypatch.setattr(AgendaContextBuilder, "_build_body_rows", classmethod(_mock_body_rows))

    context = AgendaContextBuilder.build({"meetingType": "regular", "meetingDate": "2026-03-05"})

    assert context["officers"] == [{"label": "President", "incumbent": "Test Person"}]
    assert context["regular_reports"][0]["incumbent"] == "Liaison Incumbent"
    assert context["open_reports"][0]["incumbent"] == "Chair Incumbent"
    assert context["association_reports"] == context["open_reports"]


@dataclass
class _StubReportRow:
    title: str
    name: str
    first: str
    last: str


class _Field:
    def __init__(self, name: str):
        self.name = name

    def __eq__(self, other):
        return ("eq", self.name, other)

    def asc(self):
        return ("asc", self.name)


class _StubReportRecord:
    title = _Field("title")
    body_precedence = _Field("body_precedence")
    office_precedence = _Field("office_precedence")


class _StubQuery:
    def __init__(self, rows):
        self._rows = rows
        self._title_filter = None

    def filter(self, *conditions):
        for condition in conditions:
            if isinstance(condition, tuple) and len(condition) == 3 and condition[:2] == ("eq", "title"):
                self._title_filter = condition[2]
        return self

    def order_by(self, *_args):
        return self

    def all(self):
        if self._title_filter is None:
            return list(self._rows)
        return [row for row in self._rows if row.title == self._title_filter]


class _StubSession:
    def __init__(self, rows):
        self._rows = rows
        self.closed = False

    def query(self, _model):
        return _StubQuery(self._rows)

    def close(self):
        self.closed = True


def test_agenda_context_builder_uses_report_record_rows_for_all_agenda_roles(monkeypatch):
    rows = [
        _StubReportRow("President", "Residents Council", "Pat", "Pres"),
        _StubReportRow("Vice President", "Residents Council", "Vic", "Pres"),
        _StubReportRow("Treasurer", "Residents Council", "Terry", "Treas"),
        _StubReportRow("Secretary", "Residents Council", "Sam", "Sec"),
        _StubReportRow("Administrative Assistant", "Residents Council", "Alex", "Admin"),
        _StubReportRow("Liaison", "Dining Committee", "Lia", "Dining"),
        _StubReportRow("Liaison", "St. Stephen's Green", "Lee", "Green"),
        _StubReportRow("Chair", "Dining Committee", "Chair", "Dining"),
        _StubReportRow("Chair", "Finance Committee", "Fran", "Finance"),
    ]
    session = _StubSession(rows)

    db_module = ModuleType("scribe.database")
    db_module.get_db_session = lambda: session
    monkeypatch.setitem(sys.modules, "scribe.database", db_module)

    clerk_models_module = ModuleType("scribe.clerk_models")
    clerk_models_module.ReportRecord = _StubReportRecord
    clerk_models_module.Term = object
    clerk_models_module.Office = object
    clerk_models_module.Body = object
    clerk_models_module.Person = object
    monkeypatch.setitem(sys.modules, "scribe.clerk_models", clerk_models_module)

    context = AgendaContextBuilder.build({"meetingType": "regular", "meetingDate": "2026-03-05"})

    assert {"label": "President", "incumbent": "Pat Pres"} in context["officers"]
    assert {"label": "Secretary", "incumbent": "Sam Sec"} in context["officers"]

    open_by_label = {row["label"]: row["incumbent"] for row in context["open_reports"]}
    assert open_by_label["Dining"] == "Chair Dining"
    assert open_by_label["Finance"] == "Fran Finance"

    regular_by_label = {row["label"]: row["incumbent"] for row in context["regular_reports"]}
    assert regular_by_label["Dining"] == "Lia Dining"
    assert regular_by_label["St.~Stephen's Green"] == "Lee Green"

    assert context["association_reports"] == context["open_reports"]
    assert session.closed is True
