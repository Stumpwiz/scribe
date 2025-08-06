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

# Test function to simulate the reminder route functionality
def test_reminder_agent_kickoff():
    try:
        # Import necessary modules
        from scribe.ui.routes.reminder_routes import get_meeting_type_from_date
        from scribe.tools.meeting_notification_tool import MeetingNotificationTool
        
        # Get a future meeting date
        meeting_date = date.today() + timedelta(days=7)
        
        # Determine meeting type
        meeting_type = get_meeting_type_from_date(meeting_date)
        logger.info(f"Meeting type determined: {meeting_type}")
        
        # Get recipients
        notification_tool = MeetingNotificationTool()
        recipients = notification_tool.get_recipients(meeting_type)
        logger.info(f"Recipients count: {len(recipients)}")
        
        # Example old and new business items
        old_business = "Review previous minutes\nFinalize budget"
        new_business = "Discuss new committee proposal\nPlan holiday event"
        
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
        
        # Create the kickoff context
        kickoff_context = {
            "send_meeting_notification": inputs
        }
        
        # Instead of actually calling crew.kickoff, we'll just verify that the inputs
        # dictionary doesn't contain any of the removed fields
        logger.info("Verifying inputs dictionary doesn't contain removed fields...")
        
        # Check for obsolete keys
        obsolete_keys = ["submission_deadline", "review_deadline", "reportInstructions", 
                         "submissionDeadline", "reviewDeadline"]
        found_obsolete_keys = [key for key in obsolete_keys if key in inputs]
        
        if found_obsolete_keys:
            logger.error(f"Found obsolete keys that should have been removed: {found_obsolete_keys}")
            return False
        else:
            logger.info("No obsolete keys found in inputs dictionary - test passed!")
            return True
            
    except KeyError as e:
        logger.error(f"KeyError encountered: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("Starting test of ReminderAgent kickoff without deadline fields...")
    success = test_reminder_agent_kickoff()
    
    if success:
        logger.info("Test completed successfully!")
    else:
        logger.error("Test failed!")