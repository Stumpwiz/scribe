"""
Crew configuration for the Scribe project.

This module loads agent and task configurations from YAML files,
constructs the agents with their tools, and creates a Crew object
that can be used to run the tasks.
"""

from typing import Dict, List, Any, Optional, Callable
import yaml
from pathlib import Path
from datetime import datetime
import re

from crewai import Crew, Agent, Task

# Import tools from the scribe.tools package
from scribe.tools import (
    EmailService,
    CalendarIntegration,
    FileTools,
    TranscriptionService,
    LaTeXService,
    FTPService,
    OutputTool,
    MeetingNotificationTool
)


class AgentConfig:
    """Configuration for an agent loaded from YAML."""
    
    @classmethod
    def from_yaml(cls, yaml_path: str = "config/agents.yaml") -> Dict[str, Dict[str, Any]]:
        """
        Load agent configurations from a YAML file.
        
        Args:
            yaml_path: Path to the YAML file containing agent configurations
            
        Returns:
            Dictionary of agent configurations
        """
        config_path = Path(__file__).parent / yaml_path
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)


class TaskConfig:
    """Configuration for tasks loaded from YAML."""
    
    @classmethod
    def from_yaml(cls, yaml_path: str = "config/tasks.yaml") -> Dict[str, Dict[str, Any]]:
        """
        Load task configurations from a YAML file.
        
        Args:
            yaml_path: Path to the YAML file containing task configurations
            
        Returns:
            Dictionary of task configurations
        """
        config_path = Path(__file__).parent / yaml_path
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)


def create_tool(tool_name: str) -> Any:
    """
    Create a tool instance based on its name.
    
    Args:
        tool_name: Name of the tool to create
        
    Returns:
        An instance of the requested tool
    """
    tools_map = {
        "email_service": EmailService(),
        "calendar_integration": CalendarIntegration(),
        "file_tools": FileTools(),
        "transcription_service": TranscriptionService(),
        "latex_service": LaTeXService(),
        "ftp_service": FTPService(),
        "output_tool": OutputTool(),
        "meeting_notification_tool": MeetingNotificationTool()
    }
    
    return tools_map.get(tool_name)


def create_agents(agent_configs: Dict[str, Dict[str, Any]]) -> Dict[str, Agent]:
    """
    Create Agent objects from configurations.
    
    Args:
        agent_configs: Dictionary of agent configurations
        
    Returns:
        Dictionary of Agent objects
    """
    agents = {}
    
    for agent_name, config in agent_configs.items():
        # Create tools for the agent
        tools = []
        if "tools" in config:
            for tool_name in config["tools"]:
                tool = create_tool(tool_name)
                if tool:
                    tools.append(tool)
        
        # Create the agent
        agent = Agent(
            role=config.get("role", ""),
            goal=config.get("goal", ""),
            backstory=config.get("backstory", ""),
            verbose=True,
            allow_delegation=True,
            tools=tools
        )
        
        agents[agent_name] = agent
    
    return agents


def task_callback(result: str, task_name: str, agent_name: str) -> str:
    """
    Callback function for tasks to log their results.
    
    This function is called after a task is executed. It logs the task result
    using the OutputTool, with a filename that includes the agent name and task name.
    
    Args:
        result: The result of the task execution
        task_name: The name of the task
        agent_name: The name of the agent that executed the task
        
    Returns:
        The original task result (unchanged)
    """
    # Format the task name and agent name for the filename
    safe_task_name = re.sub(r'[^\w\-]', '_', task_name)
    safe_agent_name = re.sub(r'[^\w\-]', '_', agent_name)
    
    # Format the timestamp according to the required format (YYYY-MM-DD_HH-MM-SS)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    # Create the filename hint
    filename_hint = f"{safe_agent_name}_{safe_task_name}"
    
    # Use the OutputTool to save the task result
    output_tool = OutputTool()
    log_path = output_tool.run(
        content=f"Task: {task_name}\nAgent: {agent_name}\nTimestamp: {timestamp}\n\nResult:\n{result}",
        filename_hint=filename_hint
    )
    
    # Return the original result
    return result


def create_tasks(task_configs: Dict[str, Dict[str, Any]], agents: Dict[str, Agent]) -> List[Task]:
    """
    Create Task objects from configurations.
    
    Tasks marked with 'skip: true' will be filtered out. This allows for
    skeleton test runs with only the dummy tasks.
    
    Args:
        task_configs: Dictionary of task configurations
        agents: Dictionary of Agent objects
        
    Returns:
        List of Task objects
    """
    tasks = []
    
    for task_name, config in task_configs.items():
        # Skip tasks marked with skip: true
        if config.get("skip", False):
            continue
            
        agent_name = config.get("agent")
        if agent_name not in agents:
            continue
        
        # Create a callback function specific to this task and agent
        def create_callback(tn=task_name, an=agent_name):
            return lambda result: task_callback(result, tn, an)
        
        task = Task(
            description=config.get("description", ""),
            expected_output=config.get("expected_output", ""),
            agent=agents[agent_name],
            callback=create_callback()  # Add the callback function
        )
        
        tasks.append(task)
    
    return tasks


# Load configurations
agent_configs = AgentConfig.from_yaml()
task_configs = TaskConfig.from_yaml()

# Create agents and tasks
agents = create_agents(agent_configs)
tasks = create_tasks(task_configs, agents)

# Create the crew
crew = Crew(
    agents=list(agents.values()),
    tasks=tasks,
    verbose=True
)