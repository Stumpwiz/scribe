"""
Test script for the MeetingNotificationTool's get_recipients function.
"""

import json
from pathlib import Path
from src.scribe.tools.meeting_notification_tool import MeetingNotificationTool

# Print the contents of the JSON files for debugging
def print_json_files():
    """Print the contents of the JSON files for debugging."""
    tool = MeetingNotificationTool()
    recipients_dir = Path(tool._run.__code__.co_filename).resolve().parent.parent / "assets/recipients/"
    
    council_members_path = recipients_dir / "council_members.json"
    committee_chairs_path = recipients_dir / "committee_chairs.json"
    
    print(f"Council members path: {council_members_path}")
    print(f"Committee chairs path: {committee_chairs_path}")
    
    try:
        with open(council_members_path, 'r') as f:
            council_members = json.load(f)
            print(f"Council members: {council_members}")
    except Exception as e:
        print(f"Error loading council members: {str(e)}")
    
    try:
        with open(committee_chairs_path, 'r') as f:
            committee_chairs = json.load(f)
            print(f"Committee chairs: {committee_chairs}")
    except Exception as e:
        print(f"Error loading committee chairs: {str(e)}")
    
    print()

def test_get_recipients():
    """Test the get_recipients function with different meeting types."""
    tool = MeetingNotificationTool()
    
    # Test with 'regular' meeting type
    print("Testing with 'regular' meeting type:")
    regular_recipients = tool.get_recipients("regular")
    print(f"Recipients: {regular_recipients}")
    print(f"Count: {len(regular_recipients)}")
    print()
    
    # Test with 'open' meeting type
    print("Testing with 'open' meeting type:")
    open_recipients = tool.get_recipients("open")
    print(f"Recipients: {open_recipients}")
    print(f"Count: {len(open_recipients)}")
    print()
    
    # Test with 'association' meeting type
    print("Testing with 'association' meeting type:")
    association_recipients = tool.get_recipients("association")
    print(f"Recipients: {association_recipients}")
    print(f"Count: {len(association_recipients)}")
    print()
    
    # Verify deduplication
    print("Verifying deduplication:")
    
    # Load the JSON files directly to check deduplication
    tool = MeetingNotificationTool()
    recipients_dir = Path(tool._run.__code__.co_filename).resolve().parent.parent / "assets/recipients/"
    
    council_members_path = recipients_dir / "council_members.json"
    committee_chairs_path = recipients_dir / "committee_chairs.json"
    
    with open(council_members_path, 'r') as f:
        council_members = json.load(f)
        council_emails = council_members
    
    with open(committee_chairs_path, 'r') as f:
        committee_chairs = json.load(f)
        chair_emails = committee_chairs
    
    # Count total emails before deduplication
    total_emails = len(council_emails) + len(chair_emails)
    
    # Count unique emails after deduplication
    unique_emails = len(set(council_emails + chair_emails))
    
    print(f"Total emails before deduplication: {total_emails}")
    print(f"Unique emails after deduplication: {unique_emails}")
    
    # Check if open_recipients has the correct number of unique emails
    if len(open_recipients) == unique_emails:
        print("Deduplication is working correctly!")
    else:
        print(f"Deduplication might not be working correctly. Expected {unique_emails} unique emails, got {len(open_recipients)}.")

if __name__ == "__main__":
    print("Debugging JSON files:")
    print_json_files()
    test_get_recipients()