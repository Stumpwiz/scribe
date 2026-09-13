"""
Test script to verify that the calendar integration methods work correctly.

This script tests the CalendarIntegration class with the @staticmethod decorators
added to the specified methods.
"""

import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import os
from pathlib import Path
from datetime import datetime

def test_calendar_integration():
    """Test the CalendarIntegration class."""
    try:
        # Add the src directory to the Python path
        src_dir = Path(__file__).parent.parent / "src"
        sys.path.insert(0, str(src_dir))
        print(f"Added {src_dir} to Python path")
        
        # Import the CalendarIntegration class
        from scribe.tools.calendar_integration import CalendarIntegration
        print("Imported CalendarIntegration class")
        
        # Create an instance of the CalendarIntegration class
        calendar = CalendarIntegration()
        print("Created CalendarIntegration instance")
        
        # Test each method
        print("\nTesting _schedule_event:")
        result = calendar._schedule_event(
            "Test Event",
            "2025-07-18",
            "14:00",
            60,
            ["test@example.com"],
            "Test Location",
            "Test Description"
        )
        print(result)
        
        print("\nTesting _check_availability:")
        result = calendar._check_availability("2025-07-18")
        print(result)
        
        print("\nTesting _list_events:")
        result = calendar._list_events("2025-07-18", "2025-07-25")
        print(result)
        
        print("\nTesting _set_reminder:")
        result = calendar._set_reminder("Test Reminder", "2025-07-18", 3)
        print(result)
        
        print("\nTesting _cancel_event:")
        result = calendar._cancel_event("Test Event", "2025-07-18")
        print(result)
        
        print("\nAll tests passed!")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_calendar_integration()