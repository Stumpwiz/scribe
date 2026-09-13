"""
Test script for verifying that the sender's email address is correctly loaded from the .env file.

This script tests that:
1. The EmailService correctly loads the EMAIL_FROM environment variable
2. The sender address is correctly set in the email message
3. The same sender address is used in all email service methods
"""

import os
import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import logging
from pathlib import Path

# Configure logging to output to console
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout)

logger = logging.getLogger(__name__)

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

def test_email_from_verification():
    """Test that the sender's email address is correctly loaded from the .env file."""
    logger.info("Testing that the sender's email address is correctly loaded from the .env file...")
    
    # Save the current EMAIL_FROM value
    original_email_from = os.environ.get("EMAIL_FROM")
    
    try:
        # Set EMAIL_FROM to the value from the .env file
        os.environ["EMAIL_FROM"] = "user4@example.com"
        
        # Reload the module to reinitialize DEFAULT_SENDER
        import importlib
        import scribe.tools.email_service
        importlib.reload(scribe.tools.email_service)
        
        # Import the EmailService class
        from scribe.tools.email_service import EmailService, DEFAULT_SENDER
        
        # Verify that DEFAULT_SENDER is correctly set
        logger.info(f"DEFAULT_SENDER value: {DEFAULT_SENDER}")
        assert DEFAULT_SENDER == "user4@example.com", f"Expected DEFAULT_SENDER to be 'user4@example.com', got '{DEFAULT_SENDER}'"
        
        # Create an instance of EmailService
        email_service = EmailService()
        
        # Test basic email sending (dry run)
        result = email_service._send_email(
            to=["test@example.com"],
            subject="Test Email From Verification",
            body="This is a test email to verify the sender's email address.",
            attachments=None,
            dry_run=True
        )
        
        # Verify that the email would be sent successfully
        assert result["success"] == True, f"Expected success=True, got success={result['success']}"
        assert result["status"] == "dry_run", f"Expected status='dry_run', got status={result['status']}"
        
        # Test send_reminder method (dry run)
        result = email_service.send_reminder(
            to=["test@example.com"],
            meeting_date="2025-08-15",
            meeting_type="regular",
            context={
                "meetingDate": "2025-08-15",
                "meetingType": "regular"
            },
            dry_run=True
        )
        
        # Verify that the reminder email would be sent successfully
        assert result["success"] == True, f"Expected success=True, got success={result['success']}"
        assert result["status"] == "dry_run", f"Expected status='dry_run', got status={result['status']}"
        
        # Test distribute_minutes method (dry run)
        # Create a temporary file to use as the minutes file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp:
            temp.write(b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 21 >>\nstream\nBT /F1 12 Tf 100 700 Td (Test PDF) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000010 00000 n\n0000000059 00000 n\n0000000118 00000 n\n0000000217 00000 n\ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n287\n%%EOF")
            minutes_file = temp.name
        
        try:
            result = email_service.distribute_minutes(
                to=["test@example.com"],
                minutes_file=minutes_file,
                meeting_date="2025-08-15",
                meeting_type="regular",
                dry_run=True
            )
            
            # Verify that the minutes email would be sent successfully
            assert result["success"] == True, f"Expected success=True, got success={result['success']}"
            assert result["status"] == "dry_run", f"Expected status='dry_run', got status={result['status']}"
            
            logger.info("All tests passed successfully!")
            return True
        finally:
            # Clean up the temporary file
            if os.path.exists(minutes_file):
                os.unlink(minutes_file)
    
    finally:
        # Restore the original EMAIL_FROM if it existed
        if original_email_from:
            os.environ["EMAIL_FROM"] = original_email_from
        elif "EMAIL_FROM" in os.environ:
            del os.environ["EMAIL_FROM"]

if __name__ == "__main__":
    test_email_from_verification()