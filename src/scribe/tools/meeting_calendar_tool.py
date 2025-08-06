"""
Meeting calendar tool for the Scribe project.

This module provides the MeetingCalendarTool class for deriving meeting information
based on a given meeting date.
"""

from typing import Dict, Any, Optional, ClassVar
from datetime import datetime, timedelta
import re
from pathlib import Path
from crewai.tools import BaseTool


class MeetingCalendarTool(BaseTool):
    """
    Tool for deriving meeting information based on a given date.
    
    This tool accepts a meeting date and returns a dictionary containing
    derived fields such as meeting type, location, etc.
    based on predefined rules.
    """
    
    name: str = "MeetingCalendarTool"
    description: str = "Tool for deriving meeting information based on a given date"
    
    # Compute base directory (project root) as a class attribute
    base_dir: ClassVar[Path] = Path(__file__).resolve().parents[2]  # resolves to src/
    
    def _run(self, meeting_date: str, **kwargs) -> Dict[str, Any]:
        """
        Derive meeting information based on the given meeting date.
        
        Args:
            meeting_date (str): The date of the meeting in ISO format (YYYY-MM-DD)
            
        Returns:
            Dict[str, Any]: A dictionary containing derived meeting information
            
        Raises:
            ValueError: If the meeting date is malformed or invalid
        """
        try:
            # Parse the meeting date
            date_obj = self._parse_date(meeting_date)
            
            # Derive meeting information
            meeting_info = self._derive_meeting_info(date_obj)
            
            return meeting_info
            
        except ValueError as e:
            return {
                "error": True,
                "message": str(e)
            }
        except Exception as e:
            return {
                "error": True,
                "message": f"An unexpected error occurred: {str(e)}"
            }
    
    def _parse_date(self, date_str: str) -> datetime:
        """
        Parse the date string into a datetime object.
        
        Args:
            date_str (str): The date string in ISO format (YYYY-MM-DD)
            
        Returns:
            datetime: The parsed datetime object
            
        Raises:
            ValueError: If the date string is malformed or invalid
        """
        # Check if the date string matches the ISO format
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            raise ValueError(f"Invalid date format: {date_str}. Expected format: YYYY-MM-DD")
        
        try:
            # Parse the date string
            return datetime.fromisoformat(date_str)
        except ValueError:
            raise ValueError(f"Invalid date: {date_str}")
    
    def _derive_meeting_info(self, date: datetime) -> Dict[str, Any]:
        """
        Derive meeting information based on the given date.
        
        Args:
            date (datetime): The meeting date
            
        Returns:
            Dict[str, Any]: A dictionary containing derived meeting information in camelCase format
            
        Raises:
            ValueError: If an unknown meeting type is encountered
        """
        # Extract month
        month = date.month
        
        # Determine meeting type, body, and location based on month
        if month == 12:
            meeting_type = "association"
            meeting_body = "Residents Association"
            location = "Performing Arts Center (PAC)"
        elif month in [3, 6, 9]:
            meeting_type = "open"
            meeting_body = "Residents Council"
            location = "Performing Arts Center (PAC)"
        else:  # months 1, 2, 4, 5, 7, 8, 10, 11
            meeting_type = "regular"
            meeting_body = "Residents Council"
            location = "McAuley Conference Room (MCR)"
        
        # Note: submission_deadline calculation has been removed due to simplification
        
        # Determine template and recipient file paths based on meeting type
        if meeting_type == "association":
            template_path = self.base_dir / "scribe" / "assets" / "templates" / "agenda_association.tex.j2"
            recipient_path = self.base_dir / "scribe" / "data" / "association_members.json"
            agenda_template = template_path.as_posix()
            recipient_file = recipient_path.as_posix()
        elif meeting_type == "open":
            template_path = self.base_dir / "scribe" / "assets" / "templates" / "agenda_open.tex.j2"
            recipient_path = self.base_dir / "scribe" / "data" / "council_members_and_residents.json"
            agenda_template = template_path.as_posix()
            recipient_file = recipient_path.as_posix()
        elif meeting_type == "regular":
            template_path = self.base_dir / "scribe" / "assets" / "templates" / "agenda_regular.tex.j2"
            recipient_path = self.base_dir / "scribe" / "data" / "council_members.json"
            agenda_template = template_path.as_posix()
            recipient_file = recipient_path.as_posix()
        else:
            # Handle unknown meeting types
            raise ValueError(f"Unknown meeting type: {meeting_type}")
        
        # Return the derived meeting information with camelCase keys for LaTeX compatibility
        # Note: submissionDeadline has been removed due to simplification
        return {
            "meetingType": meeting_type,
            "meetingBody": meeting_body,
            "location": location,
            "agendaTemplate": agenda_template,
            "recipientFile": recipient_file
        }