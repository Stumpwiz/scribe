"""
Reminder Workflow - Pre-Meeting Stage

This workflow handles sending meeting reminders with agendas to council members
before the meeting takes place.

Workflow steps:
1. Generate meeting agenda (optional, if FormatterAgent is included)
2. Send meeting notification with agenda attached

Agents involved:
- ReminderAgent: Creates and sends meeting notifications
- FormatterAgent: (optional) Generates LaTeX/PDF agendas

Tasks:
- generate_meeting_agenda (optional)
- send_meeting_notification
"""

import logging
from crewai import Crew, Process
from scribe.workflows.workflow_builder import WorkflowBuilder

logger = logging.getLogger(__name__)


def create_reminder_crew(include_agenda_generation: bool = False) -> Crew:
    """
    Create a crew for the meeting reminder workflow.

    This crew sends meeting reminders to council members. It can optionally
    include agenda generation if needed.

    Args:
        include_agenda_generation: If True, includes FormatterAgent and
                                  agenda generation task

    Returns:
        Configured Crew for reminder workflow
    """
    builder = WorkflowBuilder()

    # Define agents needed for this workflow
    if include_agenda_generation:
        agent_names = ["ReminderAgent", "FormatterAgent"]
        task_names = ["generate_meeting_agenda", "send_meeting_notification"]
    else:
        agent_names = ["ReminderAgent"]
        task_names = ["send_meeting_notification"]

    # Create the crew
    crew = builder.create_crew(
        workflow_name="reminder_workflow",
        agent_names=agent_names,
        task_names=task_names,
        process=Process.sequential  # Agenda first (if included), then notification
    )

    logger.info(f"Reminder workflow crew created (agenda generation: {include_agenda_generation})")
    return crew
