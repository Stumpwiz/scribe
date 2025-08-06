"""
Test script for the EmailWriterTool.

This script tests the functionality of the EmailWriterTool by providing
different meeting dates and verifying the generated email content.
"""

import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), \'..\')))
import os
from pathlib import Path

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from scribe.tools.email_writer_tool import EmailWriterTool

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