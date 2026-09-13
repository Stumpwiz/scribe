#!/usr/bin/env python3
"""
Simple test script to send a meeting reminder email using database recipients.

This script:
1. Loads recipients from the database
2. Sends a test email via Gmail API
3. Shows what happened
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from scribe.tools.meeting_notification_tool import MeetingNotificationTool
from scribe.tools.email_service import EmailService


def main():
    """Send a test meeting reminder email."""

    print("=" * 70)
    print("📧 TEST: Send Meeting Reminder Email")
    print("=" * 70)

    # Configuration
    meeting_date = "2026-02-05"
    meeting_type = "regular"  # regular, open, or association
    meeting_time = "7:30 PM"
    meeting_location = "McAuley Conference Room"

    print(f"\n📅 Meeting Details:")
    print(f"   Date: {meeting_date}")
    print(f"   Type: {meeting_type}")
    print(f"   Time: {meeting_time}")
    print(f"   Location: {meeting_location}")

    # Get recipients from database
    print(f"\n🔍 Loading recipients from database...")
    notification_tool = MeetingNotificationTool()
    recipients = notification_tool.get_recipients(meeting_type)

    print(f"\n👥 Found {len(recipients)} recipients:")
    for i, email in enumerate(sorted(recipients), 1):
        print(f"   {i}. {email}")

    # Check environment settings
    dry_run = os.getenv("DRY_RUN", "true").lower() in ("true", "1", "yes", "y", "on")
    dev_override = os.getenv("DEV_OVERRIDE_EMAIL")

    print(f"\n⚙️  Email Settings:")
    print(f"   DRY_RUN: {dry_run}")
    print(f"   DEV_OVERRIDE_EMAIL: {dev_override or '(not set)'}")

    if dry_run:
        print(f"\n⚠️  DRY_RUN is enabled - no actual email will be sent")
        print(f"   Email preview will be written to: src/scribe/output/reminders/")
    elif dev_override:
        print(f"\n✉️  Real email will be sent, but redirected to: {dev_override}")
        print(f"   Original recipients: {len(recipients)} people")
    else:
        print(f"\n⚠️  WARNING: Real emails will be sent to ALL {len(recipients)} recipients!")
        response = input("\n   Continue? (yes/no): ")
        if response.lower() != "yes":
            print("\n❌ Cancelled by user")
            return

    # Create email content
    subject = f"Council Meeting Reminder - {meeting_date}"

    body = f"""Dear Council Members,

This is a reminder of our upcoming Residents Council meeting:

Date: {meeting_date}
Time: {meeting_time}
Location: {meeting_location}

Old Business:
• Elevator outages
• Parking lot maintenance

New Business:
• Bylaws revision
• Holiday decorations policy

Please review the attached agenda before the meeting.

Best regards,
George Wright
Council Secretary
"""

    print(f"\n📝 Email Content:")
    print(f"   Subject: {subject}")
    print(f"   Body: {len(body)} characters")

    # Send the email using send_reminder (which handles agenda attachment)
    print(f"\n📤 Sending meeting reminder...")
    email_service = EmailService()

    try:
        result = email_service.send_reminder(
            to=recipients,
            meeting_date=meeting_date,
            meeting_type=meeting_type,
            dry_run=dry_run
        )

        # Display results
        print(f"\n" + "=" * 70)
        print(f"✅ RESULT")
        print("=" * 70)
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Success: {result.get('success', False)}")
        print(f"Message: {result.get('message', 'No message')}")

        if result.get('status') == 'dry_run':
            preview_path = result.get('preview_path')
            if preview_path:
                print(f"\n📄 Preview file: {preview_path}")
                print("\nYou can view the preview with:")
                print(f"   cat {preview_path}")

        elif result.get('status') == 'sent':
            message_id = result.get('message_id')
            run_id = result.get('run_id')
            print(f"\n✉️  Email sent successfully!")
            print(f"   Message ID: {message_id}")
            print(f"   Run ID: {run_id}")

            if dev_override:
                print(f"\n📬 Check your inbox: {dev_override}")
                print(f"   (Original recipients were: {', '.join(recipients[:3])}...)")

        elif result.get('status') == 'failed':
            error = result.get('error', 'Unknown error')
            print(f"\n❌ Email failed to send")
            print(f"   Error: {error}")

        print("\n" + "=" * 70)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
