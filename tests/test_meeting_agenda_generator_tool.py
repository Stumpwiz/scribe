"""
Test script for the MeetingAgendaGeneratorTool.

This script tests the functionality of the MeetingAgendaGeneratorTool by providing
a meeting date and verifying that the tool correctly generates a PDF agenda.
"""

import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import os
from pathlib import Path

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

import logging
from scribe.tools.meeting_agenda_generator_tool import MeetingAgendaGeneratorTool

def test_meeting_agenda_generator_tool():
    """Test the MeetingAgendaGeneratorTool with a sample meeting date."""
    # Configure logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create an instance of the tool
    tool = MeetingAgendaGeneratorTool()
    
    # Test with the specified meeting date
    meeting_date = "2025-08-07"
    print(f"Testing MeetingAgendaGeneratorTool with meeting date: {meeting_date}")
    
    # Call the tool
    result = tool._run(meeting_info={"meetingDate": meeting_date})
    
    # Print the result
    print("\nResult:")
    print(f"Success: {result['success']}")
    print(f"PDF Path: {result['pdfPath']}")
    print(f"Log (first 500 characters): {result['log'][:500]}...")
    
    # Check if the PDF was created
    if result["success"] and result["pdfPath"] and Path(result["pdfPath"]).exists():
        print(f"\nPDF file created successfully: {result['pdfPath']}")
    else:
        print("\nFailed to create PDF file.")

if __name__ == "__main__":
    test_meeting_agenda_generator_tool()