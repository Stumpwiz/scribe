# test_run_reminder_agent_test.py

import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure 'src' is on the import path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from scribe.crew import crew  # Import the crew instance that loads agents from YAML

def run_reminder_agent_test():
    load_dotenv()

    # Customize as needed
    meeting_type = "regular"
    meeting_date = "2025-08-07"
    location = "Chapel"
    submission_deadline = "2025-08-01"

    # Compose task input
    context = {
        "meetingType": meeting_type,
        "meetingDate": meeting_date,
        "location": location,
        "submissionDeadline": submission_deadline
    }

    # Use the crew system to run the task
    print("🔄 Running ReminderAgent via Crew...")
    result = crew.kickoff({
        "send_meeting_notification": context
    })
    print("\n✅ Agent completed task:\n", result)

if __name__ == "__main__":
    run_reminder_agent_test()
