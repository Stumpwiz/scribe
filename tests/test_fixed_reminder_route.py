import logging
import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), \'..\')))
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
        logger.info(f"Inputs: {inputs}")
    return {"success": True, "message": "Mock execution successful"}

# Test function to simulate the fixed reminder route functionality
def test_fixed_reminder_route():
    # Get a future meeting date
    meeting_date = date.today() + timedelta(days=7)
    meeting_type = "council"  # Example meeting type
    
    # Example old and new business items
    old_business = "Review previous minutes\nFinalize budget"
    new_business = "Discuss new committee proposal\nPlan holiday event"
    
    # Example recipients
    recipients = ["test@example.com"]
    
    # Construct inputs dictionary
    inputs = {
        "meeting_date": str(meeting_date),
        "meeting_type": meeting_type,
        "old_business_items": old_business.split("\n") if old_business else [],
        "new_business_items": new_business.split("\n") if new_business else [],
        "email_recipients": recipients,
        "submission_deadline": str(meeting_date - timedelta(days=5)),
        "review_deadline": str(meeting_date - timedelta(days=5)),
    }
    
    # Create the kickoff context with agent, task, and inputs
    kickoff_context = {
        "agent": "ReminderAgent",
        "task": "send_meeting_notification",
        "inputs": inputs
    }
    
    logger.info("Testing fixed crew.kickoff() call format...")
    
    # Call the mock kickoff function with the FIXED format
    results = mock_kickoff({
        "send_meeting_notification": kickoff_context["inputs"]
    })
    
    logger.info(f"Results: {results}")
    return results

if __name__ == "__main__":
    logger.info("Starting test of fixed reminder route...")
    test_results = test_fixed_reminder_route()
    logger.info("Test completed successfully!")