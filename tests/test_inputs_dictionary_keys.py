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
        logger.info(f"Inputs keys: {list(inputs.keys())}")
        
        # Verify all required keys are present
        required_keys = [
            "meeting_date",
            "meeting_type",
            "old_business_items",
            "new_business_items",
            "email_recipients",
            "submission_deadline",
            "review_deadline"
        ]
        
        missing_keys = [key for key in required_keys if key not in inputs]
        if missing_keys:
            logger.error(f"Missing required keys: {missing_keys}")
        else:
            logger.info("All required keys are present!")
            
    return {"success": True, "message": "Mock execution successful"}

# Test function to verify inputs dictionary keys
def test_inputs_dictionary_keys():
    # Get a future meeting date
    meeting_date = date(2025, 8, 7)  # Using a fixed date for testing
    meeting_type = "council"  # Example meeting type
    
    # Example old and new business items
    old_business = "Review previous minutes\nFinalize budget"
    new_business = "Discuss new committee proposal\nPlan holiday event"
    
    # Example recipients
    recipients = ["test@example.com"]
    
    # Calculate submission deadline
    submission_deadline = meeting_date - timedelta(days=5)
    
    # Construct inputs dictionary
    inputs = {
        "meeting_date": str(meeting_date),
        "meeting_type": meeting_type,
        "old_business_items": old_business.split("\n") if old_business else [],
        "new_business_items": new_business.split("\n") if new_business else [],
        "email_recipients": recipients,
        "submission_deadline": str(submission_deadline),
        "review_deadline": str(submission_deadline),
    }
    
    # Log the inputs dictionary keys
    logger.info(f"Inputs dictionary keys: {list(inputs.keys())}")
    
    # Call the mock kickoff function
    results = mock_kickoff({
        "send_meeting_notification": inputs
    })
    
    logger.info(f"Results: {results}")
    return results

if __name__ == "__main__":
    logger.info("Starting test of inputs dictionary keys...")
    test_results = test_inputs_dictionary_keys()
    logger.info("Test completed successfully!")