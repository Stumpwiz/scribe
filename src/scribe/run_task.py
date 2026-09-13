"""
CLI script to execute a named task from src/scribe/config/tasks.yaml.

Purpose
- Allow users to execute any tool-backed task defined in tasks.yaml via --task-name.

Behavior
- Parses one required argument: --task-name <TaskName>
- Loads tasks.yaml relative to this file location (no hardcoded paths)
- Locates the task by its name field (for list-style YAML) or by key (for dict-style YAML)
- For FormatterAgent tasks that specify the tool 'format_agenda_from_template',
  imports FormatterTool and calls FormatterTool().format_agenda_from_template(meeting_type, context)
- Logs progress and prints the resulting output path (or an error) to the terminal

Constraints
- Standalone CLI; no GUI or crew.kickoff() invocation
- Paths resolved with Path(__file__).resolve()
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Tuple, Optional

import yaml

# Ensure the src/ folder is in sys.path
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configure root logging (can be overridden by host application)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _project_paths() -> Tuple[Path, Path]:
    """Return (src_dir, config_dir) based on this file location."""
    src_dir = Path(__file__).resolve().parents[1]  # .../src/scribe -> parents[1] == .../src
    config_dir = src_dir / "scribe" / "config"
    return src_dir, config_dir


def _load_tasks_yaml(config_dir: Path) -> Any:
    tasks_path = config_dir / "tasks.yaml"
    try:
        with tasks_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data
    except FileNotFoundError:
        logger.error("tasks.yaml not found at %s", tasks_path)
        return None
    except Exception as e:
        logger.exception("Failed to load tasks.yaml: %s", e)
        return None


def _list_tasks(data: Any) -> None:
    """Print all tasks in a readable format.

    For each task, print: "- <task name> (agent: <agent name>)".
    If the task has no 'name' field, display "[unnamed task]" as the name.
    """
    print("Available tasks:")
    if isinstance(data, dict):
        for _key, spec in data.items():
            if not isinstance(spec, dict):
                continue
            name = spec.get("name") or "[unnamed task]"
            agent = spec.get("agent") or "unknown"
            print(f"- {name} (agent: {agent})")
    elif isinstance(data, list):
        for spec in data:
            if not isinstance(spec, dict):
                continue
            name = spec.get("name") or "[unnamed task]"
            agent = spec.get("agent") or "unknown"
            print(f"- {name} (agent: {agent})")
    else:
        logger.error("Unsupported tasks.yaml structure: %s", type(data))


def _find_task(data: Any, task_name: str) -> Optional[Dict[str, Any]]:
    """Find a task by name in either dict- or list-style YAML structures.

    - If data is a dict: keys are task ids; we match exact key or look for nested name == task_name.
    - If data is a list: items are dicts; we match item.get("name") == task_name.
    Returns the task spec dict if found, else None.
    """
    if isinstance(data, dict):
        # Direct key match
        if task_name in data and isinstance(data[task_name], dict):
            return data[task_name]
        # Fallback: search by embedded name field
        for _key, spec in data.items():
            if isinstance(spec, dict) and spec.get("name") == task_name:
                return spec
        return None
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and item.get("name") == task_name:
                return item
        return None
    return None


def _execute_task(task_spec: Dict[str, Any]) -> int:
    """Execute a tool-backed task based on its spec.

    Currently supports:
    - FormatterAgent with tool 'format_agenda_from_template'

    Returns process exit code: 0 on success, non-zero on error.
    """
    agent = task_spec.get("agent")
    tools = task_spec.get("tools") or []
    args = task_spec.get("args") or {}

    # Normalize tools to list of strings
    if isinstance(tools, str):
        tools = [tools]

    logger.info("Task found: agent=%s, tools=%s", agent, tools)

    # Handle FormatterAgent -> FormatterTool.format_agenda_from_template
    if agent == "FormatterAgent" and any(t == "format_agenda_from_template" for t in tools):
        meeting_type = args.get("meeting_type")
        context = args.get("context")
        if not meeting_type:
            logger.error("Missing required args.meeting_type for format_agenda_from_template")
            return 2
        if context is None:
            logger.error("Missing required args.context for format_agenda_from_template")
            return 3
        try:
            from scribe.tools.formatter_tool import FormatterTool
        except Exception as e:
            logger.exception("Failed to import FormatterTool: %s", e)
            return 4
        try:
            logger.info("Invoking FormatterTool.format_agenda_from_template ...")
            pdf_path = FormatterTool().format_agenda_from_template(meeting_type, context)
            logger.info("Resulting PDF: %s", pdf_path)
            print(pdf_path)
            return 0
        except Exception as e:
            logger.exception("Error executing format_agenda_from_template: %s", e)
            print(f"Error: {e}")
            return 5

    # Handle FormatterAgent -> FormatterTool.transcribe_audio when tools == ["transcribe_audio"]
    if agent == "FormatterAgent" and isinstance(tools, list) and len(tools) == 1 and tools[0] == "transcribe_audio":
        # Validate args
        audio_path = args.get("audio_path") if isinstance(args, dict) else None
        if not audio_path:
            logger.error("Missing required args.audio_path for transcribe_audio")
            return 2
        # Check file existence
        try:
            from pathlib import Path as _Path
            audio_fp = _Path(audio_path).expanduser()
            if not audio_fp.exists() or not audio_fp.is_file():
                logger.error("Audio file does not exist: %s", audio_fp)
                return 2
        except Exception as e:
            logger.exception("Error validating audio_path: %s", e)
            return 5
        # Import and invoke tool
        try:
            from scribe.tools.formatter_tool import FormatterTool
        except Exception as e:
            logger.exception("Failed to import FormatterTool: %s", e)
            return 4
        try:
            logger.info("Invoking FormatterTool.transcribe_audio ...")
            txt_path = FormatterTool().transcribe_audio(str(audio_fp))
            logger.info("Transcript generated: %s", txt_path)
            print(txt_path)
            return 0
        except FileNotFoundError as e:
            # In case the file is removed between validation and call
            logger.error("Audio file not found: %s", e)
            print(f"Error: {e}")
            return 2
        except Exception as e:
            logger.exception("Error executing transcribe_audio: %s", e)
            print(f"Error: {e}")
            return 5

    logger.error(
        "Unsupported task configuration for CLI execution. Agent=%s, tools=%s",
        agent,
        tools,
    )
    return 10


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run or list tasks defined in tasks.yaml")
    parser.add_argument(
        "--task-name",
        required=False,
        help="Name of the task to execute (matches the 'name' field or dict key)",
    )
    parser.add_argument(
        "--list-tasks",
        action="store_true",
        help="List all available tasks and exit",
    )

    args = parser.parse_args(argv)

    _src_dir, config_dir = _project_paths()
    data = _load_tasks_yaml(config_dir)
    if data is None:
        return 1

    # If --list-tasks is specified, prioritize it and do not execute any task
    if getattr(args, "list_tasks", False):
        _list_tasks(data)
        return 0

    if not args.task_name:
        logger.error("--task-name is required when not using --list-tasks")
        parser.print_help()
        return 2

    task_spec = _find_task(data, args.task_name)
    if not task_spec:
        logger.error("Task '%s' not found in tasks.yaml", args.task_name)
        return 1

    return _execute_task(task_spec)


if __name__ == "__main__":
    sys.exit(main())
