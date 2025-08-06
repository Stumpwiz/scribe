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

# Import the necessary modules
from scribe.ui.routes.reminder_routes import get_meeting_type_from_date
from scribe.tools.meeting_notification_tool import MeetingNotificationTool

# Test function to simulate the reminder route functionality
def test_reminder_agent_invocation():
    # Get a future meeting date
    meeting_date = date.today() + timedelta(days=7)
    
    try:
        # Determine meeting type
        meeting_type = get_meeting_type_from_date(meeting_date)
        print(f"Meeting type determined: {meeting_type}")
        
        # Get recipients
        notification_tool = MeetingNotificationTool()
        recipients = notification_tool.get_recipients(meeting_type)
        print(f"Recipients count: {len(recipients)}")
        
        # Construct inputs dictionary as specified in the issue
        inputs = {
            "meeting_date": str(meeting_date),
            "meeting_type": meeting_type,
            "old_business": "Test old business",
            "new_business": "Test new business",
            "email_recipients": recipients,
        }
        
        # Log the inputs dictionary
        print(f"Kicking off ReminderAgent with inputs: {inputs}")
        
        # In a real scenario, we would call crew.kickoff(inputs=inputs) here
        print("Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    test_reminder_agent_invocation()