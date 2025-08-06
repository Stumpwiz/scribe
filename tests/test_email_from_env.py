"""
Test script for verifying the EMAIL_FROM environment variable configuration.

This script tests that the EmailService correctly uses the EMAIL_FROM
environment variable and raises appropriate errors when it's missing.
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

def test_email_from_env():
    """Test the EmailService with EMAIL_FROM environment variable."""
    print("Testing EmailService with EMAIL_FROM environment variable...")
    
    # Test 1: With EMAIL_FROM set
    print("\nTest 1: With EMAIL_FROM set")
    
    # Save the current EMAIL_FROM value
    original_email_from = os.environ.get("EMAIL_FROM")
    
    # Set a test value
    test_email = "test@example.com"
    os.environ["EMAIL_FROM"] = test_email
    
    # Reload the module to reinitialize DEFAULT_SENDER
    import importlib
    import scribe.tools.email_service
    importlib.reload(scribe.tools.email_service)
    
    # Create the email service
    from scribe.tools.email_service import EmailService
    email_service = EmailService()
    
    # Test sending an email (dry run)
    result = email_service._send_email(
        to=["recipient@example.com"],
        subject="Test Email From Environment Variable",
        body="This is a test email to verify EMAIL_FROM environment variable.",
        attachments=None,
        dry_run=True
    )
    
    # Print the result
    print(f"Result with EMAIL_FROM={test_email}:")
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
    
    # Test sending an email (dry run)
    result = email_service._send_email(
        to=["recipient@example.com"],
        subject="Test Email Without Environment Variable",
        body="This email should fail due to missing EMAIL_FROM.",
        attachments=None,
        dry_run=True
    )
    
    # Print the result
    print(f"Result without EMAIL_FROM:")
    print(f"  success: {result['success']}")
    print(f"  status: {result['status']}")
    print(f"  error: {result.get('error', 'No error')}")
    
    # Restore the original EMAIL_FROM if it existed
    if original_email_from:
        os.environ["EMAIL_FROM"] = original_email_from
    elif "EMAIL_FROM" in os.environ:
        del os.environ["EMAIL_FROM"]
    
    print("\nTest completed.")

if __name__ == "__main__":
    test_email_from_env()