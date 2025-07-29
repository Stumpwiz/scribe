"""
Meeting notification tool for the Scribe project.

This module provides the MeetingNotificationTool class for creating and saving
meeting notification drafts to be sent to council members and committee chairs.
"""

from typing import Optional
import os
from pathlib import Path
from datetime import datetime
import re
from crewai.tools import BaseTool


class MeetingNotificationTool(BaseTool):
    """
    Tool for creating and saving meeting notification drafts.
    
    This tool allows agents to create meeting notification drafts and save them
    to the output/reminders/ directory for review before sending.
    """
    
    name: str = "MeetingNotificationTool"
    description: str = "Tool for creating and saving meeting notification drafts"
    
    def _run(self, 
             content: str,
             meeting_date: Optional[str] = None,
             submission_deadline: Optional[str] = None,
             location: Optional[str] = None,
             filename_hint: Optional[str] = None,
             include_agenda_template: bool = True,
             **kwargs) -> str:
        """
        Create and save a meeting notification draft.
        
        Args:
            content (str): The text content of the notification
            meeting_date (Optional[str]): Date of the meeting
            submission_deadline (Optional[str]): Deadline for submitting agenda items
            location (Optional[str]): Location of the meeting
            filename_hint (Optional[str]): A short string to use in naming the file
            include_agenda_template (bool): Whether to include a reference to the agenda template
            
        Returns:
            str: The full path to the created draft file
        """
        # Add agenda template reference if requested
        if include_agenda_template:
            content += "\n\n[Attached: agenda_template.txt]"
        
        # Add meeting details if provided
        details = []
        if meeting_date:
            details.append(f"Meeting Date: {meeting_date}")
        if submission_deadline:
            details.append(f"Submission Deadline: {submission_deadline}")
        if location:
            details.append(f"Location: {location}")
        
        if details:
            content += "\n\n--- Meeting Details ---\n" + "\n".join(details)
        
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