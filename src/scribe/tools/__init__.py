"""
Custom tools for the Scribe project.

This package contains custom tools used by agents in the Scribe project.
"""

from scribe.tools.email_service import EmailService
from scribe.tools.calendar_integration import CalendarIntegration
from scribe.tools.file_tools import FileTools
from scribe.tools.transcription_service import TranscriptionService
from scribe.tools.latex_service import LaTeXService
from scribe.tools.ftp_service import FTPService
from scribe.tools.output_tool import OutputTool
from scribe.tools.meeting_notification_tool import MeetingNotificationTool
from scribe.tools.meeting_calendar_tool import MeetingCalendarTool
from scribe.tools.recipient_loader_tool import RecipientLoaderTool
from scribe.tools.latex_agenda_tool import LaTeXAgendaTool
from scribe.tools.latex_compiler_tool import LaTeXCompilerTool
from scribe.tools.meeting_agenda_generator_tool import MeetingAgendaGeneratorTool
from scribe.tools.email_writer_tool import EmailWriterTool
from scribe.tools.email_inbox_monitor_tool import EmailInboxMonitorTool
from scribe.tools.email_classifier_tool import EmailClassifierTool
from scribe.tools.attachment_organizer_tool import AttachmentOrganizerTool

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