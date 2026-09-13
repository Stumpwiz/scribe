from src.scribe.cli.run_cycle import _summarize_originals


def test_summarize_originals_counts_each_attachment_office() -> None:
    stage_result = {
        "processed": [{
            "office": "dining",
            "attachments": [
                {"original_filename": "Dining Committee Report.docx", "office": "dining"},
                {"original_filename": "D Wing Report.docx", "office": "wingD"},
            ],
        }],
    }

    assert _summarize_originals(stage_result) == {"dining": 1, "wingD": 1}
