import os
import logging
import yaml
from pathlib import Path
from crewai import Agent, Task
from importlib import import_module

from scribe.tools.email_service import EmailService
from scribe.tools.calendar_integration import CalendarIntegration
from scribe.tools.output_tool import OutputTool
from scribe.tools.meeting_notification_tool import MeetingNotificationTool
from scribe.tools.meeting_agenda_generator_tool import MeetingAgendaGeneratorTool
from scribe.tools.database_query_tool import DatabaseQueryTool
from ..tools import file_tools

CONFIG_DIR = Path(__file__).parent.resolve()
AGENTS_PATH = os.path.join(os.path.dirname(__file__), "agents.yaml")
TASKS_PATH = CONFIG_DIR / "tasks.yaml"

# Logger for this module
logger = logging.getLogger(__name__)

# Map of string names to actual tool instances
TOOL_REGISTRY = {
    "email_service": EmailService(),
    "calendar_integration": CalendarIntegration(),
    "output_tool": OutputTool(),
    "meeting_notification_tool": MeetingNotificationTool(),
    "meeting_agenda_generator_tool": MeetingAgendaGeneratorTool(),
    "database_query_tool": DatabaseQueryTool(),
    "file_tools": file_tools.FileTools(),
}


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_agent_from_yaml(agent_id: str) -> Agent:
    with open(AGENTS_PATH, "r") as file:
        agents_data = yaml.safe_load(file)

    if agent_id not in agents_data:
        raise ValueError(f"Agent ID '{agent_id}' not found in {AGENTS_PATH}")

    agent_spec = agents_data[agent_id]

    # Resolve tool names to actual instances
    tools = agent_spec.get("tools", [])
    resolved_tools = []
    for tool_name in tools:
        tool = TOOL_REGISTRY.get(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found in TOOL_REGISTRY")
        resolved_tools.append(tool)

    agent_spec["tools"] = resolved_tools

    return Agent(**agent_spec)


def load_task_from_yaml(task_id: str, context: dict = None) -> Task:
    tasks_data = load_yaml(TASKS_PATH)
    if task_id not in tasks_data:
        raise ValueError(f"Task ID '{task_id}' not found in {TASKS_PATH}")

    task_spec = tasks_data[task_id]
    
    # Safe interpolation with proper format-style using str.format
    if context:
        # Handle description interpolation
        try:
            from crewai.utilities.string_utils import interpolate_only
            task_spec['description'] = interpolate_only(task_spec['description'], context)
        except Exception as e:
            print(f"Warning: Error interpolating description: {e}")
            
        # Handle expected_output interpolation if it exists
        if 'expected_output' in task_spec:
            try:
                task_spec['expected_output'] = interpolate_only(task_spec['expected_output'], context)
            except Exception as e:
                print(f"Warning: Error interpolating expected_output: {e}")
    
    # Ensure task_spec only contains fields expected by Task constructor
    # Get a copy of task_spec to avoid modifying it during iteration
    task_spec_copy = task_spec.copy()
    for key in task_spec_copy:
        if key not in Task.__annotations__:
            print(f"Warning: Removing unexpected field '{key}' from task_spec")
            task_spec.pop(key, None)
    
    # Handle agent field - convert from string to Agent object
    if 'agent' in task_spec and isinstance(task_spec['agent'], str):
        try:
            agent_id = task_spec['agent']
            task_spec['agent'] = load_agent_from_yaml(agent_id)
        except Exception as e:
            print(f"Warning: Error loading agent '{agent_id}': {e}")
            # Remove agent field if it can't be loaded to avoid errors
            task_spec.pop('agent', None)
    
    # Handle tools field - convert from list of strings to list of tool objects
    if 'tools' in task_spec and isinstance(task_spec['tools'], list):
        resolved_tools = []
        for tool_name in task_spec['tools']:
            if isinstance(tool_name, str):
                tool = TOOL_REGISTRY.get(tool_name)
                if tool:
                    resolved_tools.append(tool)
                else:
                    print(f"Warning: Tool '{tool_name}' not found in TOOL_REGISTRY")
            else:
                # If it's already a tool object, keep it
                resolved_tools.append(tool_name)
        task_spec['tools'] = resolved_tools
    
    # Debug support
    print("TASK SPEC DEBUG (after interpolation and validation):", task_spec)
    
    return Task(**task_spec)


def execute_formatter_format_agenda(tasks_path: Path = TASKS_PATH) -> str | None:
    """
    Load tasks.yaml, locate the FormatterAgent's FormatAgenda task, and execute it
    by directly calling FormatterTool().format_agenda_from_template(meeting_type, context).

    This function avoids any crew.kickoff() and does not rely on a tool registry.
    It is intended for CLI/programmatic use and logs progress and errors.

    Args:
        tasks_path: Optional override path to tasks.yaml

    Returns:
        The absolute path to the generated PDF on success; None on failure.
    """
    try:
        with open(tasks_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        logger.error("tasks.yaml not found at %s", tasks_path)
        return None
    except Exception as e:
        logger.exception("Failed to load tasks.yaml: %s", e)
        return None

    # Normalize tasks into an iterable of (name, task_spec) pairs
    items = []
    if isinstance(data, list):
        for idx, item in enumerate(data):
            if isinstance(item, dict):
                # If 'name' is present, use that as identifier; else use index
                name = item.get("name") or f"task_{idx}"
                items.append((name, item))
    elif isinstance(data, dict):
        items = list(data.items())
    else:
        logger.error("Unsupported tasks.yaml structure: %s", type(data))
        return None

    # Find the target task
    target = None
    for key, task in items:
        if not isinstance(task, dict):
            continue
        agent = task.get("agent")
        name_field = task.get("name")
        if agent == "FormatterAgent" and ((name_field == "FormatAgenda") or (name_field is None and key == "FormatAgenda")):
            target = task
            break

    if not target:
        logger.error("FormatAgenda task for FormatterAgent not found in %s", tasks_path)
        return None

    args = target.get("args", {}) or {}
    meeting_type = args.get("meeting_type")
    context = args.get("context")

    if not meeting_type:
        logger.error("FormatAgenda task is missing args.meeting_type")
        return None
    if context is None:
        logger.error("FormatAgenda task is missing args.context")
        return None

    # Dynamically import and execute the tool
    try:
        module = import_module("scribe.tools.formatter_tool")
        FormatterTool = getattr(module, "FormatterTool")
        tool = FormatterTool()
    except Exception as e:
        logger.exception("Failed to import or instantiate FormatterTool: %s", e)
        return None

    logger.info("Executing FormatterTool.format_agenda_from_template: meeting_type=%s", meeting_type)
    try:
        pdf_path = tool.format_agenda_from_template(meeting_type, context)
        logger.info("Agenda PDF generated: %s", pdf_path)
        print(pdf_path)  # Also print to stdout for CLI use
        return pdf_path
    except Exception as e:
        logger.exception("Agenda generation failed: %s", e)
        return None
