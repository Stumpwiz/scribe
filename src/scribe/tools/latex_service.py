"""
LaTeX service tool for the Scribe project.

This module provides the LaTeXService class for generating and formatting LaTeX documents.
"""

from typing import List, Dict, Any, Optional, ClassVar
import os
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from jinja2 import Environment, FileSystemLoader


class LaTeXServiceSchema(BaseModel):
    action: str = Field(..., description="Either 'format' or 'compile'")
    content: Optional[str] = Field(None, description="LaTeX source to format or compile")
    template: Optional[str] = Field(None, description="Template string for LaTeX formatting")
    output_file: Optional[str] = Field(None, description="Filename for the PDF output")
    variables: Optional[Dict[str, Any]] = Field(None, description="Variables for templating")


class LaTeXService(BaseTool):
    """
    Tool for generating and formatting LaTeX documents.
    
    This tool allows agents to format content for LaTeX documents,
    generate professional documents using LaTeX templates, and
    compile LaTeX documents into PDF files.
    """

    name: str = "LaTeX Service"
    description: str = "Tool for generating and formatting LaTeX documents"

    # Compute base directory (project root) as a class attribute
    base_dir: ClassVar[Path] = Path(__file__).resolve().parents[2]  # resolves to src/

    def _run(self,
             action: str = "format",
             content: Optional[str] = None,
             template: Optional[str] = None,
             output_file: Optional[str] = None,
             variables: Optional[Dict[str, Any]] = None,
             **kwargs) -> str:
        """
        Run the LaTeX service.
        
        Args:
            action (str): The action to perform ("format", "generate", "compile")
            content (Optional[str]): Content to format or include in the document
            template (Optional[str]): Path to the LaTeX template file
            output_file (Optional[str]): Path for the output file
            variables (Optional[Dict[str, Any]]): Variables to substitute in the template
            
        Returns:
            str: Result of the LaTeX operation
        """
        if action == "format":
            return self._format_content(content)
        elif action == "generate":
            return self._generate_document(template, content, variables, output_file)
        elif action == "compile":
            return self._compile_document(output_file)
        else:
            return f"Unknown action: {action}"

    def _format_content(self, content: Optional[str]) -> str:
        """
        Format content for inclusion in a LaTeX document.
        
        Args:
            content (Optional[str]): Content to format
            
        Returns:
            str: Formatted content
        """
        # In a real implementation, this would format the content for LaTeX
        # For now, we'll just return a placeholder message
        if not content:
            return "Error: No content provided"

        return f"Content formatted for LaTeX:\n{content}"

    def _generate_document(self, template: str, content: Optional[str], variables: Dict[str, Any],
                           output_file: str) -> str:
        templates_dir = self.base_dir / "scribe" / "assets" / "templates"
        env = Environment(loader=FileSystemLoader(templates_dir.as_posix()))
        try:
            template_name = os.path.basename(template)
            jinja_template = env.get_template(template_name)
            rendered = jinja_template.render(**variables)

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(rendered)
            return f"LaTeX document generated and saved to {output_file}"
        except Exception as e:
            return f"Error rendering LaTeX document: {e}"

    def _compile_document(self, output_file: Optional[str]) -> str:
        """
        Compile a LaTeX document into a PDF.
        
        Args:
            output_file (Optional[str]): Path to the LaTeX file to compile
            
        Returns:
            str: Result of the compilation
        """
        # In a real implementation, this would compile the LaTeX document
        # For now, we'll just return a placeholder message
        if not output_file:
            return "Error: No output file provided"

        pdf_file = os.path.splitext(output_file)[0] + ".pdf"

        return (f"LaTeX document {output_file} compiled successfully.\n"
                f"PDF output: {pdf_file}")

    def format_minutes(self,
                       meeting_type: str,
                       meeting_date: str,
                       attendees: List[str],
                       content: str,
                       motions: Optional[List[Dict[str, Any]]] = None,
                       reports: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Format meeting minutes using the council's LaTeX template.
        
        Args:
            meeting_type (str): Type of meeting (council, committee, etc.)
            meeting_date (str): Date of the meeting (YYYY-MM-DD)
            attendees (List[str]): List of meeting attendees
            content (str): Main content of the minutes
            motions (Optional[List[Dict[str, Any]]]): List of motions with details
            reports (Optional[List[Dict[str, Any]]]): List of reports with details
            
        Returns:
            str: Formatted LaTeX document
        """
        # In a real implementation, this would format meeting minutes
        # For now, we'll just return a placeholder message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        attendee_count = len(attendees)
        motion_count = len(motions) if motions else 0
        report_count = len(reports) if reports else 0

        result = (f"Meeting minutes formatted at {timestamp}:\n"
                  f"Meeting: {meeting_type} on {meeting_date}\n"
                  f"Attendees: {attendee_count}\n"
                  f"Motions: {motion_count}\n"
                  f"Reports: {report_count}\n\n"
                  f"LaTeX document would be generated with proper formatting for all sections.")

        return result

    def format_report(self,
                      committee: str,
                      report_date: str,
                      author: str,
                      content: str,
                      recommendations: Optional[List[str]] = None) -> str:
        """
        Format a committee report using the council's LaTeX template.
        
        Args:
            committee (str): Name of the committee
            report_date (str): Date of the report (YYYY-MM-DD)
            author (str): Author of the report
            content (str): Main content of the report
            recommendations (Optional[List[str]]): List of recommendations
            
        Returns:
            str: Formatted LaTeX document
        """
        # In a real implementation, this would format a committee report
        # For now, we'll just return a placeholder message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        recommendation_count = len(recommendations) if recommendations else 0

        result = (f"Committee report formatted at {timestamp}:\n"
                  f"Committee: {committee}\n"
                  f"Date: {report_date}\n"
                  f"Author: {author}\n"
                  f"Recommendations: {recommendation_count}\n\n"
                  f"LaTeX document would be generated with proper formatting for all sections.")

        return result

    def format_agenda(self,
                      meeting_type: str,
                      meeting_date: str,
                      items: List[Dict[str, Any]]) -> str:
        """
        Format a meeting agenda using the council's LaTeX template.
        
        Args:
            meeting_type (str): Type of meeting (council, committee, etc.)
            meeting_date (str): Date of the meeting (YYYY-MM-DD)
            items (List[Dict[str, Any]]): List of agenda items with details
            
        Returns:
            str: Formatted LaTeX document
        """
        # In a real implementation, this would format a meeting agenda
        # For now, we'll just return a placeholder message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        item_count = len(items)

        result = (f"Meeting agenda formatted at {timestamp}:\n"
                  f"Meeting: {meeting_type} on {meeting_date}\n"
                  f"Agenda items: {item_count}\n\n"
                  f"LaTeX document would be generated with proper formatting for all sections.")

        return result

    def convert_to_latex(self,
                         content: str,
                         content_type: str = "text") -> str:
        """
        Convert content to LaTeX format.
        
        Args:
            content (str): Content to convert
            content_type (str): Type of content ("text", "markdown", "html")
            
        Returns:
            str: Converted LaTeX content
        """
        # In a real implementation, this would convert content to LaTeX
        # For now, we'll just return a placeholder message
        return f"Content converted from {content_type} to LaTeX format."
