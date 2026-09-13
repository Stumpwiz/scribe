"""
Meeting notification tool for the Scribe project.

This module provides the MeetingNotificationTool class for creating and saving
meeting notification drafts to be sent to council members and committee chairs.
"""

from typing import Optional, List, Dict, Any
import os
import json
from pathlib import Path
from datetime import datetime, date
import re
from crewai.tools import BaseTool
from jinja2 import Environment, FileSystemLoader, select_autoescape


def get_meeting_type_from_date(meeting_date: date) -> str:
    """
    Determine the meeting type based on the month of the given date.
    
    Args:
        meeting_date (date): The date of the meeting
        
    Returns:
        str: The meeting type ('regular', 'open', or 'association')
        
    Raises:
        TypeError: If meeting_date is not a datetime.date object
    """
    # Validate that meeting_date is a date object
    if not isinstance(meeting_date, date):
        raise TypeError("meeting_date must be a datetime.date object")

    # Extract the month
    month = meeting_date.month

    # Determine the meeting type based on the month
    if month in [1, 2, 4, 5, 7, 8, 10, 11]:
        return "regular"
    elif month in [3, 6, 9]:
        return "open"
    elif month == 12:
        return "association"
    else:
        # This should never happen with valid dates, but included for completeness
        raise ValueError(f"Invalid month: {month}")


class MeetingNotificationTool(BaseTool):
    """
    Tool for creating and saving meeting notification drafts.
    
    This tool allows agents to create meeting notification drafts and save them
    to the output/reminders/ directory for review before sending.
    """

    name: str = "MeetingNotificationTool"
    description: str = "Tool for creating and saving meeting notification drafts"

    def render_email_from_template(self,
                                   meeting_date: str,
                                   meeting_type: str,
                                   meeting_time: str = "2:00 PM",
                                   venue: str = "McAuley Conference Room",
                                   old_business_items: Optional[List[str]] = None,
                                   new_business_items: Optional[List[str]] = None) -> Dict[str, str]:
        """
        Render meeting reminder email from Jinja2 template.

        Args:
            meeting_date: Date of the meeting (e.g., "February 5, 2026")
            meeting_type: Type of meeting ('regular', 'open', or 'association')
            meeting_time: Time of the meeting (default: "2:00 PM")
            venue: Location of the meeting (default: "McAuley Conference Room")
            old_business_items: List of old business agenda items
            new_business_items: List of new business agenda items

        Returns:
            Dict with 'subject' and 'body' keys containing the rendered email
        """
        # Get templates directory
        templates_dir = Path(__file__).resolve().parent.parent / "assets" / "templates"

        # Set up Jinja2 environment
        env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True
        )

        # Load the template
        template = env.get_template("email_reminder.txt.j2")

        # Render the template
        rendered = template.render(
            meetingDate=meeting_date,
            meetingType=meeting_type,
            meetingTime=meeting_time,
            venue=venue,
            oldBusinessItems=old_business_items or [],
            newBusinessItems=new_business_items or [],
            reportSubmissionEmail=os.getenv("REPORT_SUBMISSION_EMAIL") or os.getenv("EMAIL_FROM") or "reports@example.com",
        )

        # Split subject from body when template starts with "Subject: ...".
        # If not present, use a deterministic fallback subject.
        lines = rendered.splitlines()
        first_non_empty_idx = next((i for i, line in enumerate(lines) if line.strip()), None)
        subject = f"Report Request: {meeting_type.upper()} Residents Council Meeting - {meeting_date}"
        body = rendered.strip()
        if first_non_empty_idx is not None:
            first_line = lines[first_non_empty_idx].strip()
            if first_line.lower().startswith("subject:"):
                subject = first_line.split(":", 1)[1].strip() or subject
                body = "\n".join(lines[first_non_empty_idx + 1:]).strip()

        return {
            "subject": subject,
            "body": body
        }

    def _redact_email(self, email: str) -> str:
        if "@" not in email:
            return "***"
        local, domain = email.split("@", 1)
        if not local:
            return f"***@{domain}"
        return f"{local[0]}***@{domain}"

    def _write_recipient_audit(
            self,
            meeting_date: Optional[str],
            meeting_type: str,
            officer_emails: List[str],
            chair_emails: List[str],
            recipients: List[str],
            diagnostics: List[Dict[str, object]],
            warnings: List[str],
            redact_emails: bool,
    ) -> Optional[str]:
        reminders_dir = Path(__file__).parent.parent / "output" / "reminders"
        reminders_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_date = re.sub(r"[^\w\-]", "_", meeting_date or "unknown-date")
        file_path = reminders_dir / f"{timestamp}_recipients_{safe_date}.json"

        def _maybe_redact(values: List[str]) -> List[str]:
            return [self._redact_email(v) for v in values] if redact_emails else values

        payload = {
            "meeting_date": meeting_date,
            "meeting_type": meeting_type,
            "pii_redacted": redact_emails,
            "officer_emails": _maybe_redact(officer_emails),
            "chair_emails": _maybe_redact(chair_emails),
            "recipients": _maybe_redact(recipients),
            "diagnostics": diagnostics,
            "warnings": warnings,
        }

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, sort_keys=True)
            return str(file_path)
        except Exception:
            return None

    def get_recipients(self, meeting_type: str, meeting_date: Optional[str] = None, audit: bool = True) -> List[str]:
        """
        Get the list of email recipients based on meeting type.

        Business Rules:
        - Council officers receive emails for ALL meeting types
        - Committee chairs receive emails ONLY for 'open' and 'association' meeting types

        Args:
            meeting_type (str): Type of meeting ('regular', 'open', or 'association')

        Returns:
            List[str]: A deduplicated list of email addresses
        """
        import logging
        logger = logging.getLogger(__name__)

        # Use database query tool to get recipients
        from scribe.tools.database_query_tool import DatabaseQueryTool
        db_tool = DatabaseQueryTool()

        # Initialize the list of email addresses
        emails = []
        officer_emails: List[str] = []
        chair_emails: List[str] = []
        audit_warnings: List[str] = []
        diagnostics: List[Dict[str, object]] = []

        # Always load Clerk "Residents Council Officers" mailing list from database
        try:
            council_officers = db_tool.get_residents_council_officers_mailing_list()
            officer_emails = council_officers
            emails.extend(officer_emails)
            logger.info(
                "Loaded %d email(s) from Clerk mailing list 'Residents Council Officers'",
                len(council_officers),
            )
        except Exception as e:
            logger.error(f"Error loading Residents Council Officers from database: {str(e)}")
            audit_warnings.append(f"residents council officers query failed: {str(e)}")

        # For 'open' or 'association' meetings, also include committee chairs
        if meeting_type.lower() in ["open", "association"]:
            try:
                committee_chairs = db_tool.get_committee_chairs()
                chair_emails = committee_chairs
                emails.extend(chair_emails)
                diagnostics = getattr(db_tool, "last_committee_chair_diagnostics", []) or []
                audit_warnings.extend(getattr(db_tool, "last_committee_chair_warnings", []) or [])
                logger.info(f"Loaded {len(committee_chairs)} committee chair email(s) from database")
            except Exception as e:
                logger.error(f"Error loading committee chairs from database: {str(e)}")
                audit_warnings.append(f"committee chairs db query failed: {str(e)}")

        # Deduplicate the list of emails
        emails = list(set(emails))

        # If no recipients were found, use a safe fallback (configurable via env)
        fallback_email = os.getenv("DEFAULT_FALLBACK_EMAIL", "test@example.com")
        if not emails:
            logger.warning(
                f"No recipients found for meeting type '{meeting_type}'. Using fallback email: {fallback_email}")
            emails = [fallback_email]
        else:
            logger.info(f"Found {len(emails)} recipient(s) for meeting type '{meeting_type}'")

        if audit and meeting_date:
            redact = not logger.isEnabledFor(logging.DEBUG)
            audit_path = self._write_recipient_audit(
                meeting_date=meeting_date,
                meeting_type=meeting_type,
                officer_emails=officer_emails,
                chair_emails=chair_emails,
                recipients=emails,
                diagnostics=diagnostics,
                warnings=audit_warnings,
                redact_emails=redact,
            )
            if audit_path:
                logger.info(f"Recipient audit saved: {audit_path}")

        return emails

    def _run(self,
             content: Optional[str] = None,
             meeting_date: Optional[str] = None,
             meeting_type: Optional[str] = None,
             meeting_time: Optional[str] = "2:00 PM",
             location: Optional[str] = None,
             old_business_items: Optional[List[str]] = None,
             new_business_items: Optional[List[str]] = None,
             filename_hint: Optional[str] = None,
             include_agenda_template: bool = True,
             attachment_path: Optional[str] = None,
             agenda_result: Optional[Dict[str, Any]] = None,
             dry_run: bool = False,
             **kwargs) -> Dict[str, Any]:
        """
        Create and save a meeting notification draft.

        Args:
            content (Optional[str]): The text content of the notification (if None, will use template)
            meeting_date (Optional[str]): Date of the meeting
            meeting_type (Optional[str]): Type of meeting ('regular', 'open', 'association')
            meeting_time (Optional[str]): Time of the meeting (default: "2:00 PM")
            location (Optional[str]): Location of the meeting (if None, determined by meeting_type)
            old_business_items (Optional[List[str]]): Old business agenda items
            new_business_items (Optional[List[str]]): New business agenda items
            filename_hint (Optional[str]): A short string to use in naming the file
            include_agenda_template (bool): Whether to include a reference to the agenda template
            attachment_path (Optional[str]): Path to a PDF file to attach to the email
            agenda_result (Optional[Dict[str, Any]]): Result from MeetingAgendaGeneratorTool

        Returns:
            Dict with status, draft_path, and email send metadata (if sent).
        """
        import logging
        logger = logging.getLogger(__name__)

        # Determine location based on meeting_type if not provided
        if not location and meeting_type:
            if meeting_type.lower() == "open":
                location = "PAC"
            else:
                location = "McAuley Conference Room"

        explicit_subject = kwargs.get("subject")

        # If content not provided but meeting details are, render from template
        if not content and meeting_date and meeting_type:
            logger.info(f"Rendering email from template for {meeting_type} meeting on {meeting_date}")
            email = self.render_email_from_template(
                meeting_date=meeting_date,
                meeting_type=meeting_type,
                meeting_time=meeting_time or "2:00 PM",
                venue=location or "McAuley Conference Room",
                old_business_items=old_business_items,
                new_business_items=new_business_items
            )
            content = email["body"]
            subject = explicit_subject or email["subject"]
            logger.info(f"Rendered email with subject: {subject}")
        elif not content:
            logger.warning("No content provided and insufficient template parameters")
            content = "Meeting notification content not provided"
            subject = explicit_subject or (f"Meeting Reminder: {meeting_date}" if meeting_date else "Meeting Reminder")
        else:
            subject = explicit_subject or (f"Meeting Reminder: {meeting_date}" if meeting_date else "Meeting Reminder")

        # Extract PDF path from agenda_result if provided
        agenda_attachment = None
        if agenda_result and isinstance(agenda_result, dict) and agenda_result.get("success", False):
            agenda_attachment = agenda_result.get("pdfPath")
            if agenda_attachment:
                if os.path.exists(agenda_attachment):
                    logger.info(f"Found valid agenda PDF attachment from agenda_result: {agenda_attachment}")
                else:
                    logger.warning(f"Agenda PDF path from agenda_result does not exist: {agenda_attachment}")
                    agenda_attachment = None
            else:
                logger.warning("Agenda result was successful but no PDF path was provided")
        else:
            logger.info("No valid agenda_result provided or agenda generation was not successful")

        # Use explicitly provided attachment_path as fallback if agenda_attachment is not available
        if not agenda_attachment and attachment_path:
            if os.path.exists(attachment_path):
                agenda_attachment = attachment_path
                logger.info(f"Using fallback attachment path: {attachment_path}")
            else:
                logger.warning(f"Fallback attachment path does not exist: {attachment_path}")

        # Update content with attachment information (for email preview only)
        if agenda_attachment:
            logger.info(f"Attaching agenda PDF: {agenda_attachment}")
        else:
            logger.info("No agenda PDF attachment available")

        # Get recipients for the email (use env-configurable safe fallback if not provided)
        env_fallback_email = os.getenv("DEFAULT_FALLBACK_EMAIL", "test@example.com")
        recipients = kwargs.get("recipients", [env_fallback_email])
        logger.info("Sending meeting notification: meeting_type=%s, meeting_date=%s, recipients=%d",
                    meeting_type, meeting_date, len(recipients))
        # subject already set above when rendering from template
        email_body = content

        # Prepare email arguments
        attachments = [agenda_attachment] if agenda_attachment else []
        email_args = {
            "action": "send",
            "to": recipients,
            "subject": subject,
            "body": email_body,
            "attachments": attachments
        }

        # Log attachment status
        if attachments:
            logger.info(f"Email will include attachment: {attachments[0]}")
        else:
            logger.info("Email will be sent without attachments")

        draft_path = self._save_notification(content, filename_hint)

        # For dry runs, skip Gmail API entirely after rendering/saving.
        if dry_run:
            logger.info("Dry run requested; skipping email send.")
            return {
                "success": True,
                "status": "dry_run",
                "message": "Dry run complete. No email sent.",
                "draft_path": draft_path,
                "recipient_count": len(recipients),
                "attachment_path": agenda_attachment or "",
                "recipients": recipients,
            }

        # Send the email using EmailService
        from scribe.tools.email_service import EmailService
        email_service = EmailService()

        # Call _run method directly with unpacked arguments instead of passing a dictionary
        result = email_service._run(
            action="send",
            to=recipients,
            subject=subject,
            body=email_body,
            attachments=attachments,
            dry_run=dry_run,
        )

        logger.info(f"Email sent. Result: {result}")

        response = {
            "success": bool(result.get("success")),
            "status": result.get("status", "unknown"),
            "message": result.get("message", ""),
            "message_id": result.get("message_id", ""),
            "draft_path": draft_path,
            "recipient_count": len(recipients),
            "attachment_path": agenda_attachment or "",
            "recipients": recipients,
        }
        if result.get("error"):
            response["error"] = result.get("error")
        return response

    def _save_notification(self,
                           content: str,
                           filename_hint: Optional[str] = None) -> str:
        """
        Save notification draft to a file in the output/reminders/ directory.
        
        Args:
            content (str): The text content to save to the file
            filename_hint (Optional[str]): A short string to use in naming the file
            
        Returns:
            str: The full path to the created draft file
        """
        # Create the output/reminders directory if it doesn't exist
        reminders_dir = Path(__file__).parent.parent / "output" / "reminders"
        reminders_dir.mkdir(parents=True, exist_ok=True)

        # Generate a timestamp for the filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Process the filename_hint if provided
        if filename_hint:
            # Replace spaces and special characters with underscores
            safe_hint = re.sub(r'[^\w\-]', '_', filename_hint)
            filename = f"{timestamp}_{safe_hint}.txt"
        else:
            filename = f"{timestamp}_meeting_notification.txt"

        # Create the full file path
        file_path = reminders_dir / filename

        # Write the content to the file
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return str(file_path)
        except Exception as e:
            return f"Error saving meeting notification draft: {str(e)}"
