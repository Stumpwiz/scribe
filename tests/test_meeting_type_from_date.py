"""
Test script for the get_meeting_type_from_date function.
"""

from datetime import date
from src.scribe.tools.meeting_notification_tool import get_meeting_type_from_date

def test_get_meeting_type_from_date():
    """Test the get_meeting_type_from_date function with different dates."""
    print("Testing get_meeting_type_from_date function...")
    
    # Test regular meeting months (1, 2, 4, 5, 7, 8, 10, 11)
    regular_months = [1, 2, 4, 5, 7, 8, 10, 11]
    for month in regular_months:
        test_date = date(2025, month, 15)
        meeting_type = get_meeting_type_from_date(test_date)
        print(f"Month {month}: {meeting_type}")
        assert meeting_type == "regular", f"Expected 'regular' for month {month}, got '{meeting_type}'"
    
    # Test open meeting months (3, 6, 9)
    open_months = [3, 6, 9]
    for month in open_months:
        test_date = date(2025, month, 15)
        meeting_type = get_meeting_type_from_date(test_date)
        print(f"Month {month}: {meeting_type}")
        assert meeting_type == "open", f"Expected 'open' for month {month}, got '{meeting_type}'"
    
    # Test association meeting month (12)
    test_date = date(2025, 12, 15)
    meeting_type = get_meeting_type_from_date(test_date)
    print(f"Month 12: {meeting_type}")
    assert meeting_type == "association", f"Expected 'association' for month 12, got '{meeting_type}'"
    
    # Test error handling for invalid input
    try:
        get_meeting_type_from_date("2025-01-15")
        print("Error: Function did not raise TypeError for string input")
    except TypeError as e:
        print(f"Successfully caught TypeError: {e}")
    
    print("\nAll tests passed!")

if __name__ == "__main__":
    test_get_meeting_type_from_date()