"""
Test script for the updated EmailService using SMTP with SendGrid.

This script tests the functionality of the EmailService class after
updating it to use SMTP with SendGrid instead of the SendGrid API.
"""

import os
import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from pathlib import Path

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from scribe.tools.email_service import EmailService

def test_smtp_email_service():
    """Test the EmailService with SMTP implementation."""
    email_service = EmailService()
    
    print("Testing EmailService with SMTP implementation...")
    
    # Check if SENDGRID_API_KEY is set in the environment
    api_key = os.environ.get("SENDGRID_API_KEY")
    if not api_key:
        print("WARNING: SENDGRID_API_KEY environment variable is not set.")
        print("Tests will run in dry_run mode only.")
        print("Set this environment variable to test actual email sending.")
        print()
    
    # Test 1: Send a simple email (dry run)
    print("\nTest 1: Send a simple email (dry run)")
    result = email_service._send_email(
        to=["test@example.com"],
        subject="Test Email from Scribe SMTP Service",
        body="This is a test email sent from the Scribe project using SMTP.",
        attachments=None,
        dry_run=True
    )
    print(f"Result: {result}")
    
    # Test 2: Send an email with attachment (dry run)
    print("\nTest 2: Send an email with attachment (dry run)")
    
    # Create a temporary text file for testing attachment
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as temp:
        temp.write("This is a test attachment for SMTP email.")
        temp_file_path = temp.name
    
    result = email_service._send_email(
        to=["test@example.com"],
        subject="Test Email with Attachment from SMTP Service",
        body="This is a test email with an attachment sent using SMTP.",
        attachments=[temp_file_path],
        dry_run=True
    )
    print(f"Result: {result}")
    
    # Test 3: Test error handling for missing API key
    print("\nTest 3: Test error handling for missing API key")
    
    # Save original API key
    original_api_key = os.environ.get("SENDGRID_API_KEY")
    
    # Temporarily remove API key from environment
    if "SENDGRID_API_KEY" in os.environ:
        del os.environ["SENDGRID_API_KEY"]
    
    # Test sending without API key
    result = email_service._send_email(
        to=["test@example.com"],
        subject="Test Email - Missing API Key",
        body="This email should not be sent due to missing API key.",
        attachments=None,
        dry_run=False
    )
    print(f"Result: {result}")
    
    # Restore original API key if it existed
    if original_api_key:
        os.environ["SENDGRID_API_KEY"] = original_api_key
    
    # Test 4: Test with invalid email address
    print("\nTest 4: Test with invalid email address")
    result = email_service._run(
        action="send",
        to=["invalid-email"],
        subject="Test Email with Invalid Address",
        body="This email should not be sent due to invalid email address.",
        dry_run=True
    )
    print(f"Result: {result}")
    
    # Test 5: Test with multiple recipients
    print("\nTest 5: Test with multiple recipients")
    result = email_service._send_email(
        to=["recipient1@example.com", "recipient2@example.com"],
        subject="Test Email with Multiple Recipients",
        body="This is a test email sent to multiple recipients.",
        attachments=None,
        dry_run=True
    )
    print(f"Result: {result}")
    
    # Clean up temporary file
    if os.path.exists(temp_file_path):
        os.unlink(temp_file_path)
    
    print("\nAll tests completed.")

if __name__ == "__main__":
    test_smtp_email_service()