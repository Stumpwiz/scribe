"""
Output tool for the Scribe project.

This module provides the OutputTool class for saving agent outputs and task results
to persistent log files.
"""

from typing import Optional, ClassVar
import os
from pathlib import Path
from datetime import datetime
import re
from crewai.tools import BaseTool


class OutputTool(BaseTool):
    """
    Tool for saving agent outputs and task results to persistent log files.
    
    This tool allows agents to save their outputs and task results to log files
    in the output/logs/ directory, ensuring that important information is preserved
    between runs.
    """
    
    name: str = "OutputTool"
    description: str = "Tool for saving content to persistent log files"
    
    # Compute base directory (project root) as a class attribute
    base_dir: ClassVar[Path] = Path(__file__).resolve().parents[2]  # resolves to src/
    
    def _run(self, 
             content: str,
             filename_hint: Optional[str] = None,
             **kwargs) -> str:
        """
        Save content to a log file.
        
        Args:
            content (str): The text content to save to the log file
            filename_hint (Optional[str]): A short string to use in naming the file
            
        Returns:
            str: The full path to the created log file
        """
        return self._save_content(content, filename_hint)
    
    def _save_content(self, 
                     content: str,
                     filename_hint: Optional[str] = None) -> str:
        """
        Save content to a log file in the output/logs/ directory.
        
        Args:
            content (str): The text content to save to the log file
            filename_hint (Optional[str]): A short string to use in naming the file
            
        Returns:
            str: The full path to the created log file
        """
        # Create the output/logs directory if it doesn't exist
        logs_dir = self.base_dir / "scribe" / "output" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate a timestamp for the filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Process the filename_hint if provided
        if filename_hint:
            # Replace spaces and special characters with underscores
            safe_hint = re.sub(r'[^\w\-]', '_', filename_hint)
            filename = f"{timestamp}_{safe_hint}.txt"
        else:
            filename = f"{timestamp}_output.txt"
        
        # Create the full file path
        file_path = logs_dir / filename
        
        # Write the content to the file
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return str(file_path)
        except Exception as e:
            return f"Error saving content to file: {str(e)}"