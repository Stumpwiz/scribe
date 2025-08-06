"""
Test script for the enhanced EmailService logging functionality.

This script tests the structured logging and detailed status reporting
added to the EmailService class.
"""

import os
import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), \'..\')))
import json
from pathlib import Path
import tempfile

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from scribe.tools.email_service import EmailService

def test_structured_logging():
    """Test the structured logging functionality of the EmailService class."""
    email_service = EmailService()
    
    print("Testing structured logging functionality of EmailService...")
    
    # Create a temporary text file for testing attachment
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as temp:
        temp.write("This is a test attachment for structured logging test.")
        temp_file_path = temp.name
    
    # Test 1: Successful email send (dry run)
    print("\nTest 1: Successful email send (dry run)")
    result = email_service._send_email(
        to=["test@example.com", "another@example.com"],
        subject="Test Email with Structured Logging",
        body="This is a test email to verify structured logging.",
        attachments=[temp_file_path],
        dry_run=True
    )
    
    # Print the result in a structured way
    print("Result structure:")
    print(f"  success: {result['success']}")
    print(f"  status: {result['status']}")
    print(f"  recipients: {result['recipients']}")
    print(f"  recipient_statuses: {json.dumps(result['recipient_statuses'], indent=2)}")
    print(f"  message: {result['message']}")
    
    # Test 2: Invalid email address
    print("\nTest 2: Invalid email address")
    result = email_service._run(
        action="send",
        to=["valid@example.com", "invalid-email"],
        subject="Test Email with Invalid Address",
        body="This email tests invalid email address handling."
    )
    
    # Print the result in a structured way
    print("Result structure:")
    print(f"  success: {result['success']}")
    print(f"  status: {result['status']}")
    print(f"  error: {result.get('error', 'No error')}")
    print(f"  invalid_emails: {result.get('invalid_emails', [])}")
    
    # Test 3: Missing API key
    print("\nTest 3: Missing API key")
    
    # Save original API key
    original_api_key = os.environ.get("SENDGRID_API_KEY")
    
    # Temporarily remove API key from environment
    if "SENDGRID_API_KEY" in os.environ:
        del os.environ["SENDGRID_API_KEY"]
    
    # Test sending without API key
    result = email_service._send_email(
        to=["test@example.com"],
        subject="Test Email - Missing API Key",
        body="This email tests missing API key handling.",
        attachments=None,
        dry_run=False
    )
    
    # Print the result in a structured way
    print("Result structure:")
    print(f"  success: {result['success']}")
    print(f"  status: {result['status']}")
    print(f"  error: {result.get('error', 'No error')}")
    
    # Restore original API key if it existed
    if original_api_key:
        os.environ["SENDGRID_API_KEY"] = original_api_key
    
    # Test 4: Helper method - send_reminder
    print("\nTest 4: Helper method - send_reminder")
    result = email_service.send_reminder(
        to=["test@example.com"],
        meeting_date="2025-09-15",
        meeting_type="regular",
        submission_deadline="2025-09-10",
        context={
            "meetingDate": "2025-09-15",
            "meetingType": "regular"
        },
        dry_run=True
    )
    
    # Print the result in a structured way
    print("Result structure:")
    print(f"  success: {result['success']}")
    print(f"  status: {result['status']}")
    print(f"  email_type: {result.get('email_type', 'Unknown')}")
    print(f"  meeting_date: {result.get('meeting_date', 'Unknown')}")
    print(f"  meeting_type: {result.get('meeting_type', 'Unknown')}")
    print(f"  agenda_attached: {result.get('agenda_attached', False)}")
    print(f"  recipient_statuses: {json.dumps(result.get('recipient_statuses', []), indent=2)}")
    
    # Test 5: Helper method - distribute_minutes with non-existent file
    print("\nTest 5: Helper method - distribute_minutes with non-existent file")
    result = email_service.distribute_minutes(
        to=["test@example.com"],
        minutes_file="non_existent_file.pdf",
        meeting_date="2025-09-15",
        meeting_type="regular",
        review_deadline="2025-09-20",
        dry_run=True
    )
    
    # Print the result in a structured way
    print("Result structure:")
    print(f"  success: {result['success']}")
    print(f"  status: {result['status']}")
    print(f"  email_type: {result.get('email_type', 'Unknown')}")
    print(f"  minutes_found: {result.get('minutes_found', True)}")
    print(f"  error: {result.get('error', 'No error')}")
    
    # Clean up temporary file
    if os.path.exists(temp_file_path):
        os.unlink(temp_file_path)
    
    print("\nAll tests completed.")

if __name__ == "__main__":
    test_structured_logging()