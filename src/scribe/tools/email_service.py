"""
Email service tool for the Scribe project.

This module provides the EmailService class for sending and receiving emails
using the Gmail API.
"""

from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
import os
import json
import logging
import mimetypes
import base64
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from pathlib import Path
from crewai.tools import BaseTool
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from src.scribe.google_auth.google_auth_helper import get_google_credentials

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get sender email from environment variable - this will be None if not set
DEFAULT_SENDER = os.getenv("EMAIL_FROM")  # Must be set in environment variables


class EmailServiceSchema(BaseModel):
    action: str
    to: Optional[List[str]] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    attachments: Optional[List[str]] = Field(default_factory=list)


class EmailService(BaseTool):
    """
    Tool for sending and receiving emails.
    
    This tool allows agents to send notifications and reminders, receive and process
    emails, and distribute draft minutes and other documents.
    """

    name: str = "Email Service"
    description: str = "Tool for sending and receiving emails"
    args_schema = EmailServiceSchema

    def _validate_email(self, email: str) -> bool:
        """
        Validate that a string is a syntactically valid email address.
        
        Args:
            email (str): The email address to validate
            
        Returns:
            bool: True if the email is valid, False otherwise
        """
        import re
        # Basic email validation pattern
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _run(
            self,
            action: str = "send",
            to: Optional[List[str]] = None,
            subject: Optional[str] = None,
            body: Optional[str] = None,
            attachments: Optional[List[str]] = None,
            **kwargs
    ) -> Dict[str, Any]:
        """
        Run the email service.
        
        Args:
            action (str): The action to perform ("send", "receive", "check", "search")
            to (Optional[List[str]]): List of recipient email addresses
            subject (Optional[str]): Email subject line
            body (Optional[str]): Email body content
            attachments (Optional[List[str]]): List of file paths to attach
            
        Returns:
            Dict[str, Any]: Result of the email operation containing:
                - success (bool): Whether the operation was successful
                - message (str): Human-readable message about the operation
                - status (str): Status of the operation (e.g., "sent", "failed")
                - and other fields depending on the action
        """
        # Ensure attachments is always a list
        attachments: List[str] = attachments if attachments is not None else []
        
        # Initialize basic result structure
        result = {
            "success": False,
            "message": "",
            "status": "unknown"
        }
        
        if action == "send":
            # Validate email addresses
            if to:
                invalid_emails = [email for email in to if not self._validate_email(email)]
                if invalid_emails:
                    error_msg = f"Invalid email address(es): {', '.join(invalid_emails)}"
                    result.update({
                        "message": error_msg,
                        "status": "failed",
                        "error": error_msg,
                        "recipients": to,
                        "invalid_emails": invalid_emails
                    })
                    return result
            
            # Send email and return detailed result
            return self._send_email(to, subject, body, attachments)
        elif action == "receive":
            # For now, wrap the string result in a dictionary
            msg = self._receive_emails()
            result.update({
                "success": True,
                "message": msg,
                "status": "completed"
            })
            return result
        elif action == "check":
            # For now, wrap the string result in a dictionary
            msg = self._check_inbox()
            result.update({
                "success": True,
                "message": msg,
                "status": "completed"
            })
            return result
        elif action == "search":
            query = kwargs.get("query", "")
            # For now, wrap the string result in a dictionary
            msg = self._search_emails(query)
            result.update({
                "success": True,
                "message": msg,
                "status": "completed",
                "query": query
            })
            return result
        else:
            error_msg = f"Unknown action: {action}"
            result.update({
                "message": error_msg,
                "status": "failed",
                "error": error_msg
            })
            return result

    def _send_email(self,
                    to: Optional[List[str]],
                    subject: Optional[str],
                    body: Optional[str],
                    attachments: Optional[List[str]],
                    dry_run: bool = False) -> Dict[str, Any]:
        """
        Send an email to the specified recipients using Gmail API.
        
        Args:
            to (Optional[List[str]]): List of recipient email addresses
            subject (Optional[str]): Email subject line
            body (Optional[str]): Email body content
            attachments (Optional[List[str]]): List of file paths to attach
            dry_run (bool): If True, don't actually send the email, just log what would be sent
            
        Returns:
            Dict[str, Any]: A dictionary containing:
                - success (bool): Whether the operation was successful
                - message (str): Human-readable message about the operation
                - recipients (List[str]): List of recipients
                - subject (str): Email subject
                - status (str): Status of the operation (e.g., "sent", "failed", "dry_run")
                - timestamp (str): Timestamp of the operation
                - recipient_statuses (List[Dict]): Status for each recipient (if available)
                - error (str): Error message (if any)
                - traceback (str): Full exception traceback (if any)
        """
        # Format recipients for logging
        recipients_str = ", ".join(to) if to else "no recipients"
        attachment_count = len(attachments) if attachments else 0
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Initialize result dictionary
        result = {
            "success": False,
            "message": "",
            "recipients": to or [],
            "subject": subject or "",
            "status": "unknown",
            "timestamp": timestamp,
            "recipient_statuses": [],
            "error": "",
            "traceback": ""
        }

        # Check if EMAIL_FROM is set
        if DEFAULT_SENDER is None:
            error_message = "EMAIL_FROM environment variable is not set. Please set EMAIL_FROM in your .env file."
            logger.error(error_message)
            
            # Update result for missing EMAIL_FROM
            result.update({
                "message": error_message,
                "status": "failed",
                "error": error_message
            })
            
            return result

        # If dry run, just log what would be sent
        if dry_run:
            log_message = f"[DRY RUN] Email would be sent at {timestamp}:\nTo: {recipients_str}\nSubject: {subject}\nBody: {body}\nAttachments: {attachment_count}"
            logger.info(log_message)
            
            # Update result for dry run
            result.update({
                "success": True,
                "message": log_message,
                "status": "dry_run",
                "recipient_statuses": [{"email": email, "status": "would_send"} for email in (to or [])]
            })
            
            return result

        try:
            # Get Google credentials
            creds = get_google_credentials()
            if not creds:
                error_message = "Failed to get Google credentials. Check your credentials.json file."
                logger.error(error_message)
                
                # Update result for credentials error
                result.update({
                    "message": error_message,
                    "status": "failed",
                    "error": error_message
                })
                
                return result
                
            # Build the Gmail service
            service = build('gmail', 'v1', credentials=creds)
            
            # Create a multipart message
            msg = MIMEMultipart()
            msg['From'] = DEFAULT_SENDER
            msg['Subject'] = subject or ""
            
            # Add recipients
            if to:
                msg['To'] = ", ".join(to)
            else:
                logger.warning("No recipients specified")
                error_message = "Error: No recipients specified"
                result.update({
                    "message": error_message,
                    "status": "failed",
                    "error": error_message
                })
                return result
            
            # Attach the body as plain text
            if body:
                msg.attach(MIMEText(body, 'plain'))
            
            # Add attachments if any
            if attachments and len(attachments) > 0:
                for attachment_path in attachments:
                    if not os.path.exists(attachment_path):
                        logger.warning(f"Attachment file not found: {attachment_path}")
                        continue

                    # Get file content and type
                    with open(attachment_path, 'rb') as f:
                        file_content = f.read()

                    # Determine file type
                    content_type, _ = mimetypes.guess_type(attachment_path)
                    if not content_type:
                        content_type = 'application/octet-stream'

                    # Get file name - use a more descriptive name for agenda PDFs
                    file_name = os.path.basename(attachment_path)
                    if file_name.startswith("agenda_") and file_name.endswith(".pdf"):
                        # Extract meeting date from filename (agenda_YYYY-MM-DD_type.pdf)
                        parts = file_name.split("_")
                        if len(parts) >= 2:
                            meeting_date = parts[1]
                            file_name = f"Agenda_{meeting_date}.pdf"

                    # Create attachment part
                    part = MIMEApplication(file_content, Name=file_name)
                    part['Content-Disposition'] = f'attachment; filename="{file_name}"'
                    
                    # Add attachment to message
                    msg.attach(part)

            # Encode the message
            raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            
            # Send the message using Gmail API
            message = service.users().messages().send(
                userId="me",
                body={"raw": raw_message}
            ).execute()

            # Log success with detailed information
            message_id = message.get("id", "unknown")
            
            # Create detailed log message
            log_message = f"Email sent at {timestamp} (Message ID: {message_id}):"
            logger.info(log_message)
            logger.info(f"Recipients: {recipients_str}")
            logger.info(f"Subject: {subject}")
            
            # Log attachment details if any
            if attachments and len(attachments) > 0:
                for attachment_path in attachments:
                    file_name = os.path.basename(attachment_path)
                    logger.info(f"Attachment: filename='{file_name}', path='{attachment_path}'")
            else:
                logger.info("Attachments: none")
            
            # Update result for successful send
            result.update({
                "success": True,
                "message": log_message,
                "status": "sent",
                "message_id": message_id,
                "recipient_statuses": [{"email": email, "status": "sent"} for email in (to or [])]
            })
            
            return result

        except HttpError as e:
            # Get full traceback
            tb_str = traceback.format_exc()
            error_message = f"Gmail API error: {str(e)}"
            
            # Log detailed error information
            logger.error(f"Email send failed: {error_message}")
            logger.error(f"Attempted to send to: {recipients_str}")
            logger.error(f"Subject: {subject}")
            if attachments and len(attachments) > 0:
                for attachment_path in attachments:
                    file_name = os.path.basename(attachment_path)
                    logger.error(f"Attachment: filename='{file_name}', path='{attachment_path}'")
            logger.error(f"Error details: {str(e)}")
            logger.error(f"Traceback: {tb_str}")
            
            # Update result for error
            result.update({
                "message": error_message,
                "status": "failed",
                "error": str(e),
                "traceback": tb_str,
                "recipient_statuses": [{"email": email, "status": "failed", "error": str(e)} for email in (to or [])]
            })
            
            return result
            
        except Exception as e:
            # Get full traceback
            tb_str = traceback.format_exc()
            error_message = f"Error sending email: {str(e)}"
            
            # Log detailed error information
            logger.error(f"Email send failed: {error_message}")
            logger.error(f"Attempted to send to: {recipients_str}")
            logger.error(f"Subject: {subject}")
            if attachments and len(attachments) > 0:
                for attachment_path in attachments:
                    file_name = os.path.basename(attachment_path)
                    logger.error(f"Attachment: filename='{file_name}', path='{attachment_path}'")
            logger.error(f"Error details: {str(e)}")
            logger.error(f"Traceback: {tb_str}")
            
            # Update result for error
            result.update({
                "message": error_message,
                "status": "failed",
                "error": str(e),
                "traceback": tb_str,
                "recipient_statuses": [{"email": email, "status": "failed", "error": str(e)} for email in (to or [])]
            })
            
            return result

    def _receive_emails(self) -> str:
        """
        Receive new emails from the inbox.
        
        Returns:
            str: List of new emails
        """
        # In a real implementation, this would connect to an email server
        # For now, we'll just return a placeholder message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"Checked for new emails at {timestamp}. No new emails found."

    def _check_inbox(self) -> str:
        """
        Check the inbox status.
        
        Returns:
            str: Inbox status
        """
        # In a real implementation, this would connect to an email server
        # For now, we'll just return a placeholder message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"Inbox status as of {timestamp}: 0 unread messages, 0 total messages."

    def _search_emails(self, query: str) -> str:
        """
        Search emails using the specified query.
        
        Args:
            query (str): Search query
            
        Returns:
            str: Search results
        """
        # In a real implementation, this would search emails on the server
        # For now, we'll just return a placeholder message
        return f"Search for '{query}' returned 0 results."
        
    def _archive_email_and_attachments(self, 
                                      email_body: str, 
                                      meeting_date: str,
                                      meeting_type: str,
                                      attachments: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Archive the email body and attachments to the reminders_archive directory.
        
        Args:
            email_body (str): The body of the email to archive
            meeting_date (str): Date of the meeting (YYYY-MM-DD)
            meeting_type (str): Type of meeting (regular, open, association, etc.)
            attachments (Optional[List[str]]): List of attachment file paths
            
        Returns:
            Dict[str, Any]: A dictionary containing:
                - success (bool): Whether the archiving was successful
                - archived_files (List[str]): List of archived file paths
                - error (str): Error message if any
        """
        result = {
            "success": True,
            "archived_files": [],
            "error": ""
        }
        
        try:
            # Create the archive directory if it doesn't exist
            archive_dir = Path("instance/reminders_archive")
            archive_dir.mkdir(parents=True, exist_ok=True)
            
            # Create filename prefix with meeting date and type
            filename_prefix = f"{meeting_date}_{meeting_type}"
            
            # Archive the email body
            email_filename = f"{filename_prefix}_email.txt"
            email_path = archive_dir / email_filename
            
            with open(email_path, 'w', encoding='utf-8') as f:
                f.write(email_body)
                
            logger.info(f"Archived email body to {email_path}")
            result["archived_files"].append(str(email_path))
            
            # Archive attachments if any
            if attachments:
                for attachment_path in attachments:
                    if not os.path.exists(attachment_path):
                        logger.warning(f"Attachment file not found for archiving: {attachment_path}")
                        continue
                        
                    # Get the file extension
                    _, ext = os.path.splitext(attachment_path)
                    
                    # If it's a PDF agenda, use a specific name
                    if ext.lower() == '.pdf' and 'agenda' in attachment_path.lower():
                        attachment_filename = f"{filename_prefix}_agenda.pdf"
                        attachment_archive_path = archive_dir / attachment_filename
                        
                        # Copy the file
                        with open(attachment_path, 'rb') as src, open(attachment_archive_path, 'wb') as dst:
                            dst.write(src.read())
                            
                        logger.info(f"Archived agenda PDF to {attachment_archive_path}")
                        result["archived_files"].append(str(attachment_archive_path))
            
            return result
            
        except Exception as e:
            error_message = f"Error archiving email and attachments: {str(e)}"
            logger.error(error_message)
            result["success"] = False
            result["error"] = error_message
            return result

    def send_reminder(self,
                      to: List[str],
                      meeting_date: str,
                      meeting_type: str,
                      context: Optional[Dict[str, Any]] = None,
                      dry_run: bool = False) -> Dict[str, Any]:
        """
        Send a meeting reminder email.
        
        Args:
            to (List[str]): List of recipient email addresses
            meeting_date (str): Date of the meeting (YYYY-MM-DD)
            meeting_type (str): Type of meeting (council, committee, etc.)
            context (Optional[Dict[str, Any]]): Additional context data including meetingDate and meetingType
            dry_run (bool): If True, don't actually send the email, just log what would be sent
            
        Returns:
            Dict[str, Any]: Result of the send operation containing:
                - success (bool): Whether the operation was successful
                - message (str): Human-readable message about the operation
                - status (str): Status of the operation (e.g., "sent", "failed")
                - and other fields with detailed information
        """
        # Log reminder email preparation
        recipients_str = ", ".join(to) if to else "no recipients"
        logger.info(f"Preparing reminder email: meeting_date={meeting_date}, meeting_type={meeting_type}")
        logger.info(f"Recipients: {recipients_str}")
        
        # Initialize result dictionary
        result = {
            "success": False,
            "message": "",
            "status": "preparing",
            "email_type": "reminder",
            "meeting_date": meeting_date,
            "meeting_type": meeting_type
        }
        
        subject = f"Reminder: {meeting_type.title()} Meeting on {meeting_date}"

        body = f"Dear Council Member,\n\n"
        body += f"This is a friendly reminder that the {meeting_type} meeting is scheduled for {meeting_date}.\n\n"

        body += "Best regards,\nCouncil Secretary"

        # Initialize attachments list
        attachments = []

        # Construct the agenda PDF path based on meeting type
        agenda_path = f"src/scribe/output/agendas/agenda_{meeting_type}.pdf"
        
        # Check if the agenda file exists and is readable
        try:
            if os.path.exists(agenda_path) and os.access(agenda_path, os.R_OK):
                file_size = os.path.getsize(agenda_path)
                file_size_kb = file_size / 1024
                logger.info(f"Attaching agenda PDF: path='{agenda_path}', size={file_size_kb:.2f}KB")
                attachments.append(agenda_path)
                result["agenda_attached"] = True
                result["agenda_path"] = agenda_path
            else:
                logger.warning(f"Agenda PDF not found or not readable: path='{agenda_path}'. Email will be sent without attachment.")
                # Log possible locations that were checked
                agenda_dir = os.path.dirname(agenda_path)
                if os.path.exists(agenda_dir):
                    existing_files = os.listdir(agenda_dir)
                    if existing_files:
                        logger.info(f"Available files in {agenda_dir}: {', '.join(existing_files)}")
                    else:
                        logger.info(f"Directory {agenda_dir} exists but is empty")
                else:
                    logger.warning(f"Directory {agenda_dir} does not exist")
                
                result["agenda_attached"] = False
                result["agenda_path"] = None
                result["agenda_error"] = f"Agenda PDF not found or not readable: {agenda_path}"
        except Exception as e:
            logger.warning(f"Error checking agenda PDF: {str(e)}. Email will be sent without attachment.")
            result["agenda_attached"] = False
            result["agenda_path"] = None
            result["agenda_error"] = f"Error checking agenda PDF: {str(e)}"
            
        # If context is provided, also try the old path format for backward compatibility
        if not result["agenda_attached"] and context and 'meetingDate' in context and 'meetingType' in context:
            # Construct the agenda PDF path using the old format
            agenda_date = context['meetingDate']
            agenda_type = context['meetingType']
            old_agenda_path = f"src/scribe/output/agendas/agenda_{agenda_date}_{agenda_type}.pdf"
            
            # Only try if it's different from the path we already checked
            if old_agenda_path != agenda_path:
                try:
                    if os.path.exists(old_agenda_path) and os.access(old_agenda_path, os.R_OK):
                        file_size = os.path.getsize(old_agenda_path)
                        file_size_kb = file_size / 1024
                        logger.info(f"Attaching agenda PDF (using old path format): path='{old_agenda_path}', size={file_size_kb:.2f}KB")
                        attachments.append(old_agenda_path)
                        result["agenda_attached"] = True
                        result["agenda_path"] = old_agenda_path
                except Exception as e:
                    logger.warning(f"Error checking old format agenda PDF: {str(e)}")
                    # We already have error information from the primary path check, so no need to update result

        # Validate recipient email addresses
        if not to or len(to) == 0:
            error_message = "No recipients specified for reminder email"
            logger.error(error_message)
            
            result.update({
                "message": error_message,
                "status": "failed",
                "error": error_message
            })
            
            return result

        # Send the email
        email_result = self._send_email(to, subject, body, attachments, dry_run=dry_run)
        
        # Merge the email result with our result
        result.update(email_result)
        
        # Archive the email and attachments if sending was successful and not a dry run
        if result["success"] and result["status"] == "sent" and not dry_run:
            archive_result = self._archive_email_and_attachments(
                email_body=body,
                meeting_date=meeting_date,
                meeting_type=meeting_type,
                attachments=attachments
            )
            
            # Add archive information to the result
            result["archive_success"] = archive_result["success"]
            result["archived_files"] = archive_result["archived_files"]
            if not archive_result["success"]:
                result["archive_error"] = archive_result["error"]
        
        return result

    def distribute_minutes(self,
                           to: List[str],
                           minutes_file: str,
                           meeting_date: str,
                           meeting_type: str,
                           dry_run: bool = False) -> Dict[str, Any]:
        """
        Distribute meeting minutes for review.
        
        Args:
            to (List[str]): List of recipient email addresses
            minutes_file (str): Path to the minutes file
            meeting_date (str): Date of the meeting (YYYY-MM-DD)
            meeting_type (str): Type of meeting (council, committee, etc.)
            dry_run (bool): If True, don't actually send the email, just log what would be sent
            
        Returns:
            Dict[str, Any]: Result of the send operation containing:
                - success (bool): Whether the operation was successful
                - message (str): Human-readable message about the operation
                - status (str): Status of the operation (e.g., "sent", "failed")
                - and other fields with detailed information
        """
        # Log minutes distribution preparation
        recipients_str = ", ".join(to) if to else "no recipients"
        logger.info(f"Preparing minutes distribution: meeting_date={meeting_date}, meeting_type={meeting_type}")
        logger.info(f"Recipients: {recipients_str}")
        logger.info(f"Minutes file: {minutes_file}")
        
        # Initialize result dictionary
        result = {
            "success": False,
            "message": "",
            "status": "preparing",
            "email_type": "minutes_distribution",
            "meeting_date": meeting_date,
            "meeting_type": meeting_type,
            "minutes_file": minutes_file
        }
        
        subject = f"Draft Minutes: {meeting_type.title()} Meeting on {meeting_date} - Review Requested"

        body = f"Dear Council Officer,\n\n"
        body += f"Attached are the draft minutes from the {meeting_type} meeting held on {meeting_date}.\n\n"

        body += "Best regards,\nCouncil Secretary"

        # Verify the minutes file exists
        if not os.path.exists(minutes_file):
            error_message = f"Minutes file not found: path='{minutes_file}'"
            logger.error(error_message)
            
            # Log possible locations that were checked
            minutes_dir = os.path.dirname(minutes_file)
            if os.path.exists(minutes_dir):
                existing_files = os.listdir(minutes_dir)
                if existing_files:
                    logger.info(f"Available files in {minutes_dir}: {', '.join(existing_files)}")
                else:
                    logger.info(f"Directory {minutes_dir} exists but is empty")
            else:
                logger.warning(f"Directory {minutes_dir} does not exist")
            
            result.update({
                "message": error_message,
                "status": "failed",
                "error": error_message,
                "minutes_found": False
            })
            
            return result

        # Log file details if it exists
        file_size = os.path.getsize(minutes_file)
        file_size_kb = file_size / 1024
        file_name = os.path.basename(minutes_file)
        logger.info(f"Minutes file verified: name='{file_name}', path='{minutes_file}', size={file_size_kb:.2f}KB")

        # Send the email
        result["minutes_found"] = True
        email_result = self._send_email(to, subject, body, [minutes_file], dry_run=dry_run)
        
        # Merge the email result with our result
        result.update(email_result)
        
        return result


if __name__ == "__main__":
    # Example usage of EmailService with dry_run=True for testing
    email_service = EmailService()

    # Test sending a simple email
    result = email_service._send_email(
        to=["recipient@example.com"],
        subject="Test Email from Scribe",
        body="This is a test email sent from the Scribe project using Gmail API.",
        attachments=None,
        dry_run=True
    )
    print(result)

    # Test sending an email with attachment
    import tempfile

    # Create a temporary text file for testing attachment
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as temp:
        temp.write("This is a test attachment.")
        temp_file_path = temp.name

    result = email_service._send_email(
        to=["recipient@example.com"],
        subject="Test Email with Attachment",
        body="This is a test email with an attachment sent using Gmail API.",
        attachments=[temp_file_path],
        dry_run=True
    )
    print(result)

    # Test error handling for missing EMAIL_FROM
    import os

    # Save original EMAIL_FROM
    original_email_from = os.environ.get("EMAIL_FROM")
    
    # Temporarily remove EMAIL_FROM from environment
    if "EMAIL_FROM" in os.environ:
        del os.environ["EMAIL_FROM"]

    # Test sending without EMAIL_FROM
    result = email_service._send_email(
        to=["recipient@example.com"],
        subject="Test Email - Missing EMAIL_FROM",
        body="This email should not be sent due to missing EMAIL_FROM.",
        attachments=None,
        dry_run=False
    )
    print(result)

    # Restore original EMAIL_FROM if it existed
    if original_email_from:
        os.environ["EMAIL_FROM"] = original_email_from

    # Clean up temporary file
    if os.path.exists(temp_file_path):
        os.unlink(temp_file_path)
        
    print("All tests completed.")
