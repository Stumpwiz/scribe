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
    
    def get_recipients(self, meeting_type: str) -> List[str]:
        """
        Get the list of email recipients based on meeting type.
        
        Args:
            meeting_type (str): Type of meeting ('regular', 'open', or 'association')
            
        Returns:
            List[str]: A deduplicated list of email addresses
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Construct the path to the recipients directory
        # Use absolute path to ensure files are found regardless of where the script is run from
        recipients_dir = Path(__file__).resolve().parent.parent / "assets/recipients/"
        
        # Initialize the list of email addresses
        emails = []
        
        # Always load council members
        council_members_path = recipients_dir / "council_members.json"
        try:
            with open(council_members_path, 'r') as f:
                council_members = json.load(f)
                if not isinstance(council_members, list):
                    logger.error("Invalid format in council_members.json: expected a list of emails")
                else:
                    emails.extend(council_members)
                    logger.info(f"Loaded {len(council_members)} email(s) from council_members.json")
        except FileNotFoundError:
            logger.error(f"Council members file not found: {council_members_path}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in council members file: {council_members_path}")
        except Exception as e:
            logger.error(f"Error loading council members: {str(e)}")
        
        # For 'open' or 'association' meetings, also include committee chairs
        if meeting_type.lower() in ["open", "association"]:
            committee_chairs_path = recipients_dir / "committee_chairs.json"
            try:
                with open(committee_chairs_path, 'r') as f:
                    committee_chairs = json.load(f)
                    if not isinstance(committee_chairs, list):
                        logger.error("Invalid format in committee_chairs.json: expected a list of emails")
                    else:
                        emails.extend(committee_chairs)
                        logger.info(f"Loaded {len(committee_chairs)} email(s) from committee_chairs.json")
            except FileNotFoundError:
                logger.error(f"Committee chairs file not found: {committee_chairs_path}")
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in committee chairs file: {committee_chairs_path}")
            except Exception as e:
                logger.error(f"Error loading committee chairs: {str(e)}")
        
        # Deduplicate the list of emails
        emails = list(set(emails))
        
        # If no recipients were found, use fallback email
        if not emails:
            fallback_email = "geo@loyola.edu"
            logger.warning(f"No recipients found for meeting type '{meeting_type}'. Using fallback email: {fallback_email}")
            emails = [fallback_email]
        else:
            logger.info(f"Found {len(emails)} recipient(s) for meeting type '{meeting_type}'")
        
        return emails
    
    def _run(self, 
             content: str,
             meeting_date: Optional[str] = None,
             location: Optional[str] = None,
             filename_hint: Optional[str] = None,
             include_agenda_template: bool = True,
             attachment_path: Optional[str] = None,
             agenda_result: Optional[Dict[str, Any]] = None,
             **kwargs) -> str:
        """
        Create and save a meeting notification draft.
        
        Args:
            content (str): The text content of the notification
            meeting_date (Optional[str]): Date of the meeting
            location (Optional[str]): Location of the meeting
            filename_hint (Optional[str]): A short string to use in naming the file
            include_agenda_template (bool): Whether to include a reference to the agenda template
            attachment_path (Optional[str]): Path to a PDF file to attach to the email
            agenda_result (Optional[Dict[str, Any]]): Result from MeetingAgendaGeneratorTool
            
        Returns:
            str: The full path to the created draft file
        """
        import logging
        logger = logging.getLogger(__name__)
        
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
        
        # Update content with attachment information
        if agenda_attachment:
            content += f"\n\n[Attached: {os.path.basename(agenda_attachment)}]"
            logger.info(f"Attaching agenda PDF: {agenda_attachment}")
        # Add agenda template reference if requested and no attachment provided
        elif include_agenda_template:
            content += "\n\n[Attached: agenda_template.txt]"
            logger.info("No agenda PDF found, using template reference instead")
        
        # Add meeting details if provided
        details = []
        if meeting_date:
            details.append(f"Meeting Date: {meeting_date}")
        if location:
            details.append(f"Location: {location}")
        
        if details:
            content += "\n\n--- Meeting Details ---\n" + "\n".join(details)
        
        # Get recipients for the email
        recipients = kwargs.get("recipients", ["geo@loyola.edu"])
        subject = f"Meeting Reminder: {meeting_date}" if meeting_date else "Meeting Reminder"
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
        
        # Send the email using EmailService
        from scribe.tools.email_service import EmailService
        email_service = EmailService()
        
        # Call _run method directly with unpacked arguments instead of passing a dictionary
        result = email_service._run(
            action="send",
            to=recipients,
            subject=subject,
            body=email_body,
            attachments=attachments
        )
        
        logger.info(f"Email sent. Result: {result}")
        
        return self._save_notification(content, filename_hint)
    
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
            return f"Meeting notification draft saved to: {str(file_path)}"
        except Exception as e:
            return f"Error saving meeting notification draft: {str(e)}"