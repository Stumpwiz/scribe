"""
Workflow Builder for creating focused crews.

This module provides utilities to create workflow-specific crews by
reusing the agent and task configuration infrastructure from crew.py.
"""

from typing import Dict, List, Any
import logging
from crewai import Crew, Agent, Task, Process

# Import the existing configuration loaders and creation functions from crew.py
from scribe.crew import (
    AgentConfig,
    TaskConfig,
    create_tool,
    task_callback
)

logger = logging.getLogger(__name__)


class WorkflowBuilder:
    """
    Builder for creating workflow-specific crews.

    This class reuses the existing agent and task configuration system
    but allows creation of focused crews with only the agents and tasks
    needed for a specific workflow.
    """

    def __init__(self):
        """Initialize the workflow builder with configuration loaders."""
        self.agent_configs = AgentConfig.from_yaml()
        self.task_configs = TaskConfig.from_yaml()

    def create_agent(self, agent_name: str) -> Agent:
        """
        Create a single agent from configuration.

        Args:
            agent_name: Name of the agent to create

        Returns:
            Configured Agent instance
        """
        if agent_name not in self.agent_configs:
            raise ValueError(f"Agent '{agent_name}' not found in configuration")

        config = self.agent_configs[agent_name]

        # Create tools for this agent
        tool_names = config.get("tools", [])
        tools = []
        for tool_name in tool_names:
            try:
                tool = create_tool(tool_name)
                if tool is not None:
                    tools.append(tool)
                    logger.info(f"Agent '{agent_name}' assigned tool: {tool_name}")
                else:
                    logger.warning(f"Tool '{tool_name}' not found in tools_map, skipping for agent '{agent_name}'")
            except Exception as e:
                logger.error(f"Error creating tool '{tool_name}' for agent '{agent_name}': {str(e)}")

        agent = Agent(
            role=config.get("role", ""),
            goal=config.get("goal", ""),
            backstory=config.get("backstory", ""),
            tools=tools,
            verbose=config.get("verbose", True),
            allow_delegation=config.get("allow_delegation", True)
        )

        logger.info(f"Created agent: {agent_name}, role: {config.get('role')}, tools: {len(tools)}")
        return agent

    def create_task(self, task_name: str, agent: Agent) -> Task:
        """
        Create a single task from configuration.

        Args:
            task_name: Name of the task to create
            agent: Agent instance to assign to this task

        Returns:
            Configured Task instance
        """
        if task_name not in self.task_configs:
            raise ValueError(f"Task '{task_name}' not found in configuration")

        config = self.task_configs[task_name]

        # Check if task should be skipped
        if config.get("skip", False):
            logger.info(f"Skipping task '{task_name}' (marked with skip=true)")
            return None

        # Create callback function for this task
        agent_name = config.get("agent", "Unknown")
        def create_callback(tn=task_name, an=agent_name):
            return lambda result: task_callback(result, tn, an)

        task = Task(
            description=config.get("description", ""),
            expected_output=config.get("expected_output", ""),
            agent=agent,
            callback=create_callback()
        )

        logger.info(f"Created task: '{task_name}' assigned to agent '{agent_name}'")
        return task

    def create_crew(self,
                   workflow_name: str,
                   agent_names: List[str],
                   task_names: List[str],
                   process: Process = Process.sequential) -> Crew:
        """
        Create a focused crew for a specific workflow.

        Args:
            workflow_name: Name of the workflow (for logging)
            agent_names: List of agent names to include
            task_names: List of task names to execute (in order for sequential process)
            process: CrewAI process type (sequential or hierarchical)

        Returns:
            Configured Crew instance
        """
        logger.info(f"Creating workflow crew: {workflow_name}")

        # Create agents
        agents = {}
        for agent_name in agent_names:
            try:
                agents[agent_name] = self.create_agent(agent_name)
            except Exception as e:
                logger.error(f"Error creating agent '{agent_name}': {str(e)}")
                raise

        # Create tasks
        tasks = []
        for task_name in task_names:
            try:
                # Get the agent name from task config
                task_config = self.task_configs.get(task_name, {})
                agent_name = task_config.get("agent")

                if not agent_name:
                    logger.warning(f"Task '{task_name}' has no agent specified, skipping")
                    continue

                if agent_name not in agents:
                    logger.warning(f"Task '{task_name}' requires agent '{agent_name}' which is not in workflow, skipping")
                    continue

                task = self.create_task(task_name, agents[agent_name])
                if task:  # Only add if not skipped
                    tasks.append(task)
            except Exception as e:
                logger.error(f"Error creating task '{task_name}': {str(e)}")
                raise

        if not tasks:
            raise ValueError(f"No valid tasks created for workflow '{workflow_name}'")

        # Create the crew
        crew = Crew(
            agents=list(agents.values()),
            tasks=tasks,
            process=process,
            verbose=True
        )

        logger.info(f"Created workflow crew '{workflow_name}' with {len(agents)} agents and {len(tasks)} tasks")
        return crew
