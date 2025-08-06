import os
import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), \'..\')))
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from scribe.config.loader import load_task_from_yaml

def test_load_task_with_context():
    """Test loading a task with context variables for interpolation."""
    print("Testing task loading with context...")
    
    # Test with valid context
    context = {
        "meeting_date": "2025-08-15",
        "meeting_type": "Regular Council Meeting",
        "email_recipients": ["council@example.com", "staff@example.com"],
        "old_business_items": ["Review previous minutes", "Budget approval"],
        "new_business_items": ["Committee elections", "Event planning"]
    }
    
    try:
        task = load_task_from_yaml("send_meeting_notification", context)
        print(f"Successfully loaded task: {task.description[:50]}...")
        print(f"Expected output: {task.expected_output[:50]}...")
        print("Test passed!")
    except Exception as e:
        print(f"Error loading task with valid context: {e}")
    
    # Test with missing context variable
    print("\nTesting with missing context variable...")
    try:
        incomplete_context = {"meeting_date": "2025-08-15"}
        task = load_task_from_yaml("send_meeting_notification", incomplete_context)
        print("Warning: Test should have failed with missing context variables")
    except Exception as e:
        print(f"Expected error occurred: {e}")
        print("Test passed!")
    
    # Test with invalid field in task_spec
    print("\nTesting task with invalid field...")
    try:
        task = load_task_from_yaml("hello_world", {})
        print(f"Successfully loaded task and removed invalid fields")
        print("Test passed!")
    except Exception as e:
        print(f"Error loading task with invalid field: {e}")
        
    # Test with custom task that has interpolation in both description and expected_output
    print("\nTesting custom task with interpolation in both fields...")
    try:
        # Create a temporary task with interpolation variables
        from scribe.config.loader import TASKS_PATH
        import yaml
        
        # Load existing tasks
        with open(TASKS_PATH, "r", encoding="utf-8") as f:
            tasks_data = yaml.safe_load(f)
        
        # Add a temporary test task with interpolation in both fields
        tasks_data["test_interpolation"] = {
            "description": "This is a test task for {date} with {count} items.",
            "expected_output": "Expected output for {date} with {count} items.",
            "agent": "ReminderAgent",
            "tools": ["output_tool"]
        }
        
        # Save the modified tasks
        with open(TASKS_PATH, "w", encoding="utf-8") as f:
            yaml.dump(tasks_data, f)
            
        # Test interpolation
        test_context = {
            "date": "2025-08-20",
            "count": 5
        }
        
        task = load_task_from_yaml("test_interpolation", test_context)
        print(f"Description after interpolation: {task.description}")
        print(f"Expected output after interpolation: {task.expected_output}")
        
        # Verify interpolation worked correctly
        if "2025-08-20" in task.description and "5" in task.description and \
           "2025-08-20" in task.expected_output and "5" in task.expected_output:
            print("Interpolation test passed!")
        else:
            print("Interpolation test failed!")
            
        # Remove the temporary task
        with open(TASKS_PATH, "r", encoding="utf-8") as f:
            tasks_data = yaml.safe_load(f)
        
        if "test_interpolation" in tasks_data:
            del tasks_data["test_interpolation"]
            
        with open(TASKS_PATH, "w", encoding="utf-8") as f:
            yaml.dump(tasks_data, f)
            
    except Exception as e:
        print(f"Error in interpolation test: {e}")

if __name__ == "__main__":
    test_load_task_with_context()