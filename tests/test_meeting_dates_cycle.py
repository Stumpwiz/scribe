from scribe.meeting.meeting_dates import cycle_from_meeting_date


def test_cycle_from_meeting_date_iso_date():
    assert cycle_from_meeting_date("2026-03-05") == "2026-03"


def test_cycle_from_meeting_date_cycle():
    assert cycle_from_meeting_date("2026-03") == "2026-03"
