import json
import logging
from pathlib import Path

from scribe.tools.email_classifier_tool import EmailClassifierTool


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')

    # Sample inputs mimicking EmailInboxMonitorTool output
    samples = [
        {
            "message_id": "abc123",
            "from": "Officer One <georgemartinwright@gmail.com>",
            "subject": "Treasurer report and attachments",
            "has_attachments": True,
            "attachment_filenames": ["treasurer_report.pdf"],
            "body_excerpt": "Budget details...",
        },
        {
            "message_id": "def456",
            "from": "external@example.com",
            "subject": "General question",
            "has_attachments": False,
            "attachment_filenames": [],
            "body_excerpt": "Hello, I have a short question.",
        },
    ]

    recipients_dir = Path(__file__).resolve().parents[1] / "scribe" / "assets" / "recipients"

    tool = EmailClassifierTool()
    result = tool._run(reports=samples, recipients_dir=str(recipients_dir))

    print(json.dumps(result, indent=2))
