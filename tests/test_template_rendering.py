#!/usr/bin/env python3
"""Test script to verify MeetingNotificationTool template rendering."""

from scribe.tools.meeting_notification_tool import MeetingNotificationTool

# Create tool instance
tool = MeetingNotificationTool()

# Test data matching the form submission
meeting_date = "2026-02-05"
meeting_type = "regular"
old_business_items = ["Elevator maintenance items."]
new_business_items = ["Bylaws need revision."]

print("Testing MeetingNotificationTool template rendering...")
print(f"Meeting Date: {meeting_date}")
print(f"Meeting Type: {meeting_type}")
print(f"Old Business: {old_business_items}")
print(f"New Business: {new_business_items}")
print("\n" + "="*70 + "\n")

# Call the tool's _run method directly
result = tool._run(
    meeting_date=meeting_date,
    meeting_type=meeting_type,
    old_business_items=old_business_items,
    new_business_items=new_business_items
)

print("RESULT:")
print(result)
print("\n" + "="*70 + "\n")

# Also test the render_email_from_template method directly
print("Testing render_email_from_template method directly...")
email = tool.render_email_from_template(
    meeting_date=meeting_date,
    meeting_type=meeting_type,
    old_business_items=old_business_items,
    new_business_items=new_business_items
)

print(f"Subject: {email['subject']}")
print(f"\nBody:\n{email['body']}")
