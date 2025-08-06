"""
Test script for the OutputTool.

This script tests the functionality of the OutputTool with and without
providing the filename_hint parameter.
"""

import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), \'..\')))
import os
from pathlib import Path

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from scribe.tools.output_tool import OutputTool

def test_output_tool():
    """Test the OutputTool with and without filename_hint."""
    tool = OutputTool()
    
    print("Testing OutputTool...")
    
    # Test 1: With filename_hint provided
    print("\nTest 1: With filename_hint provided")
    content = "This is a test content with filename_hint provided."
    result1 = tool._run(
        content=content,
        filename_hint="test_with_hint"
    )
    
    # Check if the result is a valid file path
    if os.path.exists(result1):
        print(f"✓ Successfully saved content to file: {result1}")
        # Read the file to verify content
        with open(result1, 'r', encoding='utf-8') as f:
            file_content = f.read()
        if file_content == content:
            print(f"✓ File content matches the input content")
        else:
            print(f"✗ File content does not match the input content")
    else:
        print(f"✗ Failed to save content to file: {result1}")
    
    # Test 2: Without filename_hint provided
    print("\nTest 2: Without filename_hint provided")
    content = "This is a test content without filename_hint provided."
    result2 = tool._run(
        content=content
    )
    
    # Check if the result is a valid file path
    if os.path.exists(result2):
        print(f"✓ Successfully saved content to file: {result2}")
        # Read the file to verify content
        with open(result2, 'r', encoding='utf-8') as f:
            file_content = f.read()
        if file_content == content:
            print(f"✓ File content matches the input content")
        else:
            print(f"✗ File content does not match the input content")
    else:
        print(f"✗ Failed to save content to file: {result2}")
    
    # Test 3: With filename_hint set to None explicitly
    print("\nTest 3: With filename_hint set to None explicitly")
    content = "This is a test content with filename_hint set to None explicitly."
    result3 = tool._run(
        content=content,
        filename_hint=None
    )
    
    # Check if the result is a valid file path
    if os.path.exists(result3):
        print(f"✓ Successfully saved content to file: {result3}")
        # Read the file to verify content
        with open(result3, 'r', encoding='utf-8') as f:
            file_content = f.read()
        if file_content == content:
            print(f"✓ File content matches the input content")
        else:
            print(f"✗ File content does not match the input content")
    else:
        print(f"✗ Failed to save content to file: {result3}")
    
    # Check if the filenames contain the expected hints
    print("\nChecking filenames:")
    test1_filename = os.path.basename(result1)
    if "_test_with_hint." in test1_filename:
        print(f"✓ Test 1 filename contains the hint: {test1_filename}")
    else:
        print(f"✗ Test 1 filename does not contain the hint: {test1_filename}")
    
    test2_filename = os.path.basename(result2)
    if "_output." in test2_filename:
        print(f"✓ Test 2 filename contains 'output': {test2_filename}")
    else:
        print(f"✗ Test 2 filename does not contain 'output': {test2_filename}")
    
    test3_filename = os.path.basename(result3)
    if "_output." in test3_filename:
        print(f"✓ Test 3 filename contains 'output': {test3_filename}")
    else:
        print(f"✗ Test 3 filename does not contain 'output': {test3_filename}")
    
    print("\nAll tests completed.")

if __name__ == "__main__":
    test_output_tool()