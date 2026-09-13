"""
Custom tools for the Scribe project.

This package contains custom tools used by agents in the Scribe project.
"""

from importlib import import_module
from typing import Any

__all__ = [
    'EmailService',
    'CalendarIntegration',
    'FileTools',
    'TranscriptionService',
    'LaTeXService',
    'FTPService',
    'OutputTool',
    'MeetingNotificationTool',
    'MeetingCalendarTool',
    'RecipientLoaderTool',
    'LaTeXAgendaTool',
    'LaTeXCompilerTool',
    'MeetingAgendaGeneratorTool',
    'EmailWriterTool',
    'EmailInboxMonitorTool',
    'EmailClassifierTool',
    'AttachmentOrganizerTool',
]

_LAZY_IMPORTS = {
    'EmailService': '.email_service',
    'CalendarIntegration': '.calendar_integration',
    'FileTools': '.file_tools',
    'TranscriptionService': '.transcription_service',
    'LaTeXService': '.latex_service',
    'FTPService': '.ftp_service',
    'OutputTool': '.output_tool',
    'MeetingNotificationTool': '.meeting_notification_tool',
    'MeetingCalendarTool': '.meeting_calendar_tool',
    'RecipientLoaderTool': '.recipient_loader_tool',
    'LaTeXAgendaTool': '.latex_agenda_tool',
    'LaTeXCompilerTool': '.latex_compiler_tool',
    'MeetingAgendaGeneratorTool': '.meeting_agenda_generator_tool',
    'EmailWriterTool': '.email_writer_tool',
    'EmailInboxMonitorTool': '.email_inbox_monitor_tool',
    'EmailClassifierTool': '.email_classifier_tool',
    'AttachmentOrganizerTool': '.attachment_organizer_tool',
}


def __getattr__(name: str) -> Any:
    module_name = _LAZY_IMPORTS.get(name)
    if not module_name:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name, __name__)
    return getattr(module, name)
