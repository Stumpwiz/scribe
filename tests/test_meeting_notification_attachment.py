"""
Test script for the MeetingNotificationTool with PDF attachments.

This script tests the functionality of the MeetingNotificationTool by providing
a simulated agenda_result with a PDF path and verifying that the tool correctly
handles the attachment.
"""

import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import os
from pathlib import Path
import logging

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from scribe.tools.meeting_notification_tool import MeetingNotificationTool

def test_meeting_notification_with_attachment():
    """Test the MeetingNotificationTool with a PDF attachment."""
    # Configure logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create an instance of the tool
    tool = MeetingNotificationTool()
    
    # Create a test file path (using a text file that exists)
    test_file_path = str(Path(__file__).parent.parent / "src" / "scribe" / "output" / "agendas" / "test_agenda.txt")
    
    # Create a simulated agenda_result with a file path
    agenda_result = {
        "success": True,
        "pdfPath": test_file_path,
        "log": "Compilation successful"
    }
    
    # Test with a valid file path
    print(f"Testing MeetingNotificationTool with file path: {test_file_path}")
    
    # Call the tool with the agenda_result
    result = tool._run(
        content="This is a test meeting notification.",
        meeting_date="2025-08-12",
        location="Conference Room A",
        filename_hint="test_attachment",
        agenda_result=agenda_result
    )
    
    # Print the result
    print("\nResult:")
    print(result)
    
    # Test with a non-existent PDF path
    print("\nTesting with non-existent PDF path")
    non_existent_path = str(Path(__file__).parent.parent / "src" / "scribe" / "output" / "agendas" / "nonexistent.pdf")
    agenda_result["pdfPath"] = non_existent_path
    
    # Call the tool with the invalid agenda_result
    result = tool._run(
        content="This is a test meeting notification with non-existent attachment.",
        meeting_date="2025-08-12",
        location="Conference Room A",
        filename_hint="test_nonexistent_attachment",
        agenda_result=agenda_result
    )
    
    # Print the result
    print("\nResult with non-existent PDF:")
    print(result)
    
    # Test with explicit attachment_path
    print("\nTesting with explicit attachment_path")
    
    # Call the tool with explicit attachment_path
    result = tool._run(
        content="This is a test meeting notification with explicit attachment path.",
        meeting_date="2025-08-12",
        location="Conference Room A",
        filename_hint="test_explicit_attachment",
        attachment_path=test_file_path
    )
    
    # Print the result
    print("\nResult with explicit attachment_path:")
    print(result)

if __name__ == "__main__":
    test_meeting_notification_with_attachment()