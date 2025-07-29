"""
Email service tool for the Scribe project.

This module provides the EmailService class for sending and receiving emails
using the SendGrid API.
"""

from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
import os
import logging
from datetime import datetime
from crewai.tools import BaseTool

try:
    import sendgrid
    from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition, ContentId
    import base64
    import mimetypes

    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False
    logging.warning("SendGrid package not available. Email sending will be simulated.")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

    def _run(
            self,
            action: str = "send",
            to: Optional[List[str]] = None,
            subject: Optional[str] = None,
            body: Optional[str] = None,
            attachments: Optional[List[str]] = None,
            **kwargs
    ) -> str:
        # Ensure attachments is always a list
        attachments: List[str] = attachments if attachments is not None else []

        """
        Run the email service.
        
        Args:
            action (str): The action to perform ("send", "receive", "check", "search")
            to (Optional[List[str]]): List of recipient email addresses
            subject (Optional[str]): Email subject line
            body (Optional[str]): Email body content
            attachments (Optional[List[str]]): List of file paths to attach
            
        Returns:
            str: Result of the email operation
        """
        if action == "send":
            return self._send_email(to, subject, body, attachments)
        elif action == "receive":
            return self._receive_emails()
        elif action == "check":
            return self._check_inbox()
        elif action == "search":
            query = kwargs.get("query", "")
            return self._search_emails(query)
        else:
            return f"Unknown action: {action}"

    def _send_email(self,
                    to: Optional[List[str]],
                    subject: Optional[str],
                    body: Optional[str],
                    attachments: Optional[List[str]],
                    dry_run: bool = False) -> str:
        """
        Send an email to the specified recipients using SendGrid API.
        
        Args:
            to (Optional[List[str]]): List of recipient email addresses
            subject (Optional[str]): Email subject line
            body (Optional[str]): Email body content
            attachments (Optional[List[str]]): List of file paths to attach
            dry_run (bool): If True, don't actually send the email, just log what would be sent
            
        Returns:
            str: Result of the send operation
        """
        # Format recipients for logging
        recipients = ", ".join(to) if to else "no recipients"
        attachment_count = len(attachments) if attachments else 0
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # If dry run, just log what would be sent
        if dry_run:
            log_message = f"[DRY RUN] Email would be sent at {timestamp}:\nTo: {recipients}\nSubject: {subject}\nBody: {body}\nAttachments: {attachment_count}"
            logger.info(log_message)
            return log_message

        # Check if SendGrid is available
        if not SENDGRID_AVAILABLE:
            log_message = f"SendGrid package not available. Email sending simulated at {timestamp}:\nTo: {recipients}\nSubject: {subject}\nAttachments: {attachment_count}"
            logger.warning(log_message)
            return log_message

        # Get API key from environment
        api_key = os.getenv("SENDGRID_API_KEY")
        if not api_key:
            error_message = "SendGrid API key not found in environment variables. Set SENDGRID_API_KEY."
            logger.error(error_message)
            return error_message

        try:
            # Create SendGrid client
            sg = sendgrid.SendGridAPIClient(api_key=api_key)

            # Create message
            message = Mail(
                from_email="council.secretary@example.com",  # This should be configured properly in a real app
                to_emails=to,
                subject=subject,
                plain_text_content=body
            )

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

                    # Create attachment
                    encoded_content = base64.b64encode(file_content).decode()
                    attachment = Attachment()
                    attachment.file_content = FileContent(encoded_content)
                    attachment.file_name = FileName(file_name)
                    attachment.file_type = FileType(content_type)
                    attachment.disposition = Disposition('attachment')
                    attachment.content_id = ContentId(file_name)

                    # Add attachment to message
                    message.attachment = attachment

            # Send email
            response = sg.send(message)

            # Log response
            log_message = f"Email sent at {timestamp} with status code {response.status_code}:\nTo: {recipients}\nSubject: {subject}\nAttachments: {attachment_count}"
            logger.info(log_message)
            return log_message

        except Exception as e:
            error_message = f"Error sending email: {str(e)}"
            logger.error(error_message)
            return error_message

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

    def send_reminder(self,
                      to: List[str],
                      meeting_date: str,
                      meeting_type: str,
                      submission_deadline: Optional[str] = None,
                      context: Optional[Dict[str, Any]] = None,
                      dry_run: bool = False) -> str:
        """
        Send a meeting reminder email.
        
        Args:
            to (List[str]): List of recipient email addresses
            meeting_date (str): Date of the meeting (YYYY-MM-DD)
            meeting_type (str): Type of meeting (council, committee, etc.)
            submission_deadline (Optional[str]): Deadline for report submissions
            context (Optional[Dict[str, Any]]): Additional context data including meetingDate and meetingType
            dry_run (bool): If True, don't actually send the email, just log what would be sent
            
        Returns:
            str: Result of the send operation
        """
        subject = f"Reminder: {meeting_type.title()} Meeting on {meeting_date}"

        body = f"Dear Council Member,\n\n"
        body += f"This is a friendly reminder that the {meeting_type} meeting is scheduled for {meeting_date}.\n\n"

        if submission_deadline:
            body += f"Please submit your reports by {submission_deadline}.\n\n"

        body += "Best regards,\nCouncil Secretary"

        # Initialize attachments list
        attachments = []

        # If context is provided, try to attach the agenda PDF
        if context and 'meetingDate' in context and 'meetingType' in context:
            # Construct the agenda PDF path
            agenda_date = context['meetingDate']
            agenda_type = context['meetingType']
            agenda_path = f"src/scribe/output/agendas/agenda_{agenda_date}_{agenda_type}.pdf"

            # Check if the agenda file exists
            if os.path.exists(agenda_path):
                logger.info(f"Attaching agenda PDF: {agenda_path}")
                attachments.append(agenda_path)
            else:
                logger.warning(f"Agenda PDF not found: {agenda_path}. Email will be sent without attachment.")

        return self._send_email(to, subject, body, attachments, dry_run=dry_run)

    def distribute_minutes(self,
                           to: List[str],
                           minutes_file: str,
                           meeting_date: str,
                           meeting_type: str,
                           review_deadline: Optional[str] = None,
                           dry_run: bool = False) -> str:
        """
        Distribute meeting minutes for review.
        
        Args:
            to (List[str]): List of recipient email addresses
            minutes_file (str): Path to the minutes file
            meeting_date (str): Date of the meeting (YYYY-MM-DD)
            meeting_type (str): Type of meeting (council, committee, etc.)
            review_deadline (Optional[str]): Deadline for review feedback
            dry_run (bool): If True, don't actually send the email, just log what would be sent
            
        Returns:
            str: Result of the send operation
        """
        subject = f"Draft Minutes: {meeting_type.title()} Meeting on {meeting_date} - Review Requested"

        body = f"Dear Council Officer,\n\n"
        body += f"Attached are the draft minutes from the {meeting_type} meeting held on {meeting_date}.\n\n"

        if review_deadline:
            body += f"Please review and provide any feedback by {review_deadline}.\n\n"

        body += "Best regards,\nCouncil Secretary"

        return self._send_email(to, subject, body, [minutes_file], dry_run=dry_run)


if __name__ == "__main__":
    # Example usage of EmailService with dry_run=True for testing
    email_service = EmailService()

    # Test sending a simple email
    result = email_service._send_email(
        to=["recipient@example.com"],
        subject="Test Email from Scribe",
        body="This is a test email sent from the Scribe project.",
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
        body="This is a test email with an attachment.",
        attachments=[temp_file_path],
        dry_run=True
    )
    print(result)

    # Test error handling for missing API key (will only show error if SENDGRID_API_KEY is not set)
    import os

    original_api_key = os.environ.get("SENDGRID_API_KEY")
    if "SENDGRID_API_KEY" in os.environ:
        del os.environ["SENDGRID_API_KEY"]

    result = email_service._send_email(
        to=["recipient@example.com"],
        subject="Test Email - Missing API Key",
        body="This email should not be sent due to missing API key.",
        attachments=None,
        dry_run=False
    )
    print(result)

    # Restore original API key if it existed
    if original_api_key:
        os.environ["SENDGRID_API_KEY"] = original_api_key

    # Clean up temporary file
    import os

    if os.path.exists(temp_file_path):
        os.unlink(temp_file_path)
