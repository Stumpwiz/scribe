"""
Recipient loader tool for the Scribe project.

This module provides the RecipientLoaderTool class for loading recipient
information based on meeting type.
"""

from typing import List, Dict, Any, Optional, ClassVar, Union
import json
import os
from pathlib import Path
from crewai.tools import BaseTool


class RecipientLoaderTool(BaseTool):
    """
    Tool for loading recipient information based on meeting type.
    
    This tool accepts a meeting type and loads recipient information from
    appropriate JSON files based on the meeting type.
    """
    
    name: str = "RecipientLoaderTool"
    description: str = "Tool for loading recipient information based on meeting type"
    
    # Compute base directory (project root) as a class attribute
    base_dir: ClassVar[Path] = Path(__file__).resolve().parents[2]  # resolves to src/
    
    # Define file paths
    council_members_file: ClassVar[str] = "scribe/assets/recipients/council_members.json"
    committee_chairs_file: ClassVar[str] = "scribe/assets/recipients/committee_chairs.json"
    
    def _run(self, meetingType: str, **kwargs) -> Dict[str, Any]:
        """
        Load recipient information based on meeting type.
        
        Args:
            meetingType (str): Type of meeting ("regular", "open", or "association")
            
        Returns:
            Dict[str, Any]: A dictionary containing:
                - success (bool): Whether the operation was successful
                - recipients (List[Dict]): List of recipient dictionaries with name, email, and role
                - log (str): Summary of what was loaded or errors encountered
        """
        # Initialize result dictionary
        result = {
            "success": False,
            "recipients": [],
            "log": ""
        }
        
        # Validate meeting type
        if meetingType not in ["regular", "open", "association"]:
            result["log"] = f"Error: Invalid meeting type: {meetingType}. Must be one of 'regular', 'open', or 'association'."
            return result
        
        log_messages = []
        
        try:
            # Load council members for all meeting types
            private_dir = os.getenv("RECIPIENTS_DIR")
            council_path = str(Path(private_dir).expanduser() / "council_members.json") if private_dir else self.council_members_file
            council_members = self._load_recipients_from_file(council_path)
            log_messages.append(f"Loaded {len(council_members)} council members")
            result["recipients"].extend(council_members)
            
            # Additionally load committee chairs for "open" or "association" meeting types
            if meetingType in ["open", "association"]:
                chairs_path = str(Path(private_dir).expanduser() / "committee_chairs.json") if private_dir else self.committee_chairs_file
                committee_chairs = self._load_recipients_from_file(chairs_path)
                log_messages.append(f"Loaded {len(committee_chairs)} committee chairs")
                result["recipients"].extend(committee_chairs)
            
            result["success"] = True
            result["log"] = "; ".join(log_messages)
            
        except Exception as e:
            result["log"] = f"Error: {str(e)}"
            
        return result
    
    def _load_recipients_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Load and validate recipient information from a JSON file.
        
        Args:
            file_path (str): Path to the JSON file containing recipient information
            
        Returns:
            List[Dict[str, Any]]: List of validated recipient entries
            
        Raises:
            FileNotFoundError: If the recipient file does not exist
            json.JSONDecodeError: If the recipient file contains invalid JSON
            ValueError: If the recipient file is not a JSON array or recipients are invalid
        """
        # Resolve the path to the recipient file
        resolved_path = self._resolve_path(file_path)
        
        # Load the JSON file
        recipients = self._load_json_file(resolved_path)
        
        # Validate each recipient
        validated_recipients = []
        for recipient in recipients:
            if isinstance(recipient, str):
                recipient = {"name": recipient, "email": recipient, "role": "recipient"}
            self._validate_recipient(recipient)
            validated_recipients.append(recipient)
        
        return validated_recipients
    
    def _resolve_path(self, file_path: str) -> Path:
        """
        Resolve the path to the recipient file.
        
        Args:
            file_path (str): Path to the recipient file
            
        Returns:
            Path: Resolved path to the recipient file
            
        Raises:
            FileNotFoundError: If the recipient file does not exist
        """
        # Convert to Path object
        path = Path(file_path)
        
        # If the path is already absolute, use it as-is
        if path.is_absolute():
            if path.exists():
                return path
            else:
                raise FileNotFoundError(f"Recipient file not found: {file_path}")
        
        # Try to resolve the path relative to the project root
        resolved_path = self.base_dir / path
        
        if resolved_path.exists():
            return resolved_path
        
        # If the file wasn't found, try as a relative path from the current directory
        cwd_path = Path.cwd() / path
        if cwd_path.exists():
            return cwd_path
        
        # If we get here, the file wasn't found
        raise FileNotFoundError(f"Recipient file not found: {file_path}")
    
    def _load_json_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Load the JSON file containing recipient information.
        
        Args:
            file_path (Path): Path to the JSON file
            
        Returns:
            List[Dict[str, Any]]: List of recipient entries
            
        Raises:
            json.JSONDecodeError: If the file contains invalid JSON
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Ensure the data is a list
            if not isinstance(data, list):
                raise ValueError("Recipient file must contain a JSON array")
            
            return data
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Invalid JSON in recipient file: {file_path}", e.doc, e.pos)
    
    def _validate_recipient(self, recipient: Dict[str, Any]) -> None:
        """
        Validate that a recipient has the required fields.
        
        Args:
            recipient (Dict[str, Any]): Recipient entry to validate
            
        Raises:
            ValueError: If the recipient is missing required fields
        """
        required_fields = ['name', 'email', 'role']
        
        for field in required_fields:
            if field not in recipient:
                raise ValueError(f"Missing required field '{field}' in recipient: {recipient}")
            
            # Ensure the field is not empty
            if not recipient[field]:
                raise ValueError(f"Empty '{field}' field in recipient: {recipient}")
        
        # Additional validation could be added here (e.g., email format validation)