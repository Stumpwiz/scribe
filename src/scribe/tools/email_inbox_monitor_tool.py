"""
EmailInboxMonitorTool: Monitor Gmail inbox for Residents Council report candidates.

This tool scans unread messages in the authenticated Gmail inbox, marks them as
read to avoid duplicate processing, extracts basic metadata, detects attachments,
gets a body excerpt, heuristically flags report candidates, and returns a
structured JSON-like dictionary suitable for follow-up tools.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import base64
import logging
import re
from html import unescape

from crewai.tools import BaseTool
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Reuse credentials setup used elsewhere in the project
from src.scribe.google_auth.google_auth_helper import get_google_credentials

logger = logging.getLogger(__name__)


class EmailInboxMonitorTool(BaseTool):
    """
    Scan unread Gmail messages and summarize those that look like reports.

    - Extends: BaseTool
    - Tool name: "email_inbox_monitor"
    - Invocation name: EmailInboxMonitorTool
    - Inputs: none required; optional kwargs supported (max_results, query)
    """

    name: str = "email_inbox_monitor"
    description: str = (
        "Monitor Gmail inbox for unread messages, mark them read, and summarize "
        "potential Residents Council report emails (attachments or substantive body)."
    )

    # No args_schema required; tool reads from Gmail inbox

    def _run(self, max_results: int = 25, query: Optional[str] = None, **_: Any) -> Dict[str, Any]:
        """
        Execute the inbox monitor.

        Args:
            max_results: Upper bound of messages to fetch (default 25).
            query: Optional Gmail search query (appended to default unread-inbox filter).

        Returns:
            Dict with keys: status, messages_checked, report_candidates, reports
        """
        messages_checked = 0
        candidates: List[Dict[str, Any]] = []

        try:
            creds = get_google_credentials()
            if not creds:
                logger.error("EmailInboxMonitorTool: No Google credentials available")
                return {
                    "status": "error",
                    "messages_checked": 0,
                    "report_candidates": 0,
                    "reports": [],
                    "error": "Missing Google credentials"
                }

            service = build("gmail", "v1", credentials=creds)

            # Build query to get UNREAD messages in INBOX
            base_q = "label:inbox is:unread"
            if query:
                q = f"{base_q} {query}"
            else:
                q = base_q

            logger.info(f"EmailInboxMonitorTool: listing messages with q='{q}', max_results={max_results}")
            list_resp = service.users().messages().list(
                userId="me",
                q=q,
                maxResults=max_results
            ).execute()

            msg_refs = list_resp.get("messages", []) or []
            total_found = list_resp.get("resultSizeEstimate", len(msg_refs))
            logger.info(f"EmailInboxMonitorTool: found ~{total_found} unread message(s), fetching {len(msg_refs)}")

            for ref in msg_refs:
                msg_id = ref.get("id")
                if not msg_id:
                    continue

                # Mark as read first to avoid duplicate processing on subsequent runs
                try:
                    service.users().messages().modify(
                        userId="me",
                        id=msg_id,
                        body={"removeLabelIds": ["UNREAD"]}
                    ).execute()
                except HttpError as e:
                    logger.warning(f"EmailInboxMonitorTool: failed to mark message {msg_id} as read: {e}")
                except Exception as e:
                    logger.warning(f"EmailInboxMonitorTool: unexpected error clearing UNREAD for {msg_id}: {e}")

                # Retrieve full message
                try:
                    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
                except HttpError as e:
                    logger.error(f"EmailInboxMonitorTool: failed to get message {msg_id}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"EmailInboxMonitorTool: unexpected error getting message {msg_id}: {e}")
                    continue

                messages_checked += 1

                headers = _headers_to_dict(msg.get("payload", {}).get("headers", []))
                from_addr = headers.get("from", "")
                subject = headers.get("subject", "")
                date = headers.get("date", "")

                # Extract attachments metadata and body text
                payload = msg.get("payload", {})
                attachment_filenames: List[str] = []
                body_text = _extract_body_text(payload)
                if body_text:
                    body_text = body_text.strip()
                else:
                    body_text = ""

                # Detect attachments by traversing parts
                _collect_attachment_filenames(payload, attachment_filenames)
                has_attachments = len(attachment_filenames) > 0

                # Determine whether the message is a report candidate
                non_ws_len = len(re.sub(r"\s+", "", body_text))
                looks_like_report = non_ws_len >= 200
                report_candidate = has_attachments or looks_like_report

                # Truncate body excerpt to first 500 characters
                excerpt = body_text[:500]

                # Log structured info
                logger.info(
                    "EmailInboxMonitorTool candidate check | from=%s | subject=%s | attachments=%s | bodyLooksReport=%s",
                    from_addr,
                    subject,
                    has_attachments,
                    looks_like_report,
                )

                if report_candidate:
                    candidates.append({
                        "message_id": msg_id,
                        "from": from_addr,
                        "subject": subject,
                        "has_attachments": has_attachments,
                        "attachment_filenames": attachment_filenames,
                        "body_excerpt": excerpt,
                        "report_candidate": True,
                        "date": date,
                    })

            return {
                "status": "complete",
                "messages_checked": messages_checked,
                "report_candidates": len(candidates),
                "reports": candidates,
            }

        except HttpError as e:
            logger.exception("EmailInboxMonitorTool: Gmail API error")
            return {
                "status": "error",
                "messages_checked": messages_checked,
                "report_candidates": len(candidates),
                "reports": candidates,
                "error": str(e),
            }
        except Exception as e:
            logger.exception("EmailInboxMonitorTool: unexpected error")
            return {
                "status": "error",
                "messages_checked": messages_checked,
                "report_candidates": len(candidates),
                "reports": candidates,
                "error": str(e),
            }


def _headers_to_dict(headers: List[Dict[str, str]]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for h in headers or []:
        name = (h.get("name") or "").lower()
        value = h.get("value") or ""
        out[name] = value
    return out


def _decode_data(data_b64: Optional[str]) -> str:
    if not data_b64:
        return ""
    try:
        # Gmail may use URL-safe base64
        decoded = base64.urlsafe_b64decode(data_b64.encode("utf-8")).decode("utf-8", errors="replace")
        return decoded
    except Exception:
        try:
            decoded = base64.b64decode(data_b64).decode("utf-8", errors="replace")
            return decoded
        except Exception:
            return ""


def _strip_html(html: str) -> str:
    if not html:
        return ""
    # Remove scripts/styles
    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.IGNORECASE)
    # Strip tags
    text = re.sub(r"<[^>]+>", " ", html)
    text = unescape(text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_body_text(payload: Dict[str, Any]) -> str:
    """
    Prefer text/plain; fallback to stripped text/html; support both single and multipart.
    """
    if not payload:
        return ""

    mime_type = payload.get("mimeType", "")
    body = payload.get("body", {})

    # Single part
    if mime_type.startswith("text/"):
        data = body.get("data")
        text = _decode_data(data)
        if mime_type == "text/html":
            return _strip_html(text)
        return text

    # Multipart: scan parts
    parts = payload.get("parts") or []
    plain_text: Optional[str] = None
    html_text: Optional[str] = None
    for part in parts:
        p_type = part.get("mimeType", "")
        p_body = part.get("body", {})
        if p_type == "text/plain" and not plain_text:
            plain_text = _decode_data(p_body.get("data"))
        elif p_type == "text/html" and not html_text:
            html_text = _strip_html(_decode_data(p_body.get("data")))
        elif p_type.startswith("multipart/"):
            nested = _extract_body_text(part)
            if nested and not plain_text:
                plain_text = nested
    if plain_text:
        return plain_text
    if html_text:
        return html_text
    return ""


def _collect_attachment_filenames(payload: Dict[str, Any], acc: List[str]) -> None:
    if not payload:
        return
    mime = payload.get("mimeType", "")
    filename = payload.get("filename") or ""
    body = payload.get("body", {})

    # If this part represents an attachment (filename present and typically an attachmentId)
    if filename and (body.get("attachmentId") or not mime.startswith("text/")):
        acc.append(filename)

    # Recurse into parts
    for part in payload.get("parts", []) or []:
        _collect_attachment_filenames(part, acc)
