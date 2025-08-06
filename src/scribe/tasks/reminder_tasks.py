"""
Reminder tasks for the Scribe project.

This module provides task implementations for the ReminderAgent, including
sending meeting notifications with agenda attachments.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

from crewai import Task

from scribe.tools.meeting_agenda_generator_tool import MeetingAgendaGeneratorTool
from scribe.tools.meeting_notification_tool import MeetingNotificationTool
from scribe.tools.email_service import EmailService

logger = logging.getLogger(__name__)

def create_task(context: Dict[str, Any] = None) -> Task:
    """
    Create a send_meeting_notification task with the given context.
    
    Args:
        context (Dict[str, Any]): Context for the task, including meeting details
        
    Returns:
        Task: A CrewAI Task object
    """
    # Create a custom task with the send_meeting_notification_workflow function
    task = Task(
        description=f"Send a meeting reminder email for the {context.get('meetingType', 'upcoming')} meeting on {context.get('meetingDate', 'the scheduled date')}.",
        expected_output="Email notification sent to all participants with meeting details and agenda attachment.",
        async_execution=send_meeting_notification_workflow
    )
    
    # Add context to the task
    task.context = context
    
    return task

async def send_meeting_notification_workflow(self, agent, task) -> Dict[str, Any]:
    """
    Execute the meeting notification workflow according to the requirements.
    
    This function implements the following workflow:
    1. Call MeetingAgendaGeneratorTool with meeting_info
    2. Extract pdfPath from the tool's output
    3. Render email body using Jinja2 template
    4. Use EmailService to send the email with the attachment
    5. Return the structured dictionary from EmailService
    
    Args:
        agent: The agent executing the task
        task: The task being executed
        
    Returns:
        Dict[str, Any]: The structured dictionary returned from EmailService
    """
    logger.info("Starting send_meeting_notification_workflow")
    
    # Extract context from the task
    context = task.context or {}
    meeting_date = context.get("meetingDate")
    meeting_type = context.get("meetingType", "regular")
    meeting_time = context.get("meetingTime", "7:30 PM")
    location = context.get("location", "Conference Room")
    email_recipients = context.get("email_recipients", ["georgemartinwright@gmail.com"])
    
    logger.info(f"Meeting details: {meeting_type} meeting on {meeting_date} at {meeting_time} in {location}")
    
    # Step 1: Always generate a meeting agenda using MeetingAgendaGeneratorTool
    meeting_info = {
        "meetingDate": meeting_date,  # Ensure valid meetingDate field
        "meetingType": meeting_type,
        "location": location
    }
    
    # Log detailed information before calling MeetingAgendaGeneratorTool
    logger.info(f"Preparing to call MeetingAgendaGeneratorTool with meeting_info: {meeting_info}")
    logger.info(f"Meeting date: {meeting_date}, Meeting type: {meeting_type}, Location: {location}")
    
    # Call MeetingAgendaGeneratorTool and capture its return value in agenda_result
    agenda_generator = MeetingAgendaGeneratorTool()
    agenda_result = agenda_generator._run(meeting_info=meeting_info)
    
    # Log detailed information after calling MeetingAgendaGeneratorTool
    logger.info(f"MeetingAgendaGeneratorTool completed with success={agenda_result.get('success', False)}")
    if agenda_result.get("success", False):
        logger.info(f"Generated PDF path: {agenda_result.get('pdfPath', 'Not provided')}")
        logger.info(f"Log path: {agenda_result.get('logPath', 'Not provided')}")
    else:
        logger.error(f"Agenda generation failed: {agenda_result.get('log', 'No error details provided')}")
    
    # Step 2: Extract pdfPath from the tool's output
    pdf_path = None
    if agenda_result.get("success", False) and "pdfPath" in agenda_result:
        pdf_path = agenda_result["pdfPath"]
        logger.info(f"Extracted PDF path: {pdf_path}")
    else:
        logger.warning("Failed to generate agenda or PDF path not found in result")
    
    # Step 3: Render email body using Jinja2 template
    template_dir = Path(__file__).parent.parent / "assets" / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("email_reminder.txt.j2")
    
    # Pass required placeholders to the template
    template_vars = {
        "meetingType": meeting_type,
        "meetingDate": meeting_date,
        "meetingTime": meeting_time,
        "venue": location
    }
    
    # Render the template
    body = template.render(**template_vars)
    logger.info(f"Rendered email body from template")
    
    # Step 4: Use EmailService to send the email with the required arguments
    subject = f"Reminder: {meeting_type.capitalize()} Meeting on {meeting_date}"
    
    # Prepare email arguments according to requirements
    email_args = {
        "action": "send",  # Required argument
        "to": email_recipients,  # List of email addresses based on meeting type
        "subject": subject,  # "Reminder: [Meeting Type] Meeting on [Date]"
        "body": body,  # Rendered from Jinja2 template
        "attachments": [pdf_path] if pdf_path else []  # List containing PDF path
    }
    
    # Log detailed information before calling EmailService
    logger.info(f"Preparing to call EmailService with the following parameters:")
    logger.info(f"  - Action: send")
    logger.info(f"  - Recipients: {email_recipients}")
    logger.info(f"  - Subject: {subject}")
    logger.info(f"  - Body length: {len(body)} characters")
    
    if pdf_path:
        logger.info(f"  - Attachment: {pdf_path}")
        logger.info(f"  - Attachment exists: {os.path.exists(pdf_path)}")
    else:
        logger.warning("  - No attachment will be included - agenda generation may have failed")
    
    # Send the email and get the result
    email_service = EmailService()
    
    # Pass arguments directly to the _run method, not as a dictionary
    logger.info("Calling EmailService._run method...")
    result = email_service._run(
        action="send",
        to=email_recipients,
        subject=subject,
        body=body,
        attachments=[pdf_path] if pdf_path else []
    )
    
    # Log detailed information after calling EmailService
    logger.info(f"EmailService completed with result:")
    logger.info(f"  - Success: {result.get('success', False)}")
    logger.info(f"  - Status: {result.get('status', 'unknown')}")
    logger.info(f"  - Message: {result.get('message', 'No message provided')}")
    
    if not result.get('success', False):
        logger.error(f"  - Error: {result.get('error', 'No error details provided')}")
    
    # Step 5: Call MeetingNotificationTool if agenda_result["success"] is True
    if agenda_result.get("success", False):
        logger.info("Agenda generation was successful, calling MeetingNotificationTool")
        notification_tool = MeetingNotificationTool()
        
        # Log the input being passed to MeetingNotificationTool
        logger.info(f"Calling MeetingNotificationTool with: content={len(body)} chars, meeting_date={meeting_date}, location={location}")
        logger.info(f"Passing full agenda_result dictionary to MeetingNotificationTool")
        
        # Call MeetingNotificationTool with all required arguments and the full agenda_result
        notification_result = notification_tool._run(
            content=body,
            meeting_date=meeting_date,
            location=location,
            filename_hint=f"{meeting_type}_meeting_{meeting_date}",
            agenda_result=agenda_result  # Pass the full agenda_result dictionary
        )
        
        # Log the output returned by MeetingNotificationTool
        logger.info(f"MeetingNotificationTool result: {notification_result}")
    else:
        logger.warning("Agenda generation was not successful, skipping MeetingNotificationTool")
    
    # Return the structured dictionary from EmailService as the final output
    return result

# For direct testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Test context
    test_context = {
        "meetingDate": "2025-08-07",
        "meetingType": "regular",
        "meetingTime": "7:30 PM",
        "location": "Conference Room A",
        "email_recipients": ["georgemartinwright@gmail.com"]
    }
    
    # Create a task
    task = create_task(context=test_context)
    
    # Print task details
    print(f"Task created: {task.description}")
    print(f"Expected output: {task.expected_output}")