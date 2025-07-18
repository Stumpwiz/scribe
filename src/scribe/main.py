"""
Main entry point for the Scribe project.

This module imports the crew from crew.py and provides main and run functions
to kickoff the crew's execution. The run function serves as an alias for the
main function.
"""

from typing import Optional, Dict, Any
import logging
import sys
from pathlib import Path
from datetime import datetime
import re

# Import the crew from crew.py
from scribe.crew import crew
from scribe.tools import OutputTool


def setup_logging() -> None:
    """
    Set up logging configuration for the application.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('scribe.log')
        ]
    )


def create_run_summary(result: Any, task_params: Optional[Dict[str, Any]] = None) -> str:
    """
    Create a high-level summary of the crew run and save it to a file.
    
    This function generates a summary of the crew run, including the task parameters
    and the result, and saves it to a file in the output/transcripts/ directory.
    
    Args:
        result: The result of the crew execution
        task_params: Optional parameters passed to the tasks
        
    Returns:
        The path to the created summary file
    """
    # Create the output/transcripts directory if it doesn't exist
    transcripts_dir = Path(__file__).parent / "output" / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    
    # Format the timestamp according to the required format (YYYY-MM-DD_HH-MM-SS)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    # Create the filename
    filename = f"{timestamp}_run_summary.txt"
    
    # Format the summary content
    summary = f"Scribe Crew Run Summary\n"
    summary += f"=====================\n\n"
    summary += f"Timestamp: {timestamp}\n\n"
    
    if task_params:
        summary += f"Task Parameters:\n"
        for key, value in task_params.items():
            summary += f"  {key}: {value}\n"
        summary += f"\n"
    
    summary += f"Result:\n{result}\n"
    
    # Create the full file path
    file_path = transcripts_dir / filename
    
    # Write the summary to the file
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(summary)
        return str(file_path)
    except Exception as e:
        logging.error(f"Error saving run summary to file: {str(e)}")
        return f"Error saving run summary to file: {str(e)}"


def main(task_params: Optional[dict] = None) -> None:
    """
    Main function to kickoff the crew's execution.
    
    This function sets up logging, kicks off the crew execution, creates a run summary,
    and logs the result.
    
    Args:
        task_params: Optional parameters to pass to the tasks
    """
    setup_logging()
    logging.info("Starting Scribe crew execution")
    
    try:
        # Kickoff the crew
        result = crew.kickoff(inputs=task_params)
        
        # Create a run summary
        summary_path = create_run_summary(result, task_params)
        logging.info(f"Run summary saved to: {summary_path}")
        
        # Log the result
        logging.info(f"Crew execution completed successfully")
        logging.info(f"Result: {result}")
        
        return result
    except Exception as e:
        logging.error(f"Error during crew execution: {str(e)}")
        raise


def run(task_params: Optional[dict] = None) -> None:
    """
    Alias for the main function to kickoff the crew's execution.
    
    This function is an alias for the main function. It sets up logging,
    kicks off the crew execution, creates a run summary, and logs the result.
    
    Args:
        task_params: Optional parameters to pass to the tasks
    """
    return main(task_params)


if __name__ == "__main__":
    # When run directly, execute the main function
    main()