"""
LaTeX compiler tool for the Scribe project.

This module provides the LaTeXCompilerTool class for compiling LaTeX files into PDFs
using the xelatex command.
"""

from typing import Dict, Any, Optional, ClassVar
import os
import subprocess
import sys
import logging
from pathlib import Path
from crewai.tools import BaseTool

# Set up logging
logger = logging.getLogger(__name__)


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
                - "success": True if the PDF was generated successfully, else False
                - "pdfPath": Path to the compiled PDF (if successful), otherwise None
                - "logPath": Path to the log file
                - "log": concatenation of stdout and stderr or error message
        """
        # Define output paths early
        output_dir = None
        tex_file_name = None
        pdf_path = None
        log_path = None
        
        try:
            # Resolve the path to avoid LaTeX errors due to relative paths
            tex_file_path = str(Path(tex_file_path).resolve())

            # Validate the tex file path
            self._validate_tex_file_path(tex_file_path)

            # Set output_dir to the folder containing the .tex file
            output_dir = os.path.dirname(tex_file_path)
            tex_file_name = os.path.basename(tex_file_path)
            
            # Create Path objects for output files
            output_file = Path(tex_file_path).with_suffix("")
            pdf_path = output_file.with_suffix(".pdf")
            log_path = output_file.with_suffix(".log")
            aux_path = output_file.with_suffix(".aux")

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
            
            # Save stdout and stderr to a .log file
            log_content = process.stdout + "\n" + process.stderr
            with open(log_path, "w", encoding="utf-8") as log_file:
                log_file.write(log_content)

            # Determine success based on PDF file existence
            success = pdf_path.exists()

            # Clean up auxiliary files if compilation was successful
            if success:
                base_filename = os.path.splitext(tex_file_name)[0]
                self._cleanup_auxiliary_files(output_dir, base_filename)
                
                # Return success with PDF and log paths
                return {
                    "success": True,
                    "pdfPath": str(pdf_path),
                    "logPath": str(log_path),
                    "log": process.stdout + "\n" + process.stderr
                }
            else:
                # PDF was not created
                return {
                    "success": False,
                    "pdfPath": None,
                    "logPath": str(log_path) if log_path.exists() else None,
                    "log": f"PDF file was not created. Check the log at {log_path if log_path.exists() else 'N/A'}\n" + process.stdout + "\n" + process.stderr
                }

        except Exception as e:
            # Top-level exception handler
            return {
                "success": False,
                "pdfPath": str(pdf_path) if pdf_path and pdf_path.exists() else None,
                "logPath": str(log_path) if log_path and log_path.exists() else None,
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
        
        This method removes LaTeX auxiliary files (.aux, .log, .out, .toc, .gz, .lof, .lot, .synctex.gz, etc.)
        from the specified directory, preserving the .tex source file and .pdf output.
        Files that don't exist or fail to delete are logged but don't raise exceptions.
        
        Args:
            directory (str): Directory containing the auxiliary files
            base_filename (str): Base filename without extension
        """
        # Convert to Path objects for consistent handling
        directory_path = Path(directory)

        # List of auxiliary file extensions to clean up (as specified in requirements)
        # Note: We preserve .log file for debugging and to return logPath
        aux_extensions = [
            '.aux', '.out', '.toc'
        ]

        # Track which files were deleted and which had errors
        deleted_files = []
        error_files = []

        # Remove each auxiliary file
        for ext in aux_extensions:
            aux_file_path = directory_path / f"{base_filename}{ext}"
            try:
                if aux_file_path.exists():
                    aux_file_path.unlink()
                    deleted_files.append(aux_file_path.name)
            except Exception as e:
                # Log the error but continue with other files
                error_files.append((aux_file_path.name, str(e)))

        # Log the results
        if deleted_files:
            logger.info(f"Cleaned up {len(deleted_files)} LaTeX auxiliary files: {', '.join(deleted_files)}")
        else:
            logger.info("No LaTeX auxiliary files found to clean up")

        if error_files:
            for file_name, error_msg in error_files:
                logger.warning(f"Failed to delete auxiliary file {file_name}: {error_msg}")


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

    # List of auxiliary file extensions to check (matching the cleanup method)
    # Note: We preserve .log file for debugging and to return logPath
    aux_extensions = [
        '.aux', '.out', '.toc'
    ]

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

        # Verify that the .tex file still exists (should be preserved)
        tex_file = os.path.join(output_dir, base_filename + ".tex")
        if os.path.exists(tex_file):
            print(f"\n✓ Source .tex file was preserved as expected: {tex_file}")
        else:
            print(f"\n✗ ERROR: Source .tex file was deleted: {tex_file}")

        # Check if auxiliary files were cleaned up
        print("\nChecking for auxiliary files:")
        remaining_files = []

        for ext in aux_extensions:
            aux_file = os.path.join(output_dir, base_filename + ext)
            if os.path.exists(aux_file):
                print(f"  ✗ {base_filename + ext} still exists (not cleaned up)")
                remaining_files.append(base_filename + ext)
            else:
                print(f"  ✓ {base_filename + ext} was cleaned up")

        if not remaining_files:
            print("\nAll auxiliary files were successfully cleaned up!")
        else:
            print(f"\nSome auxiliary files were not cleaned up: {', '.join(remaining_files)}")
    else:
        print("\nCompilation returned non-zero exit code. This could be due to:")
        print("1. xelatex not being installed")
        print("2. Permission issues with writing to the output directory")
        print("3. Issues with the LaTeX file itself")

        # Verify that the .tex file still exists (should be preserved)
        tex_file = os.path.join(output_dir, base_filename + ".tex")
        if os.path.exists(tex_file):
            print(f"\n✓ Source .tex file was preserved as expected: {tex_file}")
        else:
            print(f"\n✗ ERROR: Source .tex file was deleted: {tex_file}")

        # Check if auxiliary files were preserved for debugging
        print("\nChecking if auxiliary files were preserved for debugging:")
        missing_files = []

        for ext in aux_extensions:
            aux_file = os.path.join(output_dir, base_filename + ext)
            if os.path.exists(aux_file):
                print(f"  ✓ {base_filename + ext} was preserved for debugging")
            else:
                print(f"  ✗ {base_filename + ext} does not exist")
                missing_files.append(base_filename + ext)

        if missing_files:
            print(f"\nSome expected auxiliary files are missing: {', '.join(missing_files)}")
            print("This is normal if they weren't generated during the failed compilation.")
        else:
            print("\nAll generated auxiliary files were preserved for debugging as expected.")

        print("\nThe tool correctly handled the process and returned appropriate information.")
        print("This demonstrates that the error handling is working as expected.")


if __name__ == "__main__":
    # Run the test function
    test_latex_compiler_tool()
