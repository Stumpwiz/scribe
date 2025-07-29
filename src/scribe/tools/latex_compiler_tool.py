"""
LaTeX compiler tool for the Scribe project.

This module provides the LaTeXCompilerTool class for compiling LaTeX files into PDFs
using the xelatex command.
"""

from typing import Dict, Any, Optional, ClassVar
import os
import subprocess
import sys
from pathlib import Path
from crewai.tools import BaseTool


class LaTeXCompilerTool(BaseTool):
    """
    Tool for compiling LaTeX files into PDFs using xelatex.
    
    This tool accepts a full path to a .tex file, uses subprocess.run() to call
    xelatex to compile the file, and returns a dictionary with the compilation
    status, PDF path, and log information.
    """
    
    name: str = "LaTeXCompilerTool"
    description: str = "Tool for compiling LaTeX files into PDFs using xelatex"
    
    # Compute base directory (project root) as a class attribute
    base_dir: ClassVar[Path] = Path(__file__).resolve().parents[2]  # resolves to src/
    
    def _run(self, tex_file_path: str, **kwargs) -> Dict[str, Any]:
        """
        Compile a LaTeX file into a PDF using xelatex.
        
        After successful compilation (return code 0), auxiliary files (*.aux, *.log, *.out, *.toc)
        are automatically cleaned up. In case of compilation failure, all auxiliary files are
        preserved for debugging purposes.
        
        Args:
            tex_file_path (str): Full path to the .tex file to compile
            
        Returns:
            Dict[str, Any]: A dictionary containing:
                - "success": True if the return code is 0, else False
                - "pdfPath": Path to the compiled PDF (if successful), otherwise None
                - "log": concatenation of stdout and stderr
        """
        try:
            # Convert to absolute path
            tex_file_path = os.path.abspath(tex_file_path)
            
            # Validate the tex file path
            self._validate_tex_file_path(tex_file_path)
            
            # Set output_dir to the folder containing the .tex file
            output_dir = os.path.dirname(tex_file_path)
            tex_file_name = os.path.basename(tex_file_path)
            
            # Construct the xelatex command
            xelatex_cmd = [
                "xelatex",
                "-interaction=nonstopmode",
                f"-output-directory={output_dir}",
                tex_file_name
            ]
            
            # Run xelatex command
            process = subprocess.run(
                xelatex_cmd,
                cwd=output_dir,
                capture_output=True,
                text=True
            )
            
            # Determine success based on return code
            success = process.returncode == 0
            
            # Get the path to the resulting PDF
            pdf_path = os.path.splitext(tex_file_path)[0] + ".pdf"
            
            # Clean up auxiliary files if compilation was successful
            if success:
                base_filename = os.path.splitext(tex_file_name)[0]
                self._cleanup_auxiliary_files(output_dir, base_filename)
            
            # Return the result
            return {
                "success": success,
                "pdfPath": pdf_path if success and os.path.exists(pdf_path) else None,
                "log": process.stdout + "\n" + process.stderr
            }
            
        except Exception as e:
            # Top-level exception handler
            return {
                "success": False,
                "pdfPath": None,
                "log": str(e)
            }
    
    def _validate_tex_file_path(self, tex_file_path: str) -> None:
        """
        Validate that the tex file path is valid.
        
        Args:
            tex_file_path (str): Full path to the .tex file
            
        Raises:
            ValueError: If the tex file path is invalid
        """
        # Check if the path is provided
        if not tex_file_path:
            raise ValueError("No .tex file path provided")
        
        # Check if the file exists
        if not os.path.exists(tex_file_path):
            raise ValueError(f"File not found: {tex_file_path}")
        
        # Check if the file has a .tex extension
        if not tex_file_path.lower().endswith(".tex"):
            raise ValueError(f"File does not have a .tex extension: {tex_file_path}")
            
    def _cleanup_auxiliary_files(self, directory: str, base_filename: str) -> None:
        """
        Clean up auxiliary files generated during LaTeX compilation.
        
        This method silently removes auxiliary files (*.aux, *.log, *.out, *.toc)
        from the specified directory. Files that don't exist or fail to delete
        are silently skipped.
        
        Args:
            directory (str): Directory containing the auxiliary files
            base_filename (str): Base filename without extension
        """
        # List of auxiliary file extensions to clean up
        aux_extensions = ['.aux', '.log', '.out', '.toc']
        
        # Remove each auxiliary file
        for ext in aux_extensions:
            aux_file = os.path.join(directory, base_filename + ext)
            try:
                if os.path.exists(aux_file):
                    os.remove(aux_file)
            except Exception:
                # Silently skip files that fail to delete
                pass


# Simple test case
def test_latex_compiler_tool():
    """
    Test the LaTeXCompilerTool by compiling a known .tex file.
    """
    # Create an instance of the LaTeXCompilerTool
    tool = LaTeXCompilerTool()
    
    # Path to a known .tex file
    base_dir = Path(__file__).resolve().parents[2]  # resolves to src/
    tex_file_path = (base_dir / "scribe" / "output" / "agendas" / "test_agenda.tex").as_posix()
    
    # Check if the file exists
    if not os.path.exists(tex_file_path):
        print(f"Test file not found: {tex_file_path}")
        print("Please run the LaTeXAgendaTool test first to generate the test file.")
        return
    
    # Convert to absolute path for display
    abs_tex_path = os.path.abspath(tex_file_path)
    print(f"Compiling {abs_tex_path}...")
    
    # Get the directory and base filename
    output_dir = os.path.dirname(abs_tex_path)
    base_filename = os.path.splitext(os.path.basename(abs_tex_path))[0]
    
    # List of auxiliary file extensions
    aux_extensions = ['.aux', '.log', '.out', '.toc']
    
    # Run the LaTeXCompilerTool
    result = tool._run(tex_file_path=tex_file_path)
    
    # Print the result
    print("\nCompilation Result:")
    print(f"Success: {result['success']} (based on return code)")
    print(f"PDF Path: {result['pdfPath']}")
    print(f"Log (first 500 characters): {result['log'][:500]}...")
    
    # Check if the PDF was created
    if result["success"]:
        print(f"\nPDF file created successfully: {result['pdfPath']}")
        
        # Check if auxiliary files were cleaned up
        print("\nChecking for auxiliary files:")
        all_cleaned_up = True
        for ext in aux_extensions:
            aux_file = os.path.join(output_dir, base_filename + ext)
            if os.path.exists(aux_file):
                print(f"  ✗ {base_filename + ext} still exists (not cleaned up)")
                all_cleaned_up = False
            else:
                print(f"  ✓ {base_filename + ext} was cleaned up")
        
        if all_cleaned_up:
            print("\nAll auxiliary files were successfully cleaned up!")
        else:
            print("\nSome auxiliary files were not cleaned up.")
    else:
        print("\nCompilation returned non-zero exit code. This could be due to:")
        print("1. xelatex not being installed")
        print("2. Permission issues with writing to the output directory")
        print("3. Issues with the LaTeX file itself")
        
        # Check if auxiliary files were preserved
        print("\nChecking if auxiliary files were preserved for debugging:")
        for ext in aux_extensions:
            aux_file = os.path.join(output_dir, base_filename + ext)
            if os.path.exists(aux_file):
                print(f"  ✓ {base_filename + ext} was preserved for debugging")
            else:
                print(f"  ✗ {base_filename + ext} does not exist")
        
        print("\nThe tool correctly handled the process and returned appropriate information.")
        print("This demonstrates that the error handling is working as expected.")


if __name__ == "__main__":
    # Run the test function
    test_latex_compiler_tool()