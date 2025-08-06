"""
Test script for the ReminderAgent task workflow.

This script tests the new implementation of the send_meeting_notification_workflow
to ensure it correctly follows the required steps:
1. Call MeetingAgendaGeneratorTool
2. Extract pdfPath
3. Render email template
4. Send email with attachment
"""

import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), \'..\')))
import os
import logging
import asyncio
from pathlib import Path

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
    logger.info("Starting test of send_meeting_notification_workflow")
    
    # Create a mock task with test context
    test_context = {
        "meetingDate": "2025-08-07",
        "meetingType": "regular",
        "meetingTime": "7:30 PM",
        "location": "Conference Room A",
        "email_recipients": ["georgemartinwright@gmail.com"]
    }
    
    mock_task = MockTask(test_context)
    mock_agent = MockAgent()
    
    # Call the workflow function
    try:
        result = await send_meeting_notification_workflow(None, mock_agent, mock_task)
        logger.info(f"Workflow completed with result: {result}")
        return True
    except Exception as e:
        logger.error(f"Error in workflow: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Run the test."""
    logger.info("Starting test script")
    
    # Run the async test function
    success = asyncio.run(test_reminder_workflow())
    
    if success:
        logger.info("Test completed successfully!")
    else:
        logger.error("Test failed!")

if __name__ == "__main__":
    main()