# Simple test to ensure committed sample recipient lists use example.com
import json
from pathlib import Path

def test_sample_recipient_files_use_example_domain():
    root = Path(__file__).resolve().parents[1]
    samples = [
        root / "src" / "scribe" / "assets" / "recipients" / "council_members.json",
        root / "src" / "scribe" / "assets" / "recipients" / "committee_chairs.json",
    ]
    for path in samples:
        assert path.exists(), f"Missing sample file: {path}"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, list), f"{path} must be a list"
        for email in data:
            assert isinstance(email, str), f"Emails must be strings in {path}"
            assert email.endswith("@example.com"), f"Email must use example.com in {path}: {email}"
