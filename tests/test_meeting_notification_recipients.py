import logging
import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), \'..\')))
from pathlib import Path
import json
import os
import shutil

# Configure logging to output to console
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout)

logger = logging.getLogger(__name__)

# Import the necessary modules
from scribe.tools.meeting_notification_tool import MeetingNotificationTool

def setup_test_files(empty=False):
    """
    Set up test JSON files for recipients.
    
    Args:
        empty (bool): If True, create empty recipient lists
    """
    # Create backup of original files if they exist
    recipients_dir = Path("src/scribe/assets/recipients")
    council_members_path = recipients_dir / "council_members.json"
    committee_chairs_path = recipients_dir / "committee_chairs.json"
    
    # Create backups
    if council_members_path.exists():
        shutil.copy(council_members_path, council_members_path.with_suffix(".json.bak"))
    
    if committee_chairs_path.exists():
        shutil.copy(committee_chairs_path, committee_chairs_path.with_suffix(".json.bak"))
    
    # Create test files
    if empty:
        # Create empty recipient lists
        with open(council_members_path, 'w') as f:
            json.dump([], f)
        
        with open(committee_chairs_path, 'w') as f:
            json.dump([], f)
    else:
        # Create test recipient lists
        with open(council_members_path, 'w') as f:
            json.dump(["council1@example.com", "council2@example.com"], f)
        
        with open(committee_chairs_path, 'w') as f:
            json.dump(["chair1@example.com", "chair2@example.com"], f)

def restore_original_files():
    """Restore the original recipient files from backups."""
    recipients_dir = Path("src/scribe/assets/recipients")
    council_members_path = recipients_dir / "council_members.json"
    committee_chairs_path = recipients_dir / "committee_chairs.json"
    
    # Restore from backups if they exist
    council_backup = council_members_path.with_suffix(".json.bak")
    if council_backup.exists():
        shutil.copy(council_backup, council_members_path)
        os.remove(council_backup)
    
    committee_backup = committee_chairs_path.with_suffix(".json.bak")
    if committee_backup.exists():
        shutil.copy(committee_backup, committee_chairs_path)
        os.remove(committee_backup)

def test_get_recipients_regular():
    """Test getting recipients for a regular meeting."""
    try:
        # Set up test files with non-empty lists
        setup_test_files(empty=False)
        
        # Create an instance of MeetingNotificationTool
        tool = MeetingNotificationTool()
        
        # Get recipients for a regular meeting
        recipients = tool.get_recipients("regular")
        
        # Log the results
        logger.info(f"Recipients for regular meeting: {recipients}")
        logger.info(f"Number of recipients: {len(recipients)}")
        
        # Verify that only council members are included
        assert len(recipients) == 2, f"Expected 2 recipients, got {len(recipients)}"
        assert all(email.startswith("council") for email in recipients), "Expected only council member emails"
        
        logger.info("Test passed: Regular meeting recipients are correct")
        return True
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return False
    finally:
        # Restore original files
        restore_original_files()

def test_get_recipients_open():
    """Test getting recipients for an open meeting."""
    try:
        # Set up test files with non-empty lists
        setup_test_files(empty=False)
        
        # Create an instance of MeetingNotificationTool
        tool = MeetingNotificationTool()
        
        # Get recipients for an open meeting
        recipients = tool.get_recipients("open")
        
        # Log the results
        logger.info(f"Recipients for open meeting: {recipients}")
        logger.info(f"Number of recipients: {len(recipients)}")
        
        # Verify that both council members and committee chairs are included
        assert len(recipients) == 4, f"Expected 4 recipients, got {len(recipients)}"
        
        # Check that we have both types of emails
        council_emails = [email for email in recipients if email.startswith("council")]
        chair_emails = [email for email in recipients if email.startswith("chair")]
        
        assert len(council_emails) == 2, f"Expected 2 council emails, got {len(council_emails)}"
        assert len(chair_emails) == 2, f"Expected 2 chair emails, got {len(chair_emails)}"
        
        logger.info("Test passed: Open meeting recipients are correct")
        return True
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return False
    finally:
        # Restore original files
        restore_original_files()

def test_get_recipients_empty():
    """Test getting recipients when the JSON files are empty."""
    try:
        # Set up test files with empty lists
        setup_test_files(empty=True)
        
        # Create an instance of MeetingNotificationTool
        tool = MeetingNotificationTool()
        
        # Get recipients for a regular meeting
        recipients = tool.get_recipients("regular")
        
        # Log the results
        logger.info(f"Recipients when JSON files are empty: {recipients}")
        logger.info(f"Number of recipients: {len(recipients)}")
        
        # Verify that the fallback email is used
        assert len(recipients) == 1, f"Expected 1 recipient (fallback), got {len(recipients)}"
        assert recipients[0] == "geo@loyola.edu", f"Expected fallback email 'geo@loyola.edu', got {recipients[0]}"
        
        logger.info("Test passed: Fallback email is used when JSON files are empty")
        return True
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return False
    finally:
        # Restore original files
        restore_original_files()

def test_get_recipients_missing_files():
    """Test getting recipients when the JSON files are missing."""
    try:
        # Backup and remove the JSON files
        recipients_dir = Path("src/scribe/assets/recipients")
        council_members_path = recipients_dir / "council_members.json"
        committee_chairs_path = recipients_dir / "committee_chairs.json"
        
        # Create backups
        if council_members_path.exists():
            shutil.copy(council_members_path, council_members_path.with_suffix(".json.bak"))
            os.remove(council_members_path)
        
        if committee_chairs_path.exists():
            shutil.copy(committee_chairs_path, committee_chairs_path.with_suffix(".json.bak"))
            os.remove(committee_chairs_path)
        
        # Create an instance of MeetingNotificationTool
        tool = MeetingNotificationTool()
        
        # Get recipients for a regular meeting
        recipients = tool.get_recipients("regular")
        
        # Log the results
        logger.info(f"Recipients when JSON files are missing: {recipients}")
        logger.info(f"Number of recipients: {len(recipients)}")
        
        # Verify that the fallback email is used
        assert len(recipients) == 1, f"Expected 1 recipient (fallback), got {len(recipients)}"
        assert recipients[0] == "geo@loyola.edu", f"Expected fallback email 'geo@loyola.edu', got {recipients[0]}"
        
        logger.info("Test passed: Fallback email is used when JSON files are missing")
        return True
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return False
    finally:
        # Restore original files
        restore_original_files()

if __name__ == "__main__":
    logger.info("Starting tests for recipient loading...")
    
    # Run the tests
    regular_test = test_get_recipients_regular()
    open_test = test_get_recipients_open()
    empty_test = test_get_recipients_empty()
    missing_test = test_get_recipients_missing_files()
    
    # Report overall results
    if regular_test and open_test and empty_test and missing_test:
        logger.info("All tests passed successfully!")
    else:
        logger.error("Some tests failed!")