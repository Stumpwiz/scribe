import logging
import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), \'..\')))
import os
from pathlib import Path

# Configure logging to output to console
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout)

logger = logging.getLogger(__name__)

# Import the EmailService class
from scribe.tools.email_service import EmailService

def test_email_with_attachment():
    """
    Test sending an email with an agenda PDF attachment.
    This test verifies that the EmailService correctly attaches an agenda PDF
    if it exists at the expected location.
    """
    logger.info("Starting test of email with attachment...")
    
    # Create an instance of EmailService
    email_service = EmailService()
    
    # Test parameters
    meeting_type = "regular"
    meeting_date = "2025-08-07"
    recipients = ["test@example.com"]  # Use a test email address
    
    # Ensure the output directory exists
    agenda_dir = Path("src/scribe/output/agendas")
    agenda_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a dummy agenda PDF for testing
    agenda_path = agenda_dir / f"agenda_{meeting_type}.pdf"
    
    # Create a simple PDF file for testing if it doesn't exist
    if not agenda_path.exists():
        logger.info(f"Creating dummy agenda PDF at {agenda_path}")
        with open(agenda_path, 'w') as f:
            f.write("%PDF-1.7\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 21 >>\nstream\nBT /F1 12 Tf 100 700 Td (Test PDF) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000010 00000 n\n0000000059 00000 n\n0000000118 00000 n\n0000000217 00000 n\ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n287\n%%EOF")
    
    # Log the file details
    if agenda_path.exists():
        file_size = agenda_path.stat().st_size
        logger.info(f"Test agenda PDF exists: {agenda_path}, size={file_size} bytes")
    else:
        logger.error(f"Failed to create test agenda PDF at {agenda_path}")
        return False
    
    # Send a test email with dry_run=True to avoid actually sending
    logger.info("Sending test email with attachment...")
    result = email_service.send_reminder(
        to=recipients,
        meeting_date=meeting_date,
        meeting_type=meeting_type,
        dry_run=True
    )
    
    # Check if the agenda was attached
    if result.get("agenda_attached", False):
        logger.info("Success: Agenda PDF was attached to the email")
        logger.info(f"Agenda path: {result.get('agenda_path')}")
    else:
        logger.error("Error: Agenda PDF was not attached to the email")
        logger.error(f"Error message: {result.get('agenda_error')}")
        return False
    
    logger.info("Test completed successfully!")
    return True

def test_email_without_attachment():
    """
    Test sending an email without an agenda PDF attachment.
    This test verifies that the EmailService gracefully handles the case
    where the agenda PDF doesn't exist.
    """
    logger.info("Starting test of email without attachment...")
    
    # Create an instance of EmailService
    email_service = EmailService()
    
    # Test parameters
    meeting_type = "nonexistent"  # Use a meeting type that doesn't have an agenda
    meeting_date = "2025-08-07"
    recipients = ["test@example.com"]  # Use a test email address
    
    # Send a test email with dry_run=True to avoid actually sending
    logger.info("Sending test email without attachment...")
    result = email_service.send_reminder(
        to=recipients,
        meeting_date=meeting_date,
        meeting_type=meeting_type,
        dry_run=True
    )
    
    # Check that the email was prepared successfully even without an attachment
    if result.get("success", False):
        logger.info("Success: Email was prepared successfully without attachment")
        logger.info(f"Agenda attached: {result.get('agenda_attached', False)}")
        logger.info(f"Error message: {result.get('agenda_error', 'No error')}")
    else:
        logger.error("Error: Email preparation failed")
        logger.error(f"Error message: {result.get('error', 'Unknown error')}")
        return False
    
    logger.info("Test completed successfully!")
    return True

if __name__ == "__main__":
    logger.info("Starting email attachment tests...")
    
    # Run test with attachment
    with_attachment_result = test_email_with_attachment()
    
    # Run test without attachment
    without_attachment_result = test_email_without_attachment()
    
    # Report overall results
    if with_attachment_result and without_attachment_result:
        logger.info("All tests passed successfully!")
    else:
        logger.error("Some tests failed!")