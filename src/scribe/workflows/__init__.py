"""
Workflow module for Scribe project.

This module provides workflow-specific crews that execute focused sets of tasks
for different stages of the secretary's meeting lifecycle.
"""

from scribe.workflows.workflow_builder import WorkflowBuilder
from scribe.workflows.reminder_workflow import create_reminder_crew

__all__ = ['WorkflowBuilder', 'create_reminder_crew']
