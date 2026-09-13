from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined


def test_meeting_dates_template_renders_without_macro_padding_spaces():
    template_dir = Path(__file__).resolve().parents[1] / "src" / "scribe" / "assets" / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
        undefined=StrictUndefined,
    )
    template = env.get_template("meeting_dates.tex.j2")
    rendered = template.render(
        last_meeting_date="February 5, 2026",
        meeting_date="March 5, 2026",
        next_meeting_date="April 2, 2026",
    )

    assert r"\newcommand{\lastMeetingDate}{February 5, 2026}" in rendered
    assert r"\newcommand{\meetingDate}{March 5, 2026}" in rendered
    assert r"\newcommand{\nextMeetingDate}{April 2, 2026}" in rendered
