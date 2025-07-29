"""
Email writer tool for the Scribe project.

This module provides the EmailWriterTool class for generating email reminders
for upcoming Residents Council or Association meetings.
"""

from typing import Dict, Any, Optional, ClassVar
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from crewai.tools import BaseTool

from scribe.tools.meeting_calendar_tool import MeetingCalendarTool
from scribe.tools.recipient_loader_tool import RecipientLoaderTool


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
    
    def _run(self, meetingDate: str, **kwargs) -> Dict[str, Any]:
        """
        Generate an email reminder for an upcoming meeting.
        
        Args:
            meetingDate (str): The date of the meeting in ISO format (YYYY-MM-DD)
            
        Returns:
            Dict[str, Any]: A dictionary containing:
                - success (bool): Whether the operation was successful
                - emailBody (str): The rendered email body
                - log (str): Summary of what was done or errors encountered
        """
        # Initialize result dictionary
        result = {
            "success": False,
            "emailBody": "",
            "log": ""
        }
        
        try:
            # Get meeting metadata using MeetingCalendarTool
            meeting_info = self._get_meeting_info(meetingDate)
            
            # Check if there was an error getting meeting info
            if "error" in meeting_info and meeting_info["error"]:
                result["log"] = f"Error getting meeting info: {meeting_info['message']}"
                return result
            
            # Get recipients using RecipientLoaderTool
            recipients_result = self._get_recipients(meeting_info["meetingType"])
            
            # Check if there was an error getting recipients
            if not recipients_result["success"]:
                result["log"] = f"Error getting recipients: {recipients_result['log']}"
                return result
            
            # Compute report instructions based on meeting type
            report_instructions = self._compute_report_instructions(meeting_info["meetingType"])
            
            # Prepare template context
            template_context = {
                "meetingType": meeting_info["meetingType"],
                "meetingDate": meetingDate,
                "meetingTime": "7:30 PM",  # This could be retrieved from meeting_info if available
                "venue": meeting_info["location"],
                "submissionDeadline": meeting_info["submissionDeadline"],
                "reportInstructions": report_instructions
            }
            
            # Render the email template
            email_body = self._render_template(template_context)
            
            # Set result
            result["success"] = True
            result["emailBody"] = email_body
            result["log"] = "Rendered email template successfully"
            
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
    
    def _compute_report_instructions(self, meeting_type: str) -> str:
        """
        Compute report instructions based on meeting type.
        
        Args:
            meeting_type (str): The type of meeting ("regular", "open", or "association")
            
        Returns:
            str: Report instructions
        """
        if meeting_type == "regular":
            return (
                "Wing Representatives: Please submit your wing reports to the Secretary and Vice President.\n"
                "Liaisons: Please submit your liaison reports to the Secretary."
            )
        elif meeting_type in ["open", "association"]:
            return (
                "Wing Representatives: Please submit your wing reports to the Secretary and Vice President.\n"
                "Committee Chairs: Please submit your committee reports to the Secretary."
            )
        else:
            return "Please submit your reports to the Secretary."
    
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
            
            # Load the template
            template = env.get_template("email_reminder.txt.j2")
            
            # Render the template
            rendered_content = template.render(**context)
            
            return rendered_content
            
        except Exception as e:
            raise ValueError(f"Error rendering template: {str(e)}")


def test_email_writer_tool():
    """Test the EmailWriterTool with various meeting dates."""
    tool = EmailWriterTool()
    
    print("Testing EmailWriterTool...")
    
    # Test with a regular meeting date (e.g., January)
    print("\nTest case 1: Regular meeting (January)")
    result = tool._run(meetingDate="2025-01-15")
    
    # Check if the result is successful and contains an email body
    if result["success"]:
        print(f"✓ Successfully generated email for regular meeting:")
        print(f"✓ Log: {result['log']}")
        print("\nEmail Body:")
        print("=" * 50)
        print(result["emailBody"])
        print("=" * 50)
    else:
        print(f"✗ Failed to generate email: {result['log']}")
    
    # Test with an open meeting date (e.g., March)
    print("\nTest case 2: Open meeting (March)")
    result = tool._run(meetingDate="2025-03-15")
    
    # Check if the result is successful and contains an email body
    if result["success"]:
        print(f"✓ Successfully generated email for open meeting:")
        print(f"✓ Log: {result['log']}")
        print("\nEmail Body:")
        print("=" * 50)
        print(result["emailBody"])
        print("=" * 50)
    else:
        print(f"✗ Failed to generate email: {result['log']}")
    
    # Test with an association meeting date (e.g., December)
    print("\nTest case 3: Association meeting (December)")
    result = tool._run(meetingDate="2025-12-15")
    
    # Check if the result is successful and contains an email body
    if result["success"]:
        print(f"✓ Successfully generated email for association meeting:")
        print(f"✓ Log: {result['log']}")
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
    
    print("\nAll tests completed.")


if __name__ == "__main__":
    test_email_writer_tool()