"""
Test script for the RecipientLoaderTool.

This script tests the functionality of the RecipientLoaderTool by providing
different meeting types and verifying the loaded recipient information.
"""

import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), \'..\')))
import os
import json
from pathlib import Path

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from scribe.tools.recipient_loader_tool import RecipientLoaderTool

def test_recipient_loader_tool():
    """Test the RecipientLoaderTool with various meeting types."""
    tool = RecipientLoaderTool()
    
    print("Testing RecipientLoaderTool...")
    
    # Test with regular meeting type
    print("\nTest case 1: Regular meeting type")
    result = tool._run(meetingType="regular")
    
    # Check if the result is successful and contains recipients
    if result["success"]:
        print(f"✓ Successfully loaded recipients for regular meeting:")
        print(f"✓ Log: {result['log']}")
        print(f"✓ Found {len(result['recipients'])} recipients")
    else:
        print(f"✗ Failed to load recipients: {result['log']}")
    
    # Test with open meeting type
    print("\nTest case 2: Open meeting type")
    result = tool._run(meetingType="open")
    
    # Check if the result is successful and contains recipients
    if result["success"]:
        print(f"✓ Successfully loaded recipients for open meeting:")
        print(f"✓ Log: {result['log']}")
        print(f"✓ Found {len(result['recipients'])} recipients")
    else:
        print(f"✗ Failed to load recipients: {result['log']}")
    
    # Test with association meeting type
    print("\nTest case 3: Association meeting type")
    result = tool._run(meetingType="association")
    
    # Check if the result is successful and contains recipients
    if result["success"]:
        print(f"✓ Successfully loaded recipients for association meeting:")
        print(f"✓ Log: {result['log']}")
        print(f"✓ Found {len(result['recipients'])} recipients")
    else:
        print(f"✗ Failed to load recipients: {result['log']}")
    
    # Test with invalid meeting type
    print("\nTest case 4: Invalid meeting type")
    result = tool._run(meetingType="invalid")
    
    # Check if the error message is returned
    if not result["success"] and "Invalid meeting type" in result["log"]:
        print(f"✓ Error correctly detected: {result['log']}")
    else:
        print(f"✗ Error not detected for invalid meeting type: {result['log']}")
    
    print("\nAll tests completed.")

if __name__ == "__main__":
    test_recipient_loader_tool()