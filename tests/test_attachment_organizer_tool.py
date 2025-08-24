import json
import logging
from datetime import datetime

from scribe.tools.attachment_organizer_tool import AttachmentOrganizerTool


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')

    month = datetime.now().strftime("%Y-%m")

    sample = {
        "classified_reports": [
            {
                "message_id": "m1",
                "from": "Treasurer <treasurer@example.com>",
                "subject": "Treasurer report",
                "classification": "officer_report",
                "has_attachments": True,
                "attachment_filenames": ["treasurer_report.pdf"],
                "body_excerpt": "Budget details...",
            },
            {
                "message_id": "m2",
                "from": "VP <vp@example.com>",
                "subject": "Vice President update",
                "classification": "officer_report",
                "has_attachments": False,
                "attachment_filenames": [],
                "body_excerpt": "This is the report body text",
            },
        ],
        "month": month,
    }

    tool = AttachmentOrganizerTool()
    result = tool._run(**sample)

    print(json.dumps(result, indent=2))
