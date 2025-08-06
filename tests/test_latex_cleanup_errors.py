"""
Test script for the LaTeXCompilerTool cleanup error handling.

This script tests the error handling during cleanup of auxiliary files.
"""

import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), \'..\')))
import os
from pathlib import Path
import logging

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from src.scribe.tools.latex_compiler_tool import LaTeXCompilerTool

def test_latex_cleanup_errors():
    """Test error handling during cleanup of auxiliary files."""
    # Configure logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create a simple test .tex file
    test_dir = Path(__file__).parent.parent / "src" / "scribe" / "output" / "test"
    test_dir.mkdir(parents=True, exist_ok=True)
    
    test_tex_path = test_dir / "test_cleanup_errors.tex"
    
    # Simple LaTeX content
    latex_content = r"""
\documentclass{article}
\begin{document}
This is a test document for testing error handling during cleanup.
\end{document}
"""
    
    # Write the test .tex file
    with open(test_tex_path, "w") as f:
        f.write(latex_content)
    
    print(f"Created test file: {test_tex_path}")
    
    # Create an instance of the LaTeXCompilerTool
    tool = LaTeXCompilerTool()
    
    # Run the LaTeXCompilerTool
    result = tool._run(tex_file_path=str(test_tex_path))
    
    # Print the result
    print("\nCompilation Result:")
    print(f"Success: {result['success']}")
    print(f"PDF Path: {result['pdfPath']}")
    
    # Check if the PDF was created
    if result["success"]:
        print(f"\nPDF file created successfully: {result['pdfPath']}")
        
        # Get the base filename and directory
        output_dir = test_tex_path.parent
        base_filename = test_tex_path.stem
        
        # Create a read-only auxiliary file to test error handling
        aux_file = output_dir / f"{base_filename}.aux"
        if not aux_file.exists():
            # Create the file if it doesn't exist
            with open(aux_file, "w") as f:
                f.write("Test auxiliary file")
        
        # Make the file read-only to cause permission error during deletion
        try:
            # On Windows, make the file read-only
            os.chmod(aux_file, 0o444)  # Read-only for all users
            print(f"Made {aux_file} read-only")
            
            # Try to compile again, which should trigger cleanup error handling
            print("\nRunning compilation again with read-only auxiliary file...")
            result2 = tool._run(tex_file_path=str(test_tex_path))
            
            print("\nSecond Compilation Result:")
            print(f"Success: {result2['success']}")
            print(f"PDF Path: {result2['pdfPath']}")
            
            # Reset file permissions
            os.chmod(aux_file, 0o666)  # Read-write for all users
            
            # Clean up test files
            if aux_file.exists():
                aux_file.unlink()
            
        except Exception as e:
            print(f"Error during permission test: {e}")
    else:
        print(f"\nCompilation failed: {result['log']}")

if __name__ == "__main__":
    test_latex_cleanup_errors()