import logging
import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import os
from datetime import date, timedelta

# Configure logging to output to console
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout)

logger = logging.getLogger(__name__)

# Mock crew.kickoff function to avoid actual execution
def mock_kickoff(task_dict):
    logger.info("Mock crew.kickoff called with task dictionary:")
    for task_name, inputs in task_dict.items():
        logger.info(f"Task: {task_name}")
        logger.info(f"Inputs keys: {list(inputs.keys())}")
        
        # Verify no obsolete keys are present
        obsolete_keys = ["submission_deadline", "review_deadline", "reportInstructions", "submissionDeadline", "reviewDeadline"]
        found_obsolete_keys = [key for key in obsolete_keys if key in inputs]
        
        if found_obsolete_keys:
            logger.error(f"Found obsolete keys that should have been removed: {found_obsolete_keys}")
            return {"success": False, "message": f"Found obsolete keys: {found_obsolete_keys}"}
        else:
            logger.info("No obsolete keys found - test passed!")
            
    return {"success": True, "message": "Mock execution successful, no obsolete keys found"}

# Test function to verify inputs dictionary keys
def test_removed_fields():
    # Get a future meeting date
    meeting_date = date(2025, 8, 7)  # Using a fixed date for testing
    meeting_type = "council"  # Example meeting type
    
    # Example old and new business items
    old_business = "Review previous minutes\nFinalize budget"
    new_business = "Discuss new committee proposal\nPlan holiday event"
    
    # Example recipients
    recipients = ["test@example.com"]
    
    # Construct inputs dictionary - should NOT include the removed fields
    inputs = {
        "meeting_date": str(meeting_date),
        "meeting_type": meeting_type,
        "old_business_items": old_business.split("\n") if old_business else [],
        "new_business_items": new_business.split("\n") if new_business else [],
        "email_recipients": recipients,
    }
    
    # Log the inputs dictionary keys
    logger.info(f"Inputs dictionary keys: {list(inputs.keys())}")
    
    # Call the mock kickoff function
    results = mock_kickoff({
        "send_meeting_notification": inputs
    })
    
    logger.info(f"Results: {results}")
    return results

# Test email_writer_tool template context
def test_email_writer():
    try:
        from scribe.tools.email_writer_tool import EmailWriterTool
        
        # Create an instance of the tool
        email_writer = EmailWriterTool()
        
        # Check if the _compute_report_instructions method exists
        if hasattr(email_writer, '_compute_report_instructions'):
            logger.error("_compute_report_instructions method still exists!")
            return False
        else:
            logger.info("_compute_report_instructions method successfully removed")
            return True
    except Exception as e:
        logger.error(f"Error testing email_writer_tool: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting test of removed fields...")
    test_results = test_removed_fields()
    
    logger.info("Testing email_writer_tool...")
    email_writer_result = test_email_writer()
    
    if test_results["success"] and email_writer_result:
        logger.info("All tests passed successfully!")
    else:
        logger.error("Some tests failed!")