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

__all__ = [
    'EmailService',
    'CalendarIntegration',
    'FileTools',
    'TranscriptionService',
    'LaTeXService',
    'FTPService',
    'OutputTool',
]