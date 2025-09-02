from src.scribe.utils.privacy import mask_email, mask_emails


def test_mask_email_various_lengths():
    assert mask_email("a@example.com") == "a*@example.com"
    assert mask_email("ab@example.com") == "a*@example.com"
    assert mask_email("abc@example.com") == "a***c@example.com"
    assert mask_email("john.doe@example.com").endswith("@example.com")
    masked = mask_email("john@example.com")
    assert masked.startswith("j")
    assert masked.split("@")[0].endswith("n")


def test_mask_emails_list_and_empty():
    masked = mask_emails(["john@example.com", "jane@example.com"])
    assert "@" in masked and "," in masked
    assert mask_emails([]) == "no recipients"
    assert mask_emails(None) == "no recipients"
