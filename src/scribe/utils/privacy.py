from typing import List, Optional


def mask_email(addr: str) -> str:
    """
    Mask the local part of an email address for safe logging.
    Examples:
      john@example.com -> j***n@example.com
      ab@example.com   -> a*@example.com
    """
    try:
        user, domain = addr.split("@", 1)
        if len(user) <= 2:
            masked_user = user[0] + "*"
        else:
            masked_user = user[0] + "***" + user[-1]
        return f"{masked_user}@{domain}"
    except Exception:
        return "***"


def mask_emails(emails: Optional[List[str]]) -> str:
    """
    Mask a list of emails for logging.
    """
    if not emails:
        return "no recipients"
    return ", ".join(mask_email(e) for e in emails)
