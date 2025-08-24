"""
Task configuration module for the Scribe project.

This module provides:
- TaskConfig for loading and parsing task configurations from YAML files; and
- monitor_and_ingest_email_reports: a CrewAI-compatible task function for the
  IngestorAgent to monitor email, classify council-related messages, and
  organize their attachments.
"""

from typing import Dict, List, Any
import yaml
from dataclasses import dataclass
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


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


async def monitor_and_ingest_email_reports(self, agent, task) -> Dict[str, Any]:
    """
    Monitor the Council Secretary's Gmail inbox, classify council-related messages,
    and organize their attachments into Reports/YYYY-MM/.

    Flow:
    1. Use EmailInboxMonitorTool to retrieve recent Gmail messages (placeholder stub).
    2. For each message, use EmailClassifierTool to determine if it is Council-related
       based on originator (assets/recipients/*.json), subject, or content.
    3. For classified messages, use AttachmentOrganizerTool to save attachments
       under Reports/YYYY-MM/ and return file paths and metadata.

    Returns a structured dictionary with:
    - success: bool
    - messageCount: int
    - classifiedCount: int
    - attachmentsSaved: List[str]
    - log: str (summary of actions or errors)

    Notes:
    - Tool implementations are assumed to be stubbed/mocked. This function only
      coordinates tool calls and handles aggregation and logging.
    """
    logger.info("📥 IngestorAgent: Beginning inbox scan...")
    log_lines: List[str] = []
    attachments_saved: List[str] = []
    message_count = 0
    classified_count = 0

    # Resolve assets/recipients directory
    recipients_dir = (Path(__file__).parent.parent / "assets" / "recipients").resolve()

    # Try to import the expected tools; if unavailable, create minimal stubs so
    # tests can patch/mock them without ImportError.
    try:
        from scribe.tools.email_inbox_monitor_tool import EmailInboxMonitorTool  # type: ignore
    except Exception:
        class EmailInboxMonitorTool:  # minimal stub
            def _run(self, **kwargs):
                return []
        log_lines.append("EmailInboxMonitorTool not found; using stub that returns no messages")

    try:
        from scribe.tools.email_classifier_tool import EmailClassifierTool  # type: ignore
    except Exception:
        class EmailClassifierTool:  # minimal stub
            def _run(self, **kwargs):
                # Default to not relevant
                return {"relevant": False, "reason": "stub"}
        log_lines.append("EmailClassifierTool not found; using stub that marks all messages as not relevant")

    try:
        from scribe.tools.attachment_organizer_tool import AttachmentOrganizerTool  # type: ignore
    except Exception:
        class AttachmentOrganizerTool:  # minimal stub
            def _run(self, **kwargs):
                return {"success": True, "saved": []}
        log_lines.append("AttachmentOrganizerTool not found; using stub that saves nothing")

    try:
        inbox_tool = EmailInboxMonitorTool()
        classifier_tool = EmailClassifierTool()
        organizer_tool = AttachmentOrganizerTool()

        log_lines.append("Initialized email monitoring, classification, and organizer tools")

        # Step 1: Retrieve recent Gmail messages (placeholder behavior)
        # We allow tools/tests to decide the retrieval specifics via kwargs in task.context
        raw_context = getattr(task, "context", None)
        context = raw_context if isinstance(raw_context, dict) else {}
        monitor_kwargs = context.get("monitor_kwargs", {})
        messages = inbox_tool._run(**monitor_kwargs)
        if messages is None:
            messages = []
        if not isinstance(messages, list):
            # Normalize to list if tool returns a dict/object
            messages = [messages]
        message_count = len(messages)
        log_lines.append(f"Retrieved {message_count} message(s) from inbox monitor")

        # Step 2 and 3: Classify and organize attachments
        for idx, msg in enumerate(messages, start=1):
            try:
                classification = classifier_tool._run(
                    message=msg,
                    recipients_dir=str(recipients_dir)
                )
                is_relevant = False
                if isinstance(classification, dict):
                    is_relevant = bool(classification.get("relevant", False))
                elif isinstance(classification, bool):
                    is_relevant = classification
                else:
                    is_relevant = False

                reason = None
                if isinstance(classification, dict):
                    reason = classification.get("reason")

                if is_relevant:
                    classified_count += 1
                    log_lines.append(f"Message {idx}: classified as relevant ({reason or 'no reason provided'})")
                    # Organizer: save attachments to Reports/YYYY-MM/
                    organize_kwargs = {
                        "message": msg,
                        "base_dir": "Reports",  # tool decides the YYYY-MM subfolder
                    }
                    result = organizer_tool._run(**organize_kwargs)
                    if isinstance(result, dict):
                        saved = result.get("saved") or result.get("attachmentsSaved") or []
                        # Normalize saved to a list of strings
                        if isinstance(saved, str):
                            saved = [saved]
                        if isinstance(saved, list):
                            attachments_saved.extend([str(p) for p in saved])
                        log_lines.append(f"Message {idx}: saved {len(saved)} attachment(s)")
                    else:
                        log_lines.append(f"Message {idx}: organizer returned non-dict result; skipped aggregation")
                else:
                    log_lines.append(f"Message {idx}: not relevant ({reason or 'no reason provided'})")
            except Exception as e:
                logger.exception("Error processing message during classification/organization")
                log_lines.append(f"Message {idx}: error during processing: {e}")

        success = True
        summary = "; ".join(log_lines)
        logger.info(f"✅ IngestorAgent: Ingestion task complete. {message_count} messages processed.")
        return {
            "success": success,
            "messageCount": message_count,
            "classifiedCount": classified_count,
            "attachmentsSaved": attachments_saved,
            "log": summary,
        }

    except Exception as e:
        logger.exception("monitor_and_ingest_email_reports encountered an error")
        log_lines.append(f"Fatal error: {e}")
        return {
            "success": False,
            "messageCount": message_count,
            "classifiedCount": classified_count,
            "attachmentsSaved": attachments_saved,
            "log": "; ".join(log_lines),
        }

# Simple registry mapping for external task functions per CrewAI v0.14+ conventions
TASK_REGISTRY: Dict[str, Any] = {}
TASK_REGISTRY["monitor_and_ingest_email_reports"] = monitor_and_ingest_email_reports