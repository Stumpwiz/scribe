"""
Test script for the LaTeXCompilerTool cleanup functionality.

This script tests the cleanup of auxiliary files after LaTeX compilation.
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

def test_latex_cleanup():
    """Test the cleanup of auxiliary files after LaTeX compilation."""
    # Configure logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create a simple test .tex file
    test_dir = Path(__file__).parent.parent / "src" / "scribe" / "output" / "test"
    test_dir.mkdir(parents=True, exist_ok=True)
    
    test_tex_path = test_dir / "test_cleanup.tex"
    
    # Simple LaTeX content
    latex_content = r"""
\documentclass{article}
\begin{document}
This is a test document for testing the cleanup of auxiliary files.
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
        
        # Check for auxiliary files
        aux_extensions = ['.aux', '.log', '.out', '.toc']
        remaining_files = []
        
        print("\nChecking for auxiliary files:")
        for ext in aux_extensions:
            aux_file = output_dir / f"{base_filename}{ext}"
            if aux_file.exists():
                print(f"  ✗ {base_filename}{ext} still exists (not cleaned up)")
                remaining_files.append(f"{base_filename}{ext}")
            else:
                print(f"  ✓ {base_filename}{ext} was cleaned up")
        
        if not remaining_files:
            print("\nAll auxiliary files were successfully cleaned up!")
        else:
            print(f"\nSome auxiliary files were not cleaned up: {', '.join(remaining_files)}")
            
        # Verify that the .tex file still exists (should be preserved)
        if test_tex_path.exists():
            print(f"\n✓ Source .tex file was preserved as expected: {test_tex_path}")
        else:
            print(f"\n✗ ERROR: Source .tex file was deleted: {test_tex_path}")
            
        # Verify that the .pdf file exists (should be preserved)
        pdf_path = test_tex_path.with_suffix(".pdf")
        if pdf_path.exists():
            print(f"✓ PDF file was preserved as expected: {pdf_path}")
        else:
            print(f"✗ ERROR: PDF file was not found: {pdf_path}")
    else:
        print(f"\nCompilation failed: {result['log']}")

if __name__ == "__main__":
    test_latex_cleanup()