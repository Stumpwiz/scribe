"""
Test script for the updated ReminderAgent task implementation.

This script tests the updated send_meeting_notification_workflow function
to ensure it meets all requirements from the issue description.
"""

import sys
import os

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import logging
import asyncio
from pathlib import Path
from pprint import pprint

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

# Import the task implementation
from scribe.tasks.reminder_tasks import send_meeting_notification_workflow

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

class MockTask:
    """Mock Task class for testing."""
    def __init__(self, context):
        self.context = context

class MockAgent:
    """Mock Agent class for testing."""
    def __init__(self, name="TestAgent"):
        self.name = name

async def test_reminder_workflow():
    """Test the send_meeting_notification_workflow function."""
    logger.info("Starting test of updated send_meeting_notification_workflow")
    
    # Create a mock task with test context
    test_context = {
        "meetingDate": "2025-08-07",
        "meetingType": "regular",
        "meetingTime": "7:30 PM",
        "location": "Conference Room A",
        "email_recipients": ["user4@example.com"]
    }
    
    mock_task = MockTask(test_context)
    mock_agent = MockAgent()
    
    # Call the workflow function
    try:
        result = await send_meeting_notification_workflow(None, mock_agent, mock_task)
        
        # Verify the result is a dictionary (structured output from EmailService)
        if isinstance(result, dict):
            logger.info("✅ Result is a dictionary as required")
        else:
            logger.error(f"❌ Result is not a dictionary: {type(result)}")
        
        # Print the result for inspection
        logger.info("Workflow result:")
        pprint(result)
        
        # Verify key requirements
        requirements_met = True
        
        # Check if agenda was generated
        if "agenda generation" in str(result).lower():
            logger.info("✅ Agenda generation was attempted")
        else:
            logger.warning("⚠️ No indication of agenda generation in result")
        
        # Check if email was sent with required arguments
        if result.get("success") is True:
            logger.info("✅ Email was sent successfully")
        else:
            logger.error("❌ Email sending failed")
            requirements_met = False
        
        # Overall assessment
        if requirements_met:
            logger.info("✅ All requirements appear to be met")
        else:
            logger.warning("⚠️ Some requirements may not be met")
        
        return result
    except Exception as e:
        logger.error(f"Error in workflow: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def main():
    """Run the test."""
    logger.info("Starting test script for updated ReminderAgent implementation")
    
    # Run the async test function
    result = asyncio.run(test_reminder_workflow())
    
    if result:
        logger.info("Test completed with result")
    else:
        logger.error("Test failed with no result")

if __name__ == "__main__":
    main()
