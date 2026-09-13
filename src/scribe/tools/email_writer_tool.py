"""
Email writer tool for the Scribe project.

This module provides the EmailWriterTool class for generating email reminders
for upcoming Residents Council or Association meetings.
"""

from typing import Dict, Any, Optional, ClassVar, List
from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from crewai.tools import BaseTool

from scribe.tools.meeting_calendar_tool import MeetingCalendarTool
from scribe.tools.recipient_loader_tool import RecipientLoaderTool
from scribe.tools.meeting_agenda_generator_tool import MeetingAgendaGeneratorTool
from scribe.tools.meeting_notification_tool import get_meeting_type_from_date


class EmailWriterTool(BaseTool):
    """
    Tool for generating email reminders for upcoming meetings.
    
    This tool accepts a meeting date and generates a plain-text email reminder
    by rendering a Jinja2 template with meeting information.
    """
    
    name: str = "EmailWriterTool"
    description: str = "Tool for generating email reminders for upcoming meetings"
    
    # Compute base directory (project root) as a class attribute
    base_dir: ClassVar[Path] = Path(__file__).resolve().parents[2]  # resolves to src/
    
    # Define template path
    template_path: ClassVar[str] = "scribe/assets/templates/email_reminder.txt.j2"
    
    def _run(self, meetingDate: str, meeting_type: Optional[str] = None, old_business: Optional[str] = None, new_business: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Generate an email reminder for an upcoming meeting.
        
        Args:
            meetingDate (str): The date of the meeting in ISO format (YYYY-MM-DD)
            meeting_type (Optional[str]): The type of meeting ('regular', 'open', or 'association')
            old_business (Optional[str]): Old business items for the agenda
            new_business (Optional[str]): New business items for the agenda
            
        Returns:
            Dict[str, Any]: A dictionary containing:
                - success (bool): Whether the operation was successful
                - emailBody (str): The rendered email body
                - agendaPdf (str): Path to the generated agenda PDF
                - log (str): Summary of what was done or errors encountered
        """
        # Initialize result dictionary
        result = {
            "success": False,
            "emailBody": "",
            "agendaPdf": "",
            "log": ""
        }
        
        try:
            # Get meeting metadata using MeetingCalendarTool
            meeting_info = self._get_meeting_info(meetingDate)
            
            # Check if there was an error getting meeting info
            if "error" in meeting_info and meeting_info["error"]:
                result["log"] = f"Error getting meeting info: {meeting_info['message']}"
                return result
            
            # Determine meeting type if not provided
            if not meeting_type:
                try:
                    # Convert string date to datetime.date object
                    meeting_date_obj = datetime.strptime(meetingDate, "%Y-%m-%d").date()
                    meeting_type = get_meeting_type_from_date(meeting_date_obj)
                except Exception as e:
                    result["log"] = f"Error determining meeting type: {str(e)}"
                    return result
            
            # Get recipients using RecipientLoaderTool
            recipients_result = self._get_recipients(meeting_type)
            
            # Check if there was an error getting recipients
            if not recipients_result["success"]:
                result["log"] = f"Error getting recipients: {recipients_result['log']}"
                return result
            
            # Note: report instructions have been removed due to simplification
            
            # Generate agenda PDF using MeetingAgendaGeneratorTool
            agenda_result = self._generate_agenda(meetingDate, meeting_type, old_business, new_business)
            
            # Check if there was an error generating the agenda
            if not agenda_result["success"]:
                result["log"] = f"Error generating agenda: {agenda_result['log']}"
                return result
            
            # Prepare template context
            # Note: submissionDeadline and reportInstructions have been removed due to simplification
            old_business_items = old_business.splitlines() if old_business else []
            new_business_items = new_business.splitlines() if new_business else []
            template_context = {
                "meetingType": meeting_type,
                "meetingDate": meetingDate,
                "meetingTime": "7:30 PM",  # This could be retrieved from meeting_info if available
                "venue": meeting_info["location"],
                "oldBusinessItems": old_business_items,
                "newBusinessItems": new_business_items,
            }
            
            # Render the email template
            email_body = self._render_template(template_context)
            
            # Set result
            result["success"] = True
            result["emailBody"] = email_body
            result["agendaPdf"] = agenda_result["pdfPath"]
            result["log"] = "Rendered email template and generated agenda PDF successfully"
            
        except Exception as e:
            result["log"] = f"Error: {str(e)}"
            
        return result
    
    def _get_meeting_info(self, meeting_date: str) -> Dict[str, Any]:
        """
        Get meeting information using MeetingCalendarTool.
        
        Args:
            meeting_date (str): The date of the meeting in ISO format (YYYY-MM-DD)
            
        Returns:
            Dict[str, Any]: Meeting information
        """
        calendar_tool = MeetingCalendarTool()
        return calendar_tool._run(meeting_date=meeting_date)
    
    def _get_recipients(self, meeting_type: str) -> Dict[str, Any]:
        """
        Get recipients using RecipientLoaderTool.
        
        Args:
            meeting_type (str): The type of meeting ("regular", "open", or "association")
            
        Returns:
            Dict[str, Any]: Recipients information
        """
        recipient_tool = RecipientLoaderTool()
        return recipient_tool._run(meetingType=meeting_type)
    
    # Note: _compute_report_instructions method has been removed due to simplification
    
    def _render_template(self, context: Dict[str, Any]) -> str:
        """
        Render the email template using Jinja2.
        
        Args:
            context (Dict[str, Any]): Template context
            
        Returns:
            str: Rendered template
            
        Raises:
            ValueError: If there are issues with template rendering
        """
        try:
            # Set up Jinja2 environment
            template_dir = self.base_dir / "scribe" / "assets" / "templates"
            env = Environment(loader=FileSystemLoader(template_dir))
            
            # Configure Jinja2 to handle missing variables gracefully
            env.undefined = StrictUndefined
            
            # Load the template
            template = env.get_template("email_reminder.txt.j2")
            
            # Render the template
            rendered_content = template.render(**context)
            
            return rendered_content
            
        except Exception as e:
            raise ValueError(f"Error rendering template: {str(e)}")
            
    def _generate_agenda(self, meeting_date: str, meeting_type: str, old_business: Optional[str] = None, new_business: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate an agenda PDF for the meeting using MeetingAgendaGeneratorTool.
        
        Args:
            meeting_date (str): The date of the meeting in ISO format (YYYY-MM-DD)
            meeting_type (str): The type of meeting ('regular', 'open', or 'association')
            old_business (Optional[str]): Old business items for the agenda
            new_business (Optional[str]): New business items for the agenda
            
        Returns:
            Dict[str, Any]: A dictionary containing:
                - success (bool): Whether the operation was successful
                - pdfPath (str): Path to the generated PDF
                - log (str): Summary of what was done or errors encountered
        """
        try:
            # Create meeting info dictionary
            meeting_info = {
                "meetingDate": meeting_date,
                "meetingType": meeting_type,
                "old_business": old_business or "",
                "new_business": new_business or ""
            }
            
            # Generate agenda using MeetingAgendaGeneratorTool
            agenda_tool = MeetingAgendaGeneratorTool()
            result = agenda_tool._run(meeting_info=meeting_info)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "pdfPath": "",
                "log": f"Error generating agenda: {str(e)}"
            }


def test_email_writer_tool():
    """Test the EmailWriterTool with various meeting dates."""
    tool = EmailWriterTool()
    
    print("Testing EmailWriterTool...")
    
    # Test with a regular meeting date (e.g., January)
    print("\nTest case 1: Regular meeting (January)")
    result = tool._run(
        meetingDate="2025-01-15",
        meeting_type="regular",
        old_business="Discussion of previous budget allocation",
        new_business="Proposal for community garden"
    )
    
    # Check if the result is successful and contains an email body and agenda PDF
    if result["success"]:
        print(f"✓ Successfully generated email for regular meeting:")
        print(f"✓ Log: {result['log']}")
        print(f"✓ Agenda PDF: {result['agendaPdf']}")
        print("\nEmail Body:")
        print("=" * 50)
        print(result["emailBody"])
        print("=" * 50)
    else:
        print(f"✗ Failed to generate email: {result['log']}")
    
    # Test with an open meeting date (e.g., March)
    print("\nTest case 2: Open meeting (March)")
    result = tool._run(
        meetingDate="2025-03-15",
        meeting_type="open",
        old_business="Follow-up on resident concerns",
        new_business="Summer event planning"
    )
    
    # Check if the result is successful and contains an email body and agenda PDF
    if result["success"]:
        print(f"✓ Successfully generated email for open meeting:")
        print(f"✓ Log: {result['log']}")
        print(f"✓ Agenda PDF: {result['agendaPdf']}")
        print("\nEmail Body:")
        print("=" * 50)
        print(result["emailBody"])
        print("=" * 50)
    else:
        print(f"✗ Failed to generate email: {result['log']}")
    
    # Test with an association meeting date (e.g., December)
    print("\nTest case 3: Association meeting (December)")
    result = tool._run(
        meetingDate="2025-12-15",
        meeting_type="association",
        old_business="Annual budget review",
        new_business="Election of new officers"
    )
    
    # Check if the result is successful and contains an email body and agenda PDF
    if result["success"]:
        print(f"✓ Successfully generated email for association meeting:")
        print(f"✓ Log: {result['log']}")
        print(f"✓ Agenda PDF: {result['agendaPdf']}")
        print("\nEmail Body:")
        print("=" * 50)
        print(result["emailBody"])
        print("=" * 50)
    else:
        print(f"✗ Failed to generate email: {result['log']}")
    
    # Test with an invalid date format
    print("\nTest case 4: Invalid date format")
    result = tool._run(meetingDate="2025/01/15")
    
    # Check if the error message is returned
    if not result["success"]:
        print(f"✓ Error correctly detected: {result['log']}")
    else:
        print(f"✗ Error not detected for invalid date format")
    
    # Test with automatic meeting type detection
    print("\nTest case 5: Automatic meeting type detection")
    result = tool._run(
        meetingDate="2025-06-15",  # June should be an "open" meeting
        old_business="Previous meeting follow-up",
        new_business="Summer activities planning"
    )
    
    # Check if the result is successful and the correct meeting type was detected
    if result["success"]:
        print(f"✓ Successfully generated email with automatic meeting type detection:")
        print(f"✓ Log: {result['log']}")
        print(f"✓ Agenda PDF: {result['agendaPdf']}")
        print("\nEmail Body:")
        print("=" * 50)
        print(result["emailBody"])
        print("=" * 50)
    else:
        print(f"✗ Failed to generate email: {result['log']}")
    
    print("\nAll tests completed.")


if __name__ == "__main__":
    test_email_writer_tool()
