"""
Test script for verifying the complete EMAIL_FROM solution.

This script tests that:
1. The EmailService correctly uses the EMAIL_FROM environment variable
2. The error handling works when EMAIL_FROM is missing
3. The sender address is consistent across all email sending methods
"""

import os
import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), \'..\')))
from pathlib import Path

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from scribe.tools.email_service import EmailService

def test_email_from_solution():
    """Test the complete EMAIL_FROM solution."""
    print("Testing complete EMAIL_FROM solution...")
    
    # Save the current EMAIL_FROM value
    original_email_from = os.environ.get("EMAIL_FROM")
    
    try:
        # Test 1: With EMAIL_FROM set
        print("\nTest 1: With EMAIL_FROM set to geo@loyola.edu")
        
        # Set EMAIL_FROM to the required value
        os.environ["EMAIL_FROM"] = "geo@loyola.edu"
        
        # Reload the module to reinitialize DEFAULT_SENDER
        import importlib
        import scribe.tools.email_service
        importlib.reload(scribe.tools.email_service)
        
        # Create the email service
        from scribe.tools.email_service import EmailService
        email_service = EmailService()
        
        # Test basic email sending (dry run)
        result = email_service._send_email(
            to=["recipient@example.com"],
            subject="Test Email From Environment Variable",
            body="This is a test email to verify EMAIL_FROM environment variable.",
            attachments=None,
            dry_run=True
        )
        
        # Print the result
        print(f"Basic email result:")
        print(f"  success: {result['success']}")
        print(f"  status: {result['status']}")
        print(f"  error: {result.get('error', 'No error')}")
        
        # Test send_reminder method (dry run)
        result = email_service.send_reminder(
            to=["recipient@example.com"],
            meeting_date="2025-08-15",
            meeting_type="regular",
            context={
                "meetingDate": "2025-08-15",
                "meetingType": "regular"
            },
            dry_run=True
        )

        # Print the result
        print(f"\nReminder email result:")
        print(f"  success: {result['success']}")
        print(f"  status: {result['status']}")
        print(f"  error: {result.get('error', 'No error')}")
        
        # Test 2: Without EMAIL_FROM set
        print("\nTest 2: Without EMAIL_FROM set")
        
        # Remove EMAIL_FROM from environment
        if "EMAIL_FROM" in os.environ:
            del os.environ["EMAIL_FROM"]
        
        # Reload the module to reinitialize DEFAULT_SENDER
        importlib.reload(scribe.tools.email_service)
        
        # Create a new email service
        from scribe.tools.email_service import EmailService
        email_service = EmailService()
        
        # Test basic email sending (dry run)
        result = email_service._send_email(
            to=["recipient@example.com"],
            subject="Test Email Without Environment Variable",
            body="This email should fail due to missing EMAIL_FROM.",
            attachments=None,
            dry_run=True
        )
        
        # Print the result
        print(f"Basic email result without EMAIL_FROM:")
        print(f"  success: {result['success']}")
        print(f"  status: {result['status']}")
        print(f"  error: {result.get('error', 'No error')}")
        
        # Test send_reminder method (dry run)
        result = email_service.send_reminder(
            to=["recipient@example.com"],
            meeting_date="2025-08-15",
            meeting_type="regular",
            context={
                "meetingDate": "2025-08-15",
                "meetingType": "regular"
            },
            dry_run=True
        )
        
        # Print the result
        print(f"\nReminder email result without EMAIL_FROM:")
        print(f"  success: {result['success']}")
        print(f"  status: {result['status']}")
        print(f"  error: {result.get('error', 'No error')}")
        
    finally:
        # Restore the original EMAIL_FROM if it existed
        if original_email_from:
            os.environ["EMAIL_FROM"] = original_email_from
        elif "EMAIL_FROM" in os.environ:
            del os.environ["EMAIL_FROM"]
    
    print("\nTest completed.")

if __name__ == "__main__":
    test_email_from_solution()