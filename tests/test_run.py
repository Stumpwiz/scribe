"""
Test script to run the Scribe project.

This script adds the src directory to the Python path and then imports and runs
the main function from the scribe.main module.
"""

import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), \'..\')))
import os
from pathlib import Path

def run_test():
    """Run the Scribe project."""
    try:
        # Add the src directory to the Python path
        src_dir = Path(__file__).parent.parent / "src"
        sys.path.insert(0, str(src_dir))
        print(f"Added {src_dir} to Python path")
        
        # Import and run the main function
        from scribe.main import main
        print("Imported main function, running...")
        result = main()
        print(f"Main function completed with result: {result}")
        
        # Check if log files were created
        output_logs_dir = src_dir / "scribe" / "output" / "logs"
        output_transcripts_dir = src_dir / "scribe" / "output" / "transcripts"
        
        if output_logs_dir.exists():
            log_files = list(output_logs_dir.glob("*.txt"))
            print(f"Found {len(log_files)} log files in {output_logs_dir}")
            for log_file in log_files:
                print(f"  - {log_file.name}")
        else:
            print(f"No log files found in {output_logs_dir}")
            
        if output_transcripts_dir.exists():
            transcript_files = list(output_transcripts_dir.glob("*.txt"))
            print(f"Found {len(transcript_files)} transcript files in {output_transcripts_dir}")
            for transcript_file in transcript_files:
                print(f"  - {transcript_file.name}")
        else:
            print(f"No transcript files found in {output_transcripts_dir}")
            
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    run_test()