"""
Test script for the refactored LaTeXCompilerTool.

This script tests the functionality of the LaTeXCompilerTool after refactoring,
focusing on consistent handling of path variables in all code paths.
"""

import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from pathlib import Path

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

import os
import logging
from src.scribe.tools.latex_compiler_tool import LaTeXCompilerTool

def test_latex_compiler_tool_refactor():
    """Test the refactored LaTeXCompilerTool with various scenarios."""
    # Configure logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create an instance of the LaTeXCompilerTool
    tool = LaTeXCompilerTool()
    
    # Test 1: Non-existent file (should trigger exception handling)
    print("\nTest 1: Non-existent file")
    non_existent_path = "D:/Projects/scribe/src/scribe/output/agendas/non_existent.tex"
    result = tool._run(tex_file_path=non_existent_path)
    
    print("Result:")
    print(f"Success: {result['success']}")
    print(f"PDF Path: {result['pdfPath']}")
    print(f"Log Path: {result['logPath']}")
    print(f"Log: {result['log']}")
    
    # Test 2: Invalid file extension (should trigger exception handling)
    print("\nTest 2: Invalid file extension")
    # Create a temporary text file
    temp_file = Path("D:/Projects/scribe/temp_test.txt")
    temp_file.write_text("This is not a LaTeX file")
    
    result = tool._run(tex_file_path=str(temp_file))
    
    print("Result:")
    print(f"Success: {result['success']}")
    print(f"PDF Path: {result['pdfPath']}")
    print(f"Log Path: {result['logPath']}")
    print(f"Log: {result['log']}")
    
    # Clean up
    if temp_file.exists():
        temp_file.unlink()
    
    print("\nTests completed. Verify that all results have consistent structure.")

if __name__ == "__main__":
    test_latex_compiler_tool_refactor()