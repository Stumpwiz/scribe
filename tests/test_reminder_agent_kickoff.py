import logging
import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), \'..\')))
import os
from datetime import date, timedelta

# Configure logging to output to console
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout)

logger = logging.getLogger(__name__)

# Mock crew.kickoff function to avoid actual execution
def mock_kickoff(**kwargs):
    logger.info("Mock crew.kickoff called with:")
    for key, value in kwargs.items():
        logger.info(f"  {key}: {value}")
    return {"success": True, "message": "Mock execution successful"}

# Test function to simulate the reminder route functionality
def test_reminder_agent_kickoff():
    # Get a future meeting date (using the current date from the issue description: 2025-08-04)
    meeting_date = date(2025, 8, 7)  # Using the date from the issue description
    meeting_type = "council"  # Example meeting type
    
    # Example old and new business items
    old_business = "Review previous minutes\nFinalize budget"
    new_business = "Discuss new committee proposal\nPlan holiday event"
    
    # Example recipients
    recipients = ["geo@loyola.edu"]
    
    # Construct inputs dictionary as specified in the issue
    inputs = {
        "meeting_date": str(meeting_date),
        "meeting_type": meeting_type,
        "old_business_items": old_business.split("\n") if old_business else [],
        "new_business_items": new_business.split("\n") if new_business else [],
        "email_recipients": recipients,
    }
    
    # Create the kickoff context with agent, task, and inputs
    kickoff_context = {
        "agent": "ReminderAgent",
        "task": "send_meeting_notification",
        "inputs": inputs
    }
    
    # Add additional parameters needed by the system
    submission_deadline = meeting_date - timedelta(days=5)
    kickoff_context["inputs"].update({
        "submission_deadline": str(submission_deadline),
        "review_deadline": str(submission_deadline),
    })
    
    # Log ReminderAgent invocation details with full context
    logger.info(f"Kicking off ReminderAgent with context: {kickoff_context}")
    
    # Add more detailed debug logging
    logger.debug(f"Agent: {kickoff_context['agent']}")
    logger.debug(f"Task: {kickoff_context['task']}")
    logger.debug(f"Meeting date: {kickoff_context['inputs']['meeting_date']}")
    logger.debug(f"Meeting type: {kickoff_context['inputs']['meeting_type']}")
    logger.debug(f"Old business items: {kickoff_context['inputs']['old_business_items']}")
    logger.debug(f"New business items: {kickoff_context['inputs']['new_business_items']}")
    logger.debug(f"Email recipients: {kickoff_context['inputs']['email_recipients']}")
    
    # Call the mock kickoff function
    results = mock_kickoff(**kickoff_context)
    
    logger.info(f"Results: {results}")
    return results

if __name__ == "__main__":
    logger.info("Starting test of ReminderAgent kickoff...")
    test_results = test_reminder_agent_kickoff()
    logger.info("Test completed successfully!")