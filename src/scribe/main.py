"""
Main entry point for the Scribe project.

This module imports the crew from crew.py and provides main and run functions
to kickoff the crew's execution. The run function serves as an alias for the
main function.
"""

"""
Main entry point for the Scribe project.
Supports both CLI execution of the Crew and Flask-based UI for ReminderAgent.
"""

from typing import Optional, Dict, Any
import logging
import sys
from pathlib import Path
from datetime import datetime

from scribe.crew import crew
from scribe.tools import OutputTool

# Optional: import Flask app entry point
from scribe.ui import create_app


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('scribe.log')
        ]
    )


def create_run_summary(result: Any, task_params: Optional[Dict[str, Any]] = None) -> str:
    transcripts_dir = Path(__file__).parent / "output" / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{timestamp}_run_summary.txt"
    summary = f"Scribe Crew Run Summary\n=====================\n\nTimestamp: {timestamp}\n\n"

    if task_params:
        summary += f"Task Parameters:\n"
        for key, value in task_params.items():
            summary += f"  {key}: {value}\n"
        summary += "\n"

    summary += f"Result:\n{result}\n"
    file_path = transcripts_dir / filename

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(summary)
        return str(file_path)
    except Exception as e:
        logging.error(f"Error saving run summary to file: {str(e)}")
        return f"Error saving run summary to file: {str(e)}"


def main(task_params: Optional[dict] = None) -> None:
    setup_logging()
    logging.info("Starting Scribe crew execution")

    try:
        result = crew.kickoff(inputs=task_params)
        summary_path = create_run_summary(result, task_params)
        logging.info(f"Run summary saved to: {summary_path}")
        logging.info(f"Result: {result}")
        return result
    except Exception as e:
        logging.error(f"Error during crew execution: {str(e)}")
        raise


def run(task_params: Optional[dict] = None) -> None:
    return main(task_params)


if __name__ == "__main__":
    if "--web" in sys.argv:
        app = create_app()
        app.run(debug=True)
    else:
        main()
