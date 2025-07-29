"""
Task configuration module for the Scribe project.

This module provides the TaskConfig class for loading and parsing task configurations
from YAML files.
"""

from typing import Dict, List
import yaml
from dataclasses import dataclass


@dataclass
class TaskConfig:
    """
    Configuration for a task in the Scribe project.
    
    Attributes:
        description (str): The description of the task
        expected_output (str): The expected output of the task
        agent (str): The name of the agent responsible for the task
        tools (List[str]): List of tool names required for the task
    """
    description: str
    expected_output: str
    agent: str
    tools: List[str]

    @classmethod
    def from_yaml(cls, yaml_path: str) -> Dict[str, 'TaskConfig']:
        """
        Load task configurations from a YAML file.
        
        Args:
            yaml_path (str): Path to the YAML file
            
        Returns:
            Dict[str, TaskConfig]: Dictionary of task name to TaskConfig object
        """
        with open(yaml_path, 'r') as file:
            data = yaml.safe_load(file)
        
        tasks = {}
        for name, config in data.items():
            # Skip comments or non-dictionary entries
            if not isinstance(config, dict):
                continue
                
            tasks[name] = cls(
                description=config.get('description', ''),
                expected_output=config.get('expected_output', ''),
                agent=config.get('agent', ''),
                tools=config.get('tools', [])
            )
        
        return tasks