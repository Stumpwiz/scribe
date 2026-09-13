"""
Reminder tasks for the Scribe project.

This module provides task implementations for the ReminderAgent, including
sending meeting notifications with agenda attachments.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from crewai import Task

from scribe.meeting.meeting_config import meeting_location_for_type
from scribe.tools.meeting_agenda_generator_tool import MeetingAgendaGeneratorTool
from scribe.tools.meeting_notification_tool import MeetingNotificationTool

logger = logging.getLogger(__name__)


def _is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in ("1", "true", "yes", "y", "on")


def generate_new_run_id() -> str:
    """Generate a short run identifier used for file naming and logs."""
    import uuid
    return uuid.uuid4().hex[:8]

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
    2. Resolve recipients from Clerk if not explicitly provided
    3. Delegate send/dry-run draft generation to MeetingNotificationTool
    4. Return structured output with run metadata
    
    Args:
        agent: The agent executing the task
        task: The task being executed
        
    Returns:
        Dict[str, Any]: The structured dictionary returned from EmailService
    """
    # Respect a provided RUN_ID for test determinism and reproducibility; otherwise generate a fresh one
    run_id = os.getenv("RUN_ID") or generate_new_run_id()
    logger.info(f"[{run_id}] Starting send_meeting_notification_workflow")
    
    # Extract context from the task
    context = task.context or {}
    meeting_date = context.get("meetingDate")
    meeting_type = context.get("meetingType", "regular")
    meeting_time = context.get("meetingTime", "7:30 PM")
    location = context.get("location")
    old_business_items = context.get("old_business_items", []) or []
    new_business_items = context.get("new_business_items", []) or []
    # Keep compatibility with alternate key names used elsewhere.
    old_business_items = context.get("oldBusinessItems", old_business_items) or []
    new_business_items = context.get("newBusinessItems", new_business_items) or []
    # Optional override, but default source is Clerk recipients via MeetingNotificationTool.
    email_recipients = context.get("email_recipients")
    dry_run = _is_truthy(context.get("dry_run")) if "dry_run" in context else _is_truthy(os.getenv("DRY_RUN", "true"))

    # Validate/normalize meeting_date: if missing or invalid, fall back to today's date for robustness
    def _is_valid_iso_date(s: Optional[str]) -> bool:
        if not s or not isinstance(s, str):
            return False
        try:
            datetime.fromisoformat(s)
            return True
        except Exception:
            return False

    original_meeting_date = meeting_date
    if not _is_valid_iso_date(meeting_date):
        meeting_date = datetime.today().date().isoformat()
        logger.warning(f"[{run_id}] Invalid or missing meetingDate '{original_meeting_date}'; falling back to today's date {meeting_date}")
    
    logger.info(f"[{run_id}] Meeting details: {meeting_type} meeting on {meeting_date} at {meeting_time} in {location}")

    if not location:
        try:
            location = meeting_location_for_type(meeting_type)
        except Exception:
            location = "McAuley Conference Room"
        logger.info(f"[{run_id}] No explicit location provided; resolved location to '{location}'")

    if not email_recipients:
        try:
            email_recipients = MeetingNotificationTool().get_recipients(
                meeting_type=meeting_type,
                meeting_date=meeting_date,
            )
        except Exception as e:
            logger.error(f"[{run_id}] Failed to load recipients from Clerk source: {e}")
            email_recipients = [os.getenv("DEFAULT_FALLBACK_EMAIL", "test@example.com")]
    
    # Step 1: Always generate a meeting agenda using MeetingAgendaGeneratorTool
    meeting_info = {
        "meetingDate": meeting_date,  # Ensure valid meetingDate field
        "meetingType": meeting_type,
        "location": location
    }
    
    # Log detailed information before calling MeetingAgendaGeneratorTool
    logger.info(f"[{run_id}] Preparing to call MeetingAgendaGeneratorTool with meeting_info: {meeting_info}")
    logger.info(f"[{run_id}] Meeting date: {meeting_date}, Meeting type: {meeting_type}, Location: {location}")
    
    # Call MeetingAgendaGeneratorTool and capture its return value in agenda_result
    agenda_generator = MeetingAgendaGeneratorTool()
    agenda_result = agenda_generator._run(meeting_info=meeting_info)
    
    # Log detailed information after calling MeetingAgendaGeneratorTool
    logger.info(f"[{run_id}] MeetingAgendaGeneratorTool completed with success={agenda_result.get('success', False)}")
    if agenda_result.get("success", False):
        logger.info(f"[{run_id}] Generated PDF path: {agenda_result.get('pdfPath', 'Not provided')}")
        logger.info(f"[{run_id}] Log path: {agenda_result.get('logPath', 'Not provided')}")
    else:
        logger.error(f"[{run_id}] Agenda generation failed: {agenda_result.get('log', 'No error details provided')}")
    
    # Step 2: Extract canonical pdfPath from the tool's output
    pdf_path = None
    if agenda_result.get("success", False) and "pdfPath" in agenda_result:
        pdf_path = str(agenda_result["pdfPath"])
        logger.info(f"[{run_id}] Extracted PDF path: {pdf_path}")
    else:
        logger.warning("Failed to generate agenda or PDF path not found in result")
    
    # Step 3/4: Call MeetingNotificationTool for dry-run draft or live send.
    notification_result: Dict[str, Any] = {}
    if agenda_result.get("success", False):
        logger.info(f"[{run_id}] Agenda generation was successful, calling MeetingNotificationTool")
        notification_tool = MeetingNotificationTool()
        logger.info(f"[{run_id}] Calling MeetingNotificationTool with: meeting_date={meeting_date}, location={location}, dry_run={dry_run}")
        
        # Call MeetingNotificationTool with all required arguments and the full agenda_result
        notification_result = notification_tool._run(
            meeting_date=meeting_date,
            meeting_type=meeting_type,
            meeting_time=meeting_time,
            location=location,
            old_business_items=old_business_items,
            new_business_items=new_business_items,
            filename_hint=f"{meeting_type}_meeting_{meeting_date}",
            agenda_result=agenda_result,  # Pass the full agenda_result dictionary
            recipients=email_recipients,
            dry_run=dry_run,
        )
        logger.info("[%s] MeetingNotificationTool result: success=%s status=%s",
                    run_id, notification_result.get("success"), notification_result.get("status"))
    else:
        logger.warning(f"[{run_id}] Agenda generation was not successful, skipping MeetingNotificationTool")

    # Build final response from notification result, with agenda-failure fallback.
    result: Dict[str, Any] = dict(notification_result) if isinstance(notification_result, dict) else {}
    if not agenda_result.get("success", False):
        result.setdefault("status", "failed")
        result["success"] = False
        result["error"] = agenda_result.get("log", result.get("error", "Agenda generation failed"))
        result.setdefault("message", result["error"])
        result.setdefault("recipient_count", len(email_recipients))
        result.setdefault("recipients", email_recipients)
        result.setdefault("attachment_path", "")

    # Backward-compatible alias used by dev helper/scripts.
    if result.get("status") == "dry_run" and result.get("draft_path"):
        result["preview_path"] = result["draft_path"]
        logger.info("[%s] Dry-run draft written to: %s", run_id, result["draft_path"])

    result["run_id"] = run_id
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
        "email_recipients": [os.getenv("DEFAULT_FALLBACK_EMAIL", "test@example.com")]
    }
    
    # Create a task
    task = create_task(context=test_context)
    
    # Print task details
    print(f"Task created: {task.description}")
    print(f"Expected output: {task.expected_output}")
