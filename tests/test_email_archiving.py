"""
Test script for the email archiving functionality.

This script tests the archiving of email body and agenda PDFs
after successful email sending.
"""

import os
import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), \'..\')))
import shutil
from pathlib import Path
import tempfile
from datetime import datetime

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from scribe.tools.email_service import EmailService

# Mock the _send_email method to always return success without actually sending
def mock_send_email(self, to, subject, body, attachments, dry_run=False):
    """Mock implementation that always returns success without sending."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "success": True,
        "message": f"[MOCK] Email sent at {timestamp}",
        "recipients": to or [],
        "subject": subject or "",
        "status": "sent",  # Important: use "sent" to trigger archiving
        "timestamp": timestamp,
        "recipient_statuses": [{"email": email, "status": "sent"} for email in (to or [])]
    }

def test_email_archiving():
    """Test the email archiving functionality of the EmailService class."""
    email_service = EmailService()
    
    # Replace the _send_email method with our mock version
    # Save the original method to restore it later
    original_send_email = email_service._send_email
    email_service._send_email = mock_send_email.__get__(email_service)
    
    print("Testing email archiving functionality...")
    
    # Create a temporary directory for testing
    archive_dir = Path("instance/reminders_archive")
    if archive_dir.exists():
        print(f"Cleaning up existing archive directory: {archive_dir}")
        # Remove all files in the directory but keep the directory
        for file_path in archive_dir.glob("*"):
            if file_path.is_file():
                file_path.unlink()
    
    # Create a temporary agenda PDF for testing
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, mode="wb") as temp:
        temp.write(b"%PDF-1.5\n%Test PDF content")
        temp_pdf_path = temp.name
    
    # Copy the temp PDF to a location that looks like an agenda
    os.makedirs("src/scribe/output/agendas", exist_ok=True)
    agenda_path = "src/scribe/output/agendas/agenda_2025-08-07_regular.pdf"
    shutil.copy(temp_pdf_path, agenda_path)
    
    print(f"Created test agenda PDF: {agenda_path}")
    
    # Test 1: Regular meeting with agenda
    print("\nTest 1: Regular meeting with agenda")
    result = email_service.send_reminder(
        to=["test@example.com"],
        meeting_date="2025-08-07",
        meeting_type="regular",
        submission_deadline="2025-08-01",
        context={
            "meetingDate": "2025-08-07",
            "meetingType": "regular"
        },
        dry_run=False  # Set to False to test actual archiving
    )
    
    # Print the result focusing on archiving
    print("Result:")
    print(f"  Email success: {result['success']}")
    print(f"  Email status: {result['status']}")
    if 'archive_success' in result:
        print(f"  Archive success: {result['archive_success']}")
        print(f"  Archived files: {result.get('archived_files', [])}")
    else:
        print("  No archiving performed")
    
    # Test 2: Open meeting without agenda
    print("\nTest 2: Open meeting without agenda")
    result = email_service.send_reminder(
        to=["test@example.com"],
        meeting_date="2025-09-15",
        meeting_type="open",
        submission_deadline="2025-09-10",
        context={
            "meetingDate": "2025-09-15",
            "meetingType": "open"
        },
        dry_run=False  # Set to False to test actual archiving
    )
    
    # Print the result focusing on archiving
    print("Result:")
    print(f"  Email success: {result['success']}")
    print(f"  Email status: {result['status']}")
    if 'archive_success' in result:
        print(f"  Archive success: {result['archive_success']}")
        print(f"  Archived files: {result.get('archived_files', [])}")
    else:
        print("  No archiving performed")
    
    # Test 3: Dry run (should not archive)
    print("\nTest 3: Dry run (should not archive)")
    result = email_service.send_reminder(
        to=["test@example.com"],
        meeting_date="2025-10-15",
        meeting_type="association",
        submission_deadline="2025-10-10",
        context={
            "meetingDate": "2025-10-15",
            "meetingType": "association"
        },
        dry_run=True  # Set to True to test that archiving is skipped
    )
    
    # Print the result focusing on archiving
    print("Result:")
    print(f"  Email success: {result['success']}")
    print(f"  Email status: {result['status']}")
    if 'archive_success' in result:
        print(f"  Archive success: {result['archive_success']}")
        print(f"  Archived files: {result.get('archived_files', [])}")
    else:
        print("  No archiving performed (expected for dry run)")
    
    # List all files in the archive directory
    print("\nFiles in archive directory:")
    if archive_dir.exists():
        for file_path in archive_dir.glob("*"):
            print(f"  {file_path.name}")
    else:
        print("  Archive directory does not exist")
    
    # Clean up
    if os.path.exists(temp_pdf_path):
        os.unlink(temp_pdf_path)
    if os.path.exists(agenda_path):
        os.unlink(agenda_path)
    
    # Restore the original _send_email method
    email_service._send_email = original_send_email
    
    print("\nTest completed.")

if __name__ == "__main__":
    test_email_archiving()