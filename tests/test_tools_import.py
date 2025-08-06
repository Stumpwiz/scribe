"""
Test script to verify that all tools can be imported correctly.

This script attempts to import all the tools from the scribe.tools package
using the specified import path convention.
"""

import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), \'..\')))
import os
from pathlib import Path

def test_imports():
    """Test that all tools can be imported correctly."""
    try:
        # Add the src directory to the Python path
        src_dir = Path(__file__).parent.parent / "src"
        sys.path.insert(0, str(src_dir))
        print(f"Added {src_dir} to Python path")
        # Import all tools using the specified import path convention
        from scribe.tools.email_service import EmailService
        from scribe.tools.calendar_integration import CalendarIntegration
        from scribe.tools.file_tools import FileTools
        from scribe.tools.transcription_service import TranscriptionService
        from scribe.tools.latex_service import LaTeXService
        from scribe.tools.ftp_service import FTPService
        from scribe.tools.output_tool import OutputTool
        
        # Import all tools from the package
        from scribe.tools import (
            EmailService,
            CalendarIntegration,
            FileTools,
            TranscriptionService,
            LaTeXService,
            FTPService,
            OutputTool
        )
        
        print("All tools imported successfully!")
        
        # Print the name and description of each tool
        tools = [
            EmailService(),
            CalendarIntegration(),
            FileTools(),
            TranscriptionService(),
            LaTeXService(),
            FTPService(),
            OutputTool()
        ]
        
        print("\nTool names and descriptions:")
        for tool in tools:
            print(f"- {tool.name}: {tool.description}")
            
        return True
    except ImportError as e:
        print(f"Import error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_imports()