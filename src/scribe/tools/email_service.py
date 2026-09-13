"""
Email service tool for the Scribe project.

This module provides the EmailService class for sending and receiving emails
using the Gmail API.

IngestorAgent v1 support:
- Manual, non-destructive ingestion of unread INBOX messages (or a caller-provided query)
- Classify: attendance / agenda-typo / agenda-omission / agenda-newbiz / unknown
- Apply label: Scribe/Incoming (add only; do not remove labels)
- Append JSONL log record per message (append-only)
- Idempotent: skip messages already labeled Scribe/Incoming to avoid duplicate logs
- No replies, no mark-read, no attachment downloads
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field

import os
import json
import logging
import mimetypes
import base64
import traceback
import uuid
import re
from datetime import datetime, timezone, date
from pathlib import Path

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

from crewai.tools import BaseTool
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.scribe.google_auth.google_auth_helper import get_google_credentials
from src.scribe.utils.privacy import mask_emails

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_INGEST_QUERY = "is:unread in:inbox -category:promotions -category:social -category:updates"


# -----------------------------
# Schema
# -----------------------------

class EmailServiceSchema(BaseModel):
    action: str = Field(
        default="send",
        description="Action to perform. Supported: send, search, check, ingest_unread_inbox_v1, stage_attachments_v2",
    )

    # send
    to: Optional[list[str]] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    attachments: Optional[list[str]] = Field(default_factory=list)

    # search/check/ingest
    query: Optional[str] = None
    max_results: Optional[int] = Field(default=25, ge=1, le=200)

    # ingest specifics
    label_name: Optional[str] = Field(default="Scribe/Incoming")
    log_path: Optional[str] = Field(
        default=None,
        description="Path to JSONL log file. Default: src/scribe/output/ingestion/ingest_log.jsonl",
    )

    # misc
    dry_run: Optional[bool] = Field(
        default=False,
        description="If true, do not apply labels or write log files (for testing).",
    )

    # ingest v2 (attachments staging)
    cycle: Optional[str] = Field(
        default=None,
        description="Cycle identifier like '2026-02' used to place staged attachments under the cycle scaffold.",
    )
    out_root: Optional[str] = Field(
        default=None,
        description="Root output directory for cycles. Default: src/scribe/output/cycles",
    )

    force: Optional[bool] = Field(
        default=False,
        description="If true (v2), re-stage attachments even if the message is already labeled.",
    )

    skip_unknown: Optional[bool] = Field(
        default=False,
        description="If true (v2), do not stage attachments for messages inferred as office='unknown'.",
    )


# -----------------------------
# Tool
# -----------------------------

class EmailService(BaseTool):
    """
    Tool for sending and receiving emails via Gmail API.

    ReminderAgent uses send operations.
    IngestorAgent v1 uses ingest_unread_inbox_v1 (label/log only).
    """

    # NOTE: loader.py TOOL_REGISTRY maps by key "email_service". The `name` here is cosmetic.
    name: str = "Email Service"
    description: str = "Tool for sending and receiving emails via Gmail API"
    args_schema = EmailServiceSchema

    # -----------------------------
    # Public entrypoint
    # -----------------------------

    def _run(
            self,
            action: str = "send",
            to: Optional[list[str]] = None,
            subject: Optional[str] = None,
            body: Optional[str] = None,
            attachments: Optional[list[str]] = None,
            **kwargs,
    ) -> dict[str, Any]:
        """
        Run the email service tool.

        Returns a dict with:
          - success (bool)
          - status (str)
          - message (str)
          - ... action-specific fields
        """
        attachments = attachments if attachments is not None else []

        try:
            if action == "send":
                # Determine DRY_RUN from environment (default true) and run_id
                try:
                    dry_run_env = os.getenv("DRY_RUN", "true").strip().lower() in ("1", "true", "yes", "y", "on")
                    dry_run = bool(kwargs.get("dry_run", dry_run_env))
                    run_id = kwargs.get("run_id") or os.getenv("RUN_ID") or uuid.uuid4().hex[:8]
                except (ValueError, AttributeError):
                    dry_run = True
                    run_id = "00000000"

                return EmailService._send_email(
                    to=to,
                    subject=subject,
                    body=body,
                    attachments=attachments,
                    dry_run=dry_run,
                    run_id=run_id,
                )

            if action == "search":
                query = (kwargs.get("query") or "").strip()
                max_results = int(kwargs.get("max_results") or 25)
                return EmailService._search_emails_via_gmail(query=query, max_results=max_results)

            if action == "check":
                return EmailService._check_inbox_via_gmail()

            if action == "ingest_unread_inbox_v1":
                max_results = int(kwargs.get("max_results") or 25)
                label_name = (kwargs.get("label_name") or "Scribe/Incoming").strip()
                log_path = kwargs.get("log_path")
                dry_run = bool(kwargs.get("dry_run", False))
                query = kwargs.get("query")  # <-- accept optional override from CLI/task

                return EmailService.ingest_unread_inbox_v1(
                    max_results=max_results,
                    label_name=label_name,
                    log_path=log_path,
                    dry_run=dry_run,
                    query=query,  # <-- pass it through
                )

            if action == "stage_attachments_v2":
                max_results = int(kwargs.get("max_results") or 25)
                label_name = (kwargs.get("label_name") or "Scribe/Incoming").strip()
                log_path = kwargs.get("log_path")
                dry_run = bool(kwargs.get("dry_run", False))
                query = kwargs.get("query")
                cycle = kwargs.get("cycle")
                out_root = kwargs.get("out_root")
                force = bool(kwargs.get("force", False))
                skip_unknown = bool(kwargs.get("skip_unknown", False))

                return EmailService.stage_attachments_v2(
                    max_results=max_results,
                    label_name=label_name,
                    log_path=log_path,
                    dry_run=dry_run,
                    query=query,
                    cycle=cycle,
                    out_root=out_root,
                    force=force,
                    skip_unknown=skip_unknown,
                )

            return {"success": False, "status": "failed", "message": f"Unknown action: {action}", "action": action}

        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"EmailService action failed: action={action} err={e}")
            logger.error(tb)
            return {
                "success": False,
                "status": "failed",
                "message": str(e),
                "error": str(e),
                "traceback": tb,
                "action": action,
            }

    # -----------------------------
    # Gmail service helpers
    # -----------------------------

    @staticmethod
    def _get_gmail_service() -> Any:
        creds = get_google_credentials()
        if not creds:
            raise RuntimeError("Failed to get Google credentials. Check credentials.json / token configuration.")
        return build("gmail", "v1", credentials=creds)

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _safe_write_unique(path: Path, data: bytes) -> Path:
        """
        Write bytes to path, adding -N before extension if collision occurs.
        Returns final path written.
        """
        candidate = path
        stem = path.stem
        suffix = path.suffix
        counter = 1
        while candidate.exists():
            candidate = path.with_name(f"{stem}-{counter}{suffix}")
            counter += 1
        candidate.parent.mkdir(parents=True, exist_ok=True)
        with candidate.open("wb") as f:
            f.write(data)
        return candidate

    @staticmethod
    def _write_overwrite(path: Path, data: bytes) -> Path:
        """
        Write bytes to path, overwriting if it exists.
        Returns the final path written.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            f.write(data)
        return path

    @staticmethod
    def _safe_header(headers: list[dict[str, str]], name: str) -> str:
        target = name.lower()
        for h in headers or []:
            if (h.get("name") or "").lower() == target:
                return h.get("value") or ""
        return ""

    # -----------------------------
    # IngestorAgent v1
    # -----------------------------

    @staticmethod
    def ingest_unread_inbox_v1(
            max_results: int = 25,
            label_name: str = "Scribe/Incoming",
            log_path: Optional[str] = None,
            dry_run: bool = False,
            query: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Manual, non-destructive ingestion:
        - Query defaults to: is:unread in:inbox -category:promotions -category:social -category:updates
          (but may be overridden by caller)
        - For each message: fetch metadata, classify, apply label, append JSONL record (with classification_confidence)
        - Idempotent: skip messages already labeled `label_name` (prevents duplicate logs)
        - NO reply, NO mark read, NO attachment downloads
        """
        # Resolve log path default
        if not log_path:
            base_src = Path(__file__).resolve().parents[2]  # .../src
            log_dir = base_src / "scribe" / "output" / "ingestion"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = str(log_dir / "ingest_log.jsonl")

        # Use caller-provided query if present; otherwise the v1 default
        query = (query or DEFAULT_INGEST_QUERY).strip()
        logger.info(f"Ingest v1: query='{query}', max_results={max_results}, label='{label_name}', dry_run={dry_run}")

        service = EmailService._get_gmail_service()

        # Resolve label id (read-only if dry_run; create if needed when not dry_run)
        if dry_run:
            label_id = EmailService._get_label_id_if_exists(service=service, label_name=label_name)
        else:
            label_id = EmailService._ensure_label(service=service, label_name=label_name)

        # List messages
        msg_ids = EmailService._list_message_ids(service=service, query=query, max_results=max_results)
        candidates_count = len(msg_ids)

        processed: list[dict[str, Any]] = []
        skipped_already_labeled = 0
        labeled_count = 0
        logged_count = 0

        for mid in msg_ids:
            meta = EmailService._get_message_metadata(service=service, message_id=mid)

            # Idempotency: if label exists and message already has it, skip entirely
            already_labeled = False
            if label_id and (label_id in (meta.get("label_ids") or [])):
                already_labeled = True

            if already_labeled:
                skipped_already_labeled += 1
                continue

            from_addr = meta.get("from", "")
            subject = meta.get("subject", "")
            snippet = meta.get("snippet", "")

            attachments = meta.get("attachments") or []
            has_attachments = len(attachments) > 0
            attachments_total_size = sum((a.get("size") or 0) for a in attachments)

            classification, classification_confidence = EmailService._classify_message(
                from_addr=from_addr,
                subject=subject,
                snippet=snippet,
                attachments=attachments,
            )

            label_applied = False
            if (not dry_run) and label_id:
                label_applied = EmailService._apply_label(service=service, message_id=mid, label_id=label_id)
                if label_applied:
                    labeled_count += 1

            record = {
                "timestamp": EmailService._now_iso(),
                "message_id": meta.get("message_id"),
                "thread_id": meta.get("thread_id"),
                "internal_date": meta.get("internal_date"),
                "from": from_addr,
                "subject": subject,
                "snippet": snippet,
                "has_attachments": has_attachments,
                "attachments_count": len(attachments),
                "attachments_total_size": attachments_total_size,
                "attachments": attachments,
                "classification": classification,
                "classification_confidence": classification_confidence,
                "label_name": label_name,
                "label_applied": label_applied,
                "logged": not dry_run,
                "dry_run": dry_run,
            }

            if not dry_run:
                EmailService._append_jsonl(path=log_path, obj=record)
                logged_count += 1

            processed.append(record)

        return {
            "success": True,
            "status": "completed",
            "action": "ingest_unread_inbox_v1",
            "message": (
                f"Processed {len(processed)} messages "
                f"(skipped {skipped_already_labeled} already labeled)."
            ),
            "query": query,
            "max_results": max_results,
            "label_name": label_name,
            "label_id": label_id,
            "log_path": log_path,
            "dry_run": dry_run,
            "processed_count": len(processed),
            "skipped_already_labeled": skipped_already_labeled,
            "labeled_count": labeled_count,
            "logged_count": logged_count,
            "processed": processed,
            "candidates_count": candidates_count,
        }

    @staticmethod
    def _classify_message(
            from_addr: str,
            subject: str,
            snippet: str,
            attachments: Optional[list[dict[str, Any]]] = None,
    ) -> tuple[str, str]:
        """
        Attachment-first heuristic classifier (report-centric).

        Taxonomy:
          - report-submission
          - forwarded-report
          - meeting-minutes
          - administrative-message
          - unknown

        Confidence:
          - high: strong attachment signals (pdf/doc/docx/xlsx) and/or strong subject cues
          - medium: attachments present but weak/odd signals
          - low: no attachments and no strong cues
        """
        attachments = attachments or []
        subj = (subject or "").strip().lower()
        text = f"{from_addr}\n{subject}\n{snippet}".lower()

        # Attachment signals
        filenames = [(a.get("filename") or "").lower() for a in attachments]
        has_attachments = len(attachments) > 0

        strong_doc = any(fn.endswith((".pdf", ".docx", ".doc", ".xlsx", ".xls")) for fn in filenames)
        minutes_cue = ("minutes" in subj) or any("minutes" in fn for fn in filenames) or ("draft minutes" in text)
        forwarded_cue = subj.startswith(("fwd:", "fw:")) or "forwarded message" in text

        if has_attachments:
            if minutes_cue:
                confidence = "high" if strong_doc else "medium"
                return "meeting-minutes", confidence

            if forwarded_cue:
                confidence = "high" if strong_doc else "medium"
                return "forwarded-report", confidence

            # Default: attachments imply a report submission
            confidence = "high" if strong_doc else "medium"
            return "report-submission", confidence

        # No attachments: likely administrative chatter (or unknown)
        admin_cues = ["question", "schedule", "time", "location", "agenda", "meeting"]
        if any(c in text for c in admin_cues):
            return "administrative-message", "medium"

        return "unknown", "low"

    # -----------------------------
    # Gmail API operations used by v1
    # -----------------------------

    @staticmethod
    def _list_message_ids(service: Any, query: str, max_results: int) -> list[str]:
        try:
            resp = service.users().messages().list(
                userId="me",
                q=query,
                maxResults=max_results,
            ).execute()
            msgs = resp.get("messages", []) or []
            return [m.get("id") for m in msgs if m.get("id")]
        except HttpError as e:
            raise RuntimeError(f"Gmail API list messages failed: {e}") from e

    @staticmethod
    def _extract_attachment_metadata(payload: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Recursively walk the Gmail payload tree and collect true attachment metadata.
        We only treat a part as an attachment if it has an attachmentId (downloadable).
        """
        attachments: list[dict[str, Any]] = []

        def walk(part: dict[str, Any]) -> None:
            if not part:
                return

            filename = (part.get("filename") or "").strip()
            mime_type = (part.get("mimeType") or "").strip()
            body = part.get("body") or {}
            attachment_id = body.get("attachmentId")
            size = body.get("size", 0)

            # Only real downloadable attachments have attachmentId
            if attachment_id:
                attachments.append({
                    "filename": filename,
                    "mime_type": mime_type or "application/octet-stream",
                    "size": int(size) if isinstance(size, int) else int(size) if str(size).isdigit() else 0,
                    "attachment_id": attachment_id,
                })

            for child in (part.get("parts") or []):
                walk(child)

        walk(payload)
        return attachments

    @staticmethod
    def _extract_attachment_metadata_v2(payload: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Alias to v1 helper (kept for clarity in v2 code path).
        """
        return EmailService._extract_attachment_metadata(payload)

    @staticmethod
    def _get_message_metadata(service: Any, message_id: str) -> dict[str, Any]:
        """
        Fetches message metadata plus payload structure (no attachment bytes) so attachments can be enumerated.
        Also includes labelIds so ingestion can be idempotent.

        IMPORTANT: This method does NOT download attachment bytes. It only reads the message payload structure.
        """
        try:
            msg = service.users().messages().get(
                userId="me",
                id=message_id,
                format="full",  # includes payload structure so attachments can be enumerated
                fields=(
                    "id,threadId,labelIds,internalDate,snippet,"
                    "payload("
                    "headers/name,headers/value,"
                    "filename,mimeType,"
                    "body/size,body/attachmentId,"
                    "parts(headers/name,headers/value,filename,mimeType,body/size,body/attachmentId,parts)"
                    ")"
                ),
            ).execute()
        except HttpError as e:
            raise RuntimeError(f"Gmail API get message failed (id={message_id}): {e}") from e

        payload = msg.get("payload") or {}
        headers = payload.get("headers") or []
        internal_ms = msg.get("internalDate")  # string millis
        internal_dt = None
        if internal_ms:
            try:
                internal_dt = datetime.fromtimestamp(int(internal_ms) / 1000, tz=timezone.utc).isoformat()
            except (ValueError, OSError, OverflowError):
                internal_dt = None

        attachments = EmailService._extract_attachment_metadata(payload)

        return {
            "message_id": msg.get("id"),
            "thread_id": msg.get("threadId"),
            "internal_date": internal_dt,
            "label_ids": msg.get("labelIds") or [],
            "from": EmailService._safe_header(headers, "From"),
            "subject": EmailService._safe_header(headers, "Subject"),
            "date": EmailService._safe_header(headers, "Date"),
            "snippet": msg.get("snippet", "") or "",
            "attachments": attachments,
        }

    @staticmethod
    def _get_message_full_for_attachments(service: Any, message_id: str) -> dict[str, Any]:
        """
        Fetch full payload fields sufficient to enumerate and download attachments.
        Includes labelIds for idempotency decisions.
        """
        try:
            msg = service.users().messages().get(
                userId="me",
                id=message_id,
                format="full",
                fields=(
                    "id,threadId,labelIds,internalDate,snippet,"
                    "payload("
                    "headers/name,headers/value,"
                    "filename,mimeType,"
                    "body/size,body/attachmentId,"
                    "parts(headers/name,headers/value,filename,mimeType,body/size,body/attachmentId,parts)"
                    ")"
                ),
            ).execute()
        except HttpError as e:
            raise RuntimeError(f"Gmail API get message failed (id={message_id}): {e}") from e

        payload = msg.get("payload") or {}
        headers = payload.get("headers") or []
        internal_ms = msg.get("internalDate")
        internal_dt = None
        if internal_ms:
            try:
                internal_dt = datetime.fromtimestamp(int(internal_ms) / 1000, tz=timezone.utc).isoformat()
            except (ValueError, OSError, OverflowError):
                internal_dt = None

        attachments = EmailService._extract_attachment_metadata_v2(payload)

        return {
            "message_id": msg.get("id"),
            "thread_id": msg.get("threadId"),
            "internal_date": internal_dt,
            "label_ids": msg.get("labelIds") or [],
            "from": EmailService._safe_header(headers, "From"),
            "subject": EmailService._safe_header(headers, "Subject"),
            "snippet": msg.get("snippet", "") or "",
            "payload": payload,
            "attachments": attachments,
        }

    @staticmethod
    def _get_label_id_if_exists(service: Any, label_name: str) -> Optional[str]:
        """
        Read-only label lookup. Returns label id or None if not found.
        """
        try:
            labels_resp = service.users().labels().list(userId="me").execute()
            labels = labels_resp.get("labels", []) or []
            for lbl in labels:
                if (lbl.get("name") or "").strip() == label_name:
                    return lbl.get("id")
            return None
        except HttpError as e:
            raise RuntimeError(f"Gmail API list labels failed: {e}") from e

    @staticmethod
    def _ensure_label(service: Any, label_name: str) -> str:
        """
        Returns label ID. Creates user label if it doesn't exist.
        This is the only allowed mailbox-side "creation" in v1 (label definition).
        """
        existing = EmailService._get_label_id_if_exists(service=service, label_name=label_name)
        if existing:
            return existing

        try:
            created = service.users().labels().create(
                userId="me",
                body={
                    "name": label_name,
                    "labelListVisibility": "labelShow",
                    "messageListVisibility": "show",
                    "type": "user",
                },
            ).execute()
            return created.get("id")
        except HttpError as e:
            raise RuntimeError(f"Gmail API create label failed (name={label_name}): {e}") from e

    @staticmethod
    def _download_attachment_bytes(service: Any, message_id: str, attachment_id: str) -> bytes:
        try:
            resp = service.users().messages().attachments().get(
                userId="me",
                messageId=message_id,
                id=attachment_id,
            ).execute()
        except HttpError as e:
            raise RuntimeError(
                f"Gmail API get attachment failed (message_id={message_id}, attachment_id={attachment_id}): {e}") from e

        data = resp.get("data")
        if data is None:
            return b""

        # base64url decode with padding fix
        padded = data.encode("utf-8") + b"=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(padded)

    @staticmethod
    def _apply_label(service: Any, message_id: str, label_id: str) -> bool:
        """
        Adds label only. Does NOT remove UNREAD or INBOX.
        """
        try:
            service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"addLabelIds": [label_id], "removeLabelIds": []},
            ).execute()
            return True
        except HttpError as e:
            logger.error(f"Failed to apply label: message_id={message_id} label_id={label_id} err={e}")
            return False

    @staticmethod
    def _append_jsonl(path: str, obj: dict[str, Any]) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    # -----------------------------
    # Existing send logic (kept)
    # -----------------------------

    @staticmethod
    def _validate_email(email: str) -> bool:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def _send_email(
            to: Optional[list[str]],
            subject: Optional[str],
            body: Optional[str],
            attachments: Optional[list[str]],
            dry_run: bool = False,
            run_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Send an email to the specified recipients using Gmail API.
        (Existing behavior preserved.)
        """
        # Read EMAIL_FROM at send time (avoid import-time env surprises)
        default_sender = os.getenv("EMAIL_FROM")

        # Check for DEV_OVERRIDE_EMAIL environment variable
        dev_override = os.getenv("DEV_OVERRIDE_EMAIL")
        original_recipients = to

        if dev_override and not dry_run:
            logger.warning(f"DEV_OVERRIDE_EMAIL is set - redirecting all emails to {dev_override}")
            logger.info(f"Original recipients were: {mask_emails(to) if to else 'none'}")
            to = [dev_override]

        recipients_str = mask_emails(to) if to else "no recipients"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        send_result = {
            "success": False,
            "message": "",
            "recipients": to or [],
            "subject": subject or "",
            "status": "unknown",
            "timestamp": timestamp,
            "recipient_statuses": [],
            "error": "",
            "traceback": "",
        }

        if dev_override and not dry_run:
            send_result["dev_override_active"] = True
            send_result["original_recipients"] = original_recipients or []
            send_result["overridden_to"] = dev_override

        # If dry run, do not attempt Gmail API send. Reminder workflow already writes
        # a canonical draft artifact via MeetingNotificationTool.
        if dry_run:
            send_result.update({
                "success": True,
                "message": "Dry run complete. No email sent.",
                "status": "dry_run",
                "recipient_statuses": [{"email": email, "status": "would_send"} for email in (to or [])],
                "run_id": run_id,
            })
            return send_result

        # Check if EMAIL_FROM is set (only required for real sends)
        if default_sender is None:
            error_message = "EMAIL_FROM environment variable is not set. Please set EMAIL_FROM in your environment."
            logger.error(error_message)
            send_result.update({
                "message": error_message,
                "status": "failed",
                "error": error_message,
            })
            return send_result

        try:
            service = EmailService._get_gmail_service()

            msg = MIMEMultipart()
            msg["From"] = default_sender
            msg["Subject"] = subject or ""

            if to:
                msg["To"] = ", ".join(to)
            else:
                error_message = "Error: No recipients specified"
                logger.warning(error_message)
                send_result.update({
                    "message": error_message,
                    "status": "failed",
                    "error": error_message,
                })
                return send_result

            if body:
                msg.attach(MIMEText(body, "plain"))

            if attachments and len(attachments) > 0:
                for attachment_path in attachments:
                    if not os.path.exists(attachment_path):
                        logger.warning(f"Attachment file not found: {attachment_path}")
                        continue

                    with open(attachment_path, "rb") as f:
                        file_content = f.read()

                    content_type, _ = mimetypes.guess_type(attachment_path)
                    if not content_type:
                        _ = "application/octet-stream"  # content_type not used; MIMEApplication handles it

                    file_name = os.path.basename(attachment_path)
                    if file_name.startswith("agenda_") and file_name.endswith(".pdf"):
                        parts = file_name.split("_")
                        if len(parts) >= 2:
                            meeting_date = parts[1]
                            file_name = f"Agenda_{meeting_date}.pdf"

                    part = MIMEApplication(file_content, Name=file_name)
                    part["Content-Disposition"] = f'attachment; filename="{file_name}"'
                    msg.attach(part)

            raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()

            message = service.users().messages().send(
                userId="me",
                body={"raw": raw_message},
            ).execute()

            message_id = message.get("id", "unknown")

            log_message = f"Email sent at {timestamp} (Message ID: {message_id}):"
            logger.info(log_message)
            logger.info(f"Recipients: {recipients_str}")
            logger.info(f"Subject: {subject}")

            send_result.update({
                "success": True,
                "message": log_message,
                "status": "sent",
                "message_id": message_id,
                "recipient_statuses": [{"email": email, "status": "sent"} for email in (to or [])],
                "run_id": run_id,
            })
            return send_result

        except (HttpError, Exception) as e:
            tb_str = traceback.format_exc()
            error_prefix = "Gmail API error" if isinstance(e, HttpError) else "Error sending email"
            error_message = f"{error_prefix}: {str(e)}"
            logger.error(f"Email send failed: {error_message}")
            logger.error(f"Attempted to send to: {recipients_str}")
            logger.error(f"Subject: {subject}")
            logger.error(f"Traceback: {tb_str}")

            send_result.update({
                "message": error_message,
                "status": "failed",
                "error": str(e),
                "traceback": tb_str,
                "recipient_statuses": [{"email": email, "status": "failed", "error": str(e)} for email in (to or [])],
            })
            return send_result

    # -----------------------------
    # Gmail-backed check/search (kept)
    # -----------------------------

    @staticmethod
    def _check_inbox_via_gmail() -> dict[str, Any]:
        """
        Returns lightweight presence checks for total INBOX and unread INBOX.
        """
        service = EmailService._get_gmail_service()

        total_ids = EmailService._list_message_ids(service=service, query="in:inbox", max_results=1)
        unread_ids = EmailService._list_message_ids(service=service, query=DEFAULT_INGEST_QUERY, max_results=1)

        return {
            "success": True,
            "status": "completed",
            "action": "check",
            "message": "Checked inbox status (non-destructive).",
            "inbox_has_messages": bool(total_ids),
            "inbox_has_unread": bool(unread_ids),
            "timestamp": EmailService._now_iso(),
            "note": "For exact counts, we'd need pagination; this is intentionally lightweight for v1.",
        }

    @staticmethod
    def _search_emails_via_gmail(query: str, max_results: int = 25) -> dict[str, Any]:
        service = EmailService._get_gmail_service()
        msg_ids = EmailService._list_message_ids(service=service, query=query, max_results=max_results)
        metas = [EmailService._get_message_metadata(service=service, message_id=mid) for mid in msg_ids]
        return {
            "success": True,
            "status": "completed",
            "action": "search",
            "query": query,
            "max_results": max_results,
            "results_count": len(metas),
            "results": metas,
            "timestamp": EmailService._now_iso(),
        }

    # -----------------------------
    # IngestorAgent v2 - attachment staging
    # -----------------------------

    @staticmethod
    def _extract_sender_email(from_addr: str) -> str:
        """
        Extract normalized sender email from headers like:
        'Name <email@domain>' or raw 'email@domain'.
        """
        raw = (from_addr or "").strip().lower()
        m = re.search(r"<([^>]+@[^>]+)>", raw)
        return (m.group(1) if m else raw).strip()

    @staticmethod
    def _office_stem_from_text(text: str) -> str:
        """
        Convert governance body/office text to lowerCamel office stem.
        """
        value = (text or "").strip()
        if not value:
            return ""
        value = re.sub(r"(?i)\bcommittee\b", "", value)
        value = value.replace("&", " and ").replace("/", " ")
        value = re.sub(r"[^A-Za-z0-9]+", " ", value).strip()
        if not value:
            return ""
        parts = [p for p in value.split(" ") if p]
        if not parts:
            return ""
        return parts[0].lower() + "".join(p[:1].upper() + p[1:] for p in parts[1:])

    @staticmethod
    def _sender_office_stem_from_db(from_addr: str) -> Optional[str]:
        """
        Conservative DB fallback:
        - derive sender email
        - get active terms for that sender
        - return a stem only if exactly one unique active office/body stem is found
        """
        sender_email = EmailService._extract_sender_email(from_addr)
        if "@" not in sender_email:
            return None

        try:
            from src.scribe.database import get_db_session
            from src.scribe.clerk_models import Person, Office, Term, Body
        except Exception:
            return None

        db = get_db_session()
        try:
            today = date.today()
            rows = (
                db.query(Office.title, Body.name)
                .join(Term, Term.term_office_id == Office.office_id)
                .join(Person, Term.term_person_id == Person.person_id)
                .join(Body, Office.office_body_id == Body.body_id)
                .filter(Person.email.ilike(sender_email))
                .filter((Term.end.is_(None)) | (Term.end >= today))
                .all()
            )
        except Exception:
            return None
        finally:
            try:
                db.close()
            except Exception:
                pass

        stems = set()
        chair_body_stems = set()
        for title_raw, body_name_raw in rows:
            title = (title_raw or "").strip().lower()
            body_name = (body_name_raw or "").strip()
            body_name_lower = body_name.lower()

            # Direct officer title mapping first.
            if title == "executive director":
                stems.add("director")
                continue
            if title == "vice president":
                stems.add("vicePresident")
                continue
            if title == "president":
                stems.add("president")
                continue
            if title == "treasurer":
                stems.add("treasurer")
                continue
            if title == "secretary":
                stems.add("secretary")
                continue
            if title in ("administrative assistant", "assistant"):
                stems.add("administrativeAssistant")
                continue

            # Wing roles may vary by title/body; infer canonical wing stems.
            wing_match = re.search(r"\bwing\s*([a-g])\b", f"{title} {body_name}".lower())
            if wing_match:
                stems.add(f"wing{wing_match.group(1).upper()}")
                continue

            # Committee chairs and other committee/body-bound roles use body name.
            # Ignore council body names for this generic derivation.
            if "council" in body_name_lower:
                continue
            derived = EmailService._office_stem_from_text(body_name)
            if derived:
                stems.add(derived)
                if title == "chair":
                    chair_body_stems.add(derived)

        if len(stems) == 1:
            return next(iter(stems))
        # If sender has one unique non-council chair body, prefer that when
        # broader active-role set is otherwise ambiguous.
        if len(chair_body_stems) == 1:
            return next(iter(chair_body_stems))
        return None

    @staticmethod
    def _is_open_cycle(cycle: Optional[str]) -> bool:
        """
        Minimal meeting-type guard for staging business rules.
        For current workflow, 2026-03 is an open meeting cycle.
        """
        return (cycle or "").strip() == "2026-03"

    @staticmethod
    def _should_exclude_from_staging(
            cycle: Optional[str],
            from_addr: str,
            subject: str,
            snippet: str,
            attachments: Optional[list[dict[str, Any]]] = None,
    ) -> bool:
        """
        Exclude known non-report artifacts from report staging.
        - Reminder-originated reminder emails
        - Liaison reports during open meeting cycles
        """
        attachments = attachments or []
        sender_email = EmailService._extract_sender_email(from_addr)
        subj = (subject or "").lower()
        snip = (snippet or "").lower()
        filenames = " ".join((a.get("filename") or "") for a in attachments).lower()
        all_text = f"{subj}\n{snip}\n{filenames}"

        # Reminder-originated reminder emails should never be staged as reports.
        reminder_sender = EmailService._extract_sender_email(os.getenv("EMAIL_FROM", ""))
        if reminder_sender and sender_email == reminder_sender and "open meeting reminder" in subj:
            return True

        # Liaison reports are not valid for open meeting cycles.
        if EmailService._is_open_cycle(cycle):
            liaison_cue = ("liaison report" in all_text) or re.search(r"\bliaison\b", all_text)
            # Executive Director / Management reports remain eligible at all times.
            director_cue = re.search(r"\bexecutive director\b|\bdirector\b|\bmanagement report\b", all_text)
            if liaison_cue and not director_cue:
                return True

        return False

    @staticmethod
    def _infer_office_stem(
            from_addr: str,
            subject: str,
            snippet: str,
            attachments: Optional[list[dict[str, Any]]] = None,
    ) -> str:
        office, _ = EmailService._infer_office_stem_with_reason(
            from_addr=from_addr,
            subject=subject,
            snippet=snippet,
            attachments=attachments,
        )
        return office

    @staticmethod
    def _normalize_signal_text(text: str, *, is_subject: bool = False) -> str:
        value = (text or "").lower()
        # Remove bracketed tags like [external], [spam], etc.
        value = re.sub(r"\[[^\]]+\]", " ", value)
        if is_subject:
            # Repeatedly strip common reply/forward prefixes.
            while True:
                stripped = re.sub(r"^\s*(?:re|fw|fwd)\s*:\s*", "", value)
                if stripped == value:
                    break
                value = stripped
        # Ignore punctuation differences.
        value = re.sub(r"[^a-z0-9]+", " ", value)
        value = re.sub(r"\s+", " ", value).strip()
        return value

    @staticmethod
    def _office_aliases() -> list[tuple[str, list[str]]]:
        return [
            ("director", ["executive director", "management report", "management", "director report"]),
            ("vicePresident", [
                "vice president",
                "vicepresident",
                "consol wings report",
                "consolidated wings report",
            ]),
            ("president", ["president report", "president"]),
            ("secretary", ["secretary"]),
            ("administrativeAssistant", ["administrative assistant", "admin assistant", "assistant report"]),
            ("buildingMaintenance", ["building maintenance", "maintenance committee", "maintenance"]),
            ("dining", ["dining committee", "dining"]),
            ("employeeAppreciation", [
                "employee appreciation committee",
                "employee appreciation liaison",
                "employee appreciation",
                "ea c",
                "eac",
            ]),
            ("treasurer", ["treasurer"]),
            ("environmentLandscape", [
                "environment landscape",
                "environment and landscape",
                "env land",
                "e l",
                "environment",
                "landscape",
            ]),
            ("finance", ["finance committee", "finance", "financial report"]),
            ("library", ["library committee", "library"]),
            ("scholarship", ["scholarship committee", "scholarship"]),
            ("specialEventsAndTrips", ["special events and trips", "special events", "events and trips", "trips"]),
            ("nominatingCommittee", ["nominating committee", "nominating report"]),
            ("wingA", ["wing a", "winga", "liffey a wing", "a wing"]),
            ("wingB", ["wing b", "wingb", "liffey b wing", "b wing"]),
            ("wingC", ["wing c", "wingc", "liffey c wing", "c wing"]),
            ("wingD", ["wing d", "wingd", "killarney d wing", "d wing"]),
            ("wingE", ["wing e", "winge", "shannon e wing", "e wing"]),
            ("wingF", ["wing f", "wingf", "shannon f wing", "f wing"]),
            ("wingG", ["wing g", "wingg", "shannon g wing", "g wing"]),
        ]

    @staticmethod
    def _match_office_aliases(signal_text: str) -> Optional[str]:
        if not signal_text:
            return None
        for canonical, terms in EmailService._office_aliases():
            for term in terms:
                pattern = rf"\b{re.escape(term)}\b"
                if re.search(pattern, signal_text):
                    return canonical
        return None

    @staticmethod
    def _infer_office_stem_from_attachment_filename(filename: str) -> Optional[str]:
        normalized_stem = EmailService._normalize_signal_text(Path(filename).stem)
        if re.fullmatch(r"(?:executive )?director(?: s)?(?: report)?", normalized_stem):
            return "director"

        normalized_filename = EmailService._normalize_signal_text(filename)
        return EmailService._match_office_aliases(normalized_filename)

    @staticmethod
    def _infer_attachment_office_with_reason(
            filename: str,
            from_addr: str,
            subject: str,
    ) -> tuple[str, str]:
        filename_match = EmailService._infer_office_stem_from_attachment_filename(filename)
        if filename_match:
            return filename_match, "attachment_filename_alias"

        normalized_subject = EmailService._normalize_signal_text(subject, is_subject=True)
        subject_match = EmailService._match_office_aliases(normalized_subject)
        if subject_match:
            return subject_match, "message_subject_alias"

        sender_fallback = EmailService._sender_office_stem_from_db(from_addr)
        if sender_fallback:
            return sender_fallback, "message_sender_fallback"

        return "unknown", "no_match"

    @staticmethod
    def _infer_office_stem_with_reason(
            from_addr: str,
            subject: str,
            snippet: str,
            attachments: Optional[list[dict[str, Any]]] = None,
    ) -> tuple[str, str]:
        """
        Infer canonical office key from email metadata and attachment filenames.

        Returns canonical keys aligned with report_map.json.
        Order matters:
        - normalized content cues (subject/body/attachments)
        - advisory sender fallback
        """

        attachments = attachments or []
        normalized_subject = EmailService._normalize_signal_text(subject, is_subject=True)
        normalized_snippet = EmailService._normalize_signal_text(snippet)
        normalized_filenames = EmailService._normalize_signal_text(
            " ".join((a.get("filename") or "") for a in attachments)
        )

        subject_match = EmailService._match_office_aliases(normalized_subject)
        if subject_match:
            return subject_match, "subject_alias"

        filename_match = EmailService._match_office_aliases(normalized_filenames)
        snippet_match = EmailService._match_office_aliases(normalized_snippet)

        if filename_match and snippet_match and filename_match == snippet_match:
            return filename_match, "body_and_attachment_alias"
        if filename_match:
            return filename_match, "attachment_alias"
        if snippet_match:
            return snippet_match, "body_alias"

        # Advisory fallback only when content cues do not strongly match.
        sender_fallback = EmailService._sender_office_stem_from_db(from_addr)
        if sender_fallback:
            return sender_fallback, "sender_fallback"

        return "unknown", "no_match"

    @staticmethod
    def _should_restage_labeled_message(office_dir: Path, internal_date_iso: Optional[str]) -> bool:
        """
        Allow re-staging labeled messages when office has no staged assets yet,
        or when message timestamp is newer than all staged files for that office.
        """
        files = [p for p in office_dir.glob("*") if p.is_file()]
        if not files:
            return True
        if not internal_date_iso:
            return False
        try:
            msg_ts = datetime.fromisoformat(internal_date_iso)
        except Exception:
            return False
        latest_file_ts = max(datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc) for p in files)
        return msg_ts > latest_file_ts

    @staticmethod
    def stage_attachments_v2(
            max_results: int = 25,
            label_name: str = "Scribe/Incoming",
            log_path: Optional[str] = None,
            dry_run: bool = False,
            query: Optional[str] = None,
            cycle: Optional[str] = None,
            out_root: Optional[str] = None,
            force: bool = False,
            skip_unknown: bool = False,
    ) -> dict[str, Any]:
        if not cycle:
            raise ValueError("cycle is required for stage_attachments_v2 (e.g., '2026-02')")

        base_src = Path(__file__).resolve().parents[2]  # .../src
        if not log_path:
            log_dir = base_src / "scribe" / "output" / "ingestion"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = str(log_dir / "ingest_log.jsonl")

        out_root_path = Path(out_root) if out_root else (base_src / "scribe" / "output" / "cycles")

        default_with_attachments = f"{DEFAULT_INGEST_QUERY} in:anywhere has:attachment newer_than:30d"
        query = (query or default_with_attachments).strip()
        logger.info(
            f"Stage attachments v2: query='{query}', max_results={max_results}, label='{label_name}', cycle={cycle}, dry_run={dry_run}"
        )

        service = EmailService._get_gmail_service()

        # Label resolution
        if dry_run:
            label_id = EmailService._get_label_id_if_exists(service=service, label_name=label_name)
        else:
            label_id = EmailService._ensure_label(service=service, label_name=label_name)

        msg_ids = EmailService._list_message_ids(service=service, query=query, max_results=max_results)
        candidates_count = len(msg_ids)

        processed: list[dict[str, Any]] = []
        skipped_already_labeled = 0
        labeled_count = 0
        saved_attachments_count = 0

        for mid in msg_ids:
            meta = EmailService._get_message_full_for_attachments(service=service, message_id=mid)

            from_addr = meta.get("from", "")
            subject = meta.get("subject", "")
            snippet = meta.get("snippet", "")
            attachments_meta = meta.get("attachments") or []
            classification, classification_confidence = EmailService._classify_message(
                from_addr=from_addr,
                subject=subject,
                snippet=snippet,
                attachments=attachments_meta,
            )

            if EmailService._should_exclude_from_staging(
                    cycle=cycle,
                    from_addr=from_addr,
                    subject=subject,
                    snippet=snippet,
                    attachments=attachments_meta,
            ):
                record = {
                    "timestamp": EmailService._now_iso(),
                    "action": "stage_attachments_v2",
                    "status": "skipped_non_report",
                    "cycle": cycle,
                    "message_id": meta.get("message_id"),
                    "thread_id": meta.get("thread_id"),
                    "internal_date": meta.get("internal_date"),
                    "from": from_addr,
                    "subject": subject,
                    "office": None,
                    "attachments": [],
                    "classification": classification,
                    "classification_confidence": classification_confidence,
                    "label_name": label_name,
                    "label_applied": False,
                    "dry_run": dry_run,
                    "force": force,
                }
                processed.append(record)
                continue

            office, office_reason = EmailService._infer_office_stem_with_reason(
                from_addr=from_addr,
                subject=subject,
                snippet=snippet,
                attachments=attachments_meta,
            )

            already_labeled = bool(label_id and (label_id in (meta.get("label_ids") or [])))
            office_dir = out_root_path / cycle / "originals" / office
            allow_restage = False
            if already_labeled and not force and office != "unknown":
                allow_restage = EmailService._should_restage_labeled_message(
                    office_dir=office_dir,
                    internal_date_iso=meta.get("internal_date"),
                )

            # Default behavior: skip already-labeled messages (idempotent),
            # but allow restage when message is newer for same office.
            if already_labeled and not force and not allow_restage:
                record = {
                    "timestamp": EmailService._now_iso(),
                    "action": "stage_attachments_v2",
                    "status": "skipped_already_labeled",
                    "cycle": cycle,
                    "message_id": meta.get("message_id"),
                    "thread_id": meta.get("thread_id"),
                    "internal_date": meta.get("internal_date"),
                    "from": meta.get("from", ""),
                    "subject": meta.get("subject", ""),
                    "office": office,
                    "office_inference_reason": office_reason,
                    "attachments": [],
                    "classification": classification,
                    "classification_confidence": classification_confidence,
                    "label_name": label_name,
                    "label_applied": False,
                    "dry_run": dry_run,
                    "force": force,
                    "decision_reason": "already_labeled_not_newer",
                }
                skipped_already_labeled += 1
                logger.info(
                    "Stage v2 skip: message_id=%s office=%s reason=%s",
                    meta.get("message_id"),
                    office,
                    "already_labeled_not_newer",
                )
                processed.append(record)
                continue

            attachment_office_inferences = [
                EmailService._infer_attachment_office_with_reason(
                    filename=a.get("filename") or "",
                    from_addr=from_addr,
                    subject=subject,
                )
                for a in attachments_meta
            ]

            if skip_unknown and all(
                    attachment_office == "unknown"
                    for attachment_office, _ in attachment_office_inferences
            ):
                record = {
                    "timestamp": EmailService._now_iso(),
                    "action": "stage_attachments_v2",
                    "status": "skipped_unknown_office",
                    "cycle": cycle,
                    "message_id": meta.get("message_id"),
                    "thread_id": meta.get("thread_id"),
                    "internal_date": meta.get("internal_date"),
                    "from": from_addr,
                    "subject": subject,
                    "office": office,
                    "office_inference_reason": office_reason,
                    "attachments": [],
                    "classification": classification,
                    "classification_confidence": classification_confidence,
                    "label_name": label_name,
                    "label_applied": False,
                    "dry_run": dry_run,
                    "force": force,
                    "skip_unknown": skip_unknown,
                    "decision_reason": "unknown_office",
                }
                # For skip_unknown we do NOT apply label; leave message untouched.
                logger.info(
                    "Stage v2 skip: message_id=%s office=%s reason=%s",
                    meta.get("message_id"),
                    office,
                    "unknown_office",
                )
                processed.append(record)
                continue

            attachments_records = []
            normalized_names: list[str] = []

            for idx, att in enumerate(attachments_meta, start=1):
                original_filename = att.get("filename") or ""
                mime_type = att.get("mime_type") or "application/octet-stream"
                attachment_id = att.get("attachment_id")
                size = att.get("size") or 0
                attachment_office, attachment_office_reason = attachment_office_inferences[idx - 1]
                attachment_office_dir = out_root_path / cycle / "originals" / attachment_office
                logger.info(
                    "Stage v2 attachment: message_id=%s filename=%s office=%s reason=%s",
                    meta.get("message_id"),
                    original_filename,
                    attachment_office,
                    attachment_office_reason,
                )

                # Skip parts without downloadable attachment id
                if not attachment_id:
                    continue

                if skip_unknown and attachment_office == "unknown":
                    continue

                # ---- Extension resolution ----
                ext = ""
                if original_filename:
                    _, dot, rest = original_filename.rpartition(".")
                    if dot:
                        ext = "." + rest

                if not ext:
                    guessed = mimetypes.guess_extension(mime_type or "")
                    if guessed:
                        ext = guessed

                if not ext:
                    ext = ".bin"

                # ---- Deterministic canonical filename ----
                if len(attachments_meta) == 1:
                    base_name = attachment_office
                else:
                    base_name = f"{attachment_office}-{idx}"

                normalized_filename = f"{base_name}{ext}"
                target_path = attachment_office_dir / normalized_filename

                # ---- Write behavior ----
                if not dry_run:
                    data = EmailService._download_attachment_bytes(
                        service=service,
                        message_id=meta.get("message_id"),
                        attachment_id=attachment_id,
                    )

                    if force:
                        # Overwrite deterministic filename (no version creep)
                        final_path = EmailService._write_overwrite(target_path, data)
                        saved_path = str(final_path)
                    else:
                        # Collision-safe unique filenames
                        final_path = EmailService._safe_write_unique(target_path, data)
                        normalized_filename = final_path.name
                        saved_path = str(final_path)

                    saved_attachments_count += 1
                else:
                    # Dry-run: simulate deterministic path (no unique suffix)
                    final_path = target_path
                    saved_path = str(final_path)

                normalized_names.append(normalized_filename)

                attachments_records.append({
                    "original_filename": original_filename,
                    "normalized_filename": normalized_filename,
                    "office": attachment_office,
                    "office_inference_reason": attachment_office_reason,
                    "mime_type": mime_type,
                    "size": size,
                    "saved_path": saved_path,
                })

            label_applied = False
            if (not dry_run) and label_id:
                label_applied = EmailService._apply_label(service=service, message_id=mid, label_id=label_id)
                if label_applied:
                    labeled_count += 1

            record = {
                "timestamp": EmailService._now_iso(),
                "action": "stage_attachments_v2",
                "status": "ok",
                "cycle": cycle,
                "message_id": meta.get("message_id"),
                "thread_id": meta.get("thread_id"),
                "internal_date": meta.get("internal_date"),
                "from": from_addr,
                "subject": subject,
                "office": office,
                "office_inference_reason": office_reason,
                "attachments": attachments_records,
                "classification": classification,
                "classification_confidence": classification_confidence,
                "label_name": label_name,
                "label_applied": label_applied,
                "dry_run": dry_run,
                "force": force,
            }
            logger.info(
                "Stage v2 classify: message_id=%s office=%s reason=%s attachments=%d",
                meta.get("message_id"),
                office,
                office_reason,
                len(attachments_records),
            )

            if not dry_run:
                EmailService._append_jsonl(path=log_path, obj=record)

            processed.append(record)

        return {
            "success": True,
            "status": "completed",
            "action": "stage_attachments_v2",
            "cycle": cycle,
            "out_root": str(out_root_path),
            "query": query,
            "max_results": max_results,
            "label_name": label_name,
            "label_id": label_id,
            "dry_run": dry_run,
            "processed_count": len(processed),
            "skipped_already_labeled": skipped_already_labeled,
            "saved_attachments_count": saved_attachments_count,
            "processed": processed,
            "candidates_count": candidates_count,
            "force": force,
        }

    # -----------------------------
    # Existing high-level methods (kept)
    # -----------------------------

    @staticmethod
    def send_reminder(
            to: list[str],
            meeting_date: str,
            meeting_type: str,
            dry_run: bool = False,
    ) -> dict[str, Any]:
        logger.info(f"Preparing reminder email: meeting_date={meeting_date}, meeting_type={meeting_type}")
        logger.info(f"Recipients: {', '.join(to) if to else 'no recipients'}")

        reminder_result = {
            "success": False,
            "message": "",
            "status": "preparing",
            "email_type": "reminder",
            "meeting_date": meeting_date,
            "meeting_type": meeting_type,
        }

        subject = f"Reminder: {meeting_type.title()} Meeting on {meeting_date}"
        body = (
            "Dear Council Member,\n\n"
            f"This is a friendly reminder that the {meeting_type} meeting is scheduled for {meeting_date}.\n\n"
            "Best regards,\nCouncil Secretary"
        )

        attachments: list[str] = []

        agenda_path = f"src/scribe/output/agendas/agenda_{meeting_type}.pdf"
        if os.path.exists(agenda_path) and os.access(agenda_path, os.R_OK):
            attachments.append(agenda_path)
            reminder_result["agenda_attached"] = True
            reminder_result["agenda_path"] = agenda_path
        else:
            reminder_result["agenda_attached"] = False
            reminder_result["agenda_path"] = ""

        if not to:
            error_message = "No recipients specified for reminder email"
            logger.error(error_message)
            reminder_result.update({"message": error_message, "status": "failed", "error": error_message})
            return reminder_result

        email_result = EmailService._send_email(to, subject, body, attachments, dry_run=dry_run)
        reminder_result.update(email_result)
        return reminder_result

    @staticmethod
    def distribute_minutes(
            to: list[str],
            minutes_file: str,
            meeting_date: str,
            meeting_type: str,
            dry_run: bool = False,
    ) -> dict[str, Any]:
        logger.info(f"Preparing minutes distribution: meeting_date={meeting_date}, meeting_type={meeting_type}")
        logger.info(f"Recipients: {', '.join(to) if to else 'no recipients'}")
        logger.info(f"Minutes file: {minutes_file}")

        minutes_result = {
            "success": False,
            "message": "",
            "status": "preparing",
            "email_type": "minutes_distribution",
            "meeting_date": meeting_date,
            "meeting_type": meeting_type,
            "minutes_file": minutes_file,
        }

        subject = f"Draft Minutes: {meeting_type.title()} Meeting on {meeting_date} - Review Requested"
        body = (
            "Dear Council Officer,\n\n"
            f"Attached are the draft minutes from the {meeting_type} meeting held on {meeting_date}.\n\n"
            "Best regards,\nCouncil Secretary"
        )

        if not os.path.exists(minutes_file):
            error_message = f"Minutes file not found: path='{minutes_file}'"
            logger.error(error_message)
            minutes_result.update({
                "message": error_message,
                "status": "failed",
                "error": error_message,
                "minutes_found": False,
            })
            return minutes_result

        minutes_result["minutes_found"] = True
        email_result = EmailService._send_email(to, subject, body, [minutes_file], dry_run=dry_run)
        minutes_result.update(email_result)
        return minutes_result


if __name__ == "__main__":
    # Minimal manual test: ingestion dry-run (no labels/logging written)
    # Note: _run is part of BaseTool interface, not a protected method
    test_result = EmailService.ingest_unread_inbox_v1(max_results=5, dry_run=True)
    print(test_result)
