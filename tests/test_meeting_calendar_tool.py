"""
Test script for the MeetingCalendarTool.

This script tests the functionality of the MeetingCalendarTool by providing
different meeting dates and verifying the derived meeting information.
"""

import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import os
from pathlib import Path

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from scribe.tools.meeting_calendar_tool import MeetingCalendarTool

def test_meeting_calendar_tool():
    """Test the MeetingCalendarTool with various dates."""
    tool = MeetingCalendarTool()
    
    # Test cases for different months
    test_cases = [
        # Regular council meeting (January)
        {
            "date": "2025-01-02",
            "expected_type": "regular",
            "expected_body": "Residents Council",
            "expected_location": "McAuley Conference Room (MCR)"
        },
        # Open council meeting (March)
        {
            "date": "2025-03-06",
            "expected_type": "open",
            "expected_body": "Residents Council",
            "expected_location": "Performing Arts Center (PAC)"
        },
        # Association meeting (December)
        {
            "date": "2025-12-04",
            "expected_type": "association",
            "expected_body": "Residents Association",
            "expected_location": "Performing Arts Center (PAC)"
        },
        # The date from the task.yaml file
        {
            "date": "2025-08-07",
            "expected_type": "regular",
            "expected_body": "Residents Council",
            "expected_location": "McAuley Conference Room (MCR)"
        }
    ]
    
    # Run tests
    for i, test_case in enumerate(test_cases):
        print(f"\nTest case {i+1}: {test_case['date']}")
        result = tool._run(meeting_date=test_case["date"])
        
        # Check for errors
        if "error" in result and result["error"]:
            print(f"Error: {result['message']}")
            continue
        
        # Verify meeting type
        if result["meetingType"] == test_case["expected_type"]:
            print(f"✓ Meeting type: {result['meetingType']}")
        else:
            print(f"✗ Meeting type: {result['meetingType']} (expected: {test_case['expected_type']})")
        
        # Verify meeting body
        if result["meetingBody"] == test_case["expected_body"]:
            print(f"✓ Meeting body: {result['meetingBody']}")
        else:
            print(f"✗ Meeting body: {result['meetingBody']} (expected: {test_case['expected_body']})")
        
        # Verify location
        if result["location"] == test_case["expected_location"]:
            print(f"✓ Location: {result['location']}")
        else:
            print(f"✗ Location: {result['location']} (expected: {test_case['expected_location']})")
        
        # Print other derived information
        print(f"Submission deadline: {result['submissionDeadline']}")
        print(f"Agenda template: {result['agendaTemplate']}")
        print(f"Recipient file: {result['recipientFile']}")
        
        # Verify agenda template path based on meeting type
        expected_template = ""
        if test_case["expected_type"] == "regular":
            expected_template = "assets/templates/agenda_regular.tex.j2"
        elif test_case["expected_type"] == "open":
            expected_template = "assets/templates/agenda_open.tex.j2"
        elif test_case["expected_type"] == "association":
            expected_template = "assets/templates/agenda_association.tex.j2"
            
        if result["agendaTemplate"] == expected_template:
            print(f"✓ Agenda template path is correct: {result['agendaTemplate']}")
        else:
            print(f"✗ Agenda template path is incorrect: {result['agendaTemplate']} (expected: {expected_template})")
    
    # Test error handling with invalid date format
    print("\nTest case: Invalid date format")
    result = tool._run(meeting_date="2025/01/02")
    if "error" in result and result["error"]:
        print(f"✓ Error correctly detected: {result['message']}")
    else:
        print("✗ Error not detected for invalid date format")
    
    # Test error handling with invalid date
    print("\nTest case: Invalid date")
    result = tool._run(meeting_date="2025-13-45")
    if "error" in result and result["error"]:
        print(f"✓ Error correctly detected: {result['message']}")
    else:
        print("✗ Error not detected for invalid date")

if __name__ == "__main__":
    test_meeting_calendar_tool()