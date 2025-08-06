"""
Test script for the LaTeXAgendaTool.

This script tests the functionality of the LaTeXAgendaTool by providing
a sample meeting information dictionary and verifying that the tool
correctly renders the template and saves the file.
"""

import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), \'..\')))
import os
from pathlib import Path
import shutil

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from scribe.tools.latex_agenda_tool import LaTeXAgendaTool
from scribe.tools.meeting_calendar_tool import MeetingCalendarTool

def test_latex_agenda_tool():
    """Test the LaTeXAgendaTool with a sample meeting information dictionary."""
    # Create an instance of the LaTeXAgendaTool
    tool = LaTeXAgendaTool()
    
    # Create an instance of the MeetingCalendarTool to get meeting information
    calendar_tool = MeetingCalendarTool()
    
    # Get meeting information for a specific date
    meeting_date = "2025-08-07"  # The date from the issue description
    meeting_info = calendar_tool._run(meeting_date=meeting_date)
    
    if "error" in meeting_info and meeting_info["error"]:
        print(f"Error getting meeting information: {meeting_info['message']}")
        return
    
    # Print the meeting information
    print("Meeting Information:")
    for key, value in meeting_info.items():
        print(f"  {key}: {value}")
    
    # Add additional required fields for the template
    meeting_info["meetingDate"] = meeting_date  # Add the meeting date to the dictionary
    meeting_info["meetingTime"] = "7:30"
    meeting_info["nextMeetingDate"] = "2025-09-04"
    meeting_info["thisVenue"] = meeting_info["location"]
    meeting_info["mextVenue"] = "Performing Arts Center (PAC)"  # For the next meeting
    
    # Create the output directory if it doesn't exist
    output_dir = os.path.join("src", "scribe", "output", "agendas")
    os.makedirs(output_dir, exist_ok=True)
    
    # Run the LaTeXAgendaTool
    print("\nRunning LaTeXAgendaTool...")
    result = tool._run(meeting_info=meeting_info)
    
    # Check if the result is an error message
    if result.startswith("Error:") or result.startswith("An unexpected error occurred:"):
        print(f"Tool returned an error: {result}")
        return
    
    # Print the result (path to the saved file)
    print(f"File saved to: {result}")
    
    # Check if the file exists
    if os.path.exists(result):
        print(f"✓ File exists: {result}")
        
        # Print the first few lines of the file
        print("\nFirst 10 lines of the generated file:")
        with open(result, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i < 10:
                    print(f"  {i+1}: {line.rstrip()}")
                else:
                    break
    else:
        print(f"✗ File does not exist: {result}")

if __name__ == "__main__":
    test_latex_agenda_tool()