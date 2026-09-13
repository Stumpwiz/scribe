"""
Meeting agenda generator tool for the Scribe project.

This module provides the MeetingAgendaGeneratorTool class for generating meeting agendas
by orchestrating multiple tools: MeetingCalendarTool, LaTeXAgendaTool, and LaTeXCompilerTool.
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from crewai.tools import BaseTool

from scribe.tools.meeting_calendar_tool import MeetingCalendarTool
from scribe.tools.latex_agenda_tool import LaTeXAgendaTool
from scribe.tools.latex_compiler_tool import LaTeXCompilerTool
from scribe.meeting.agenda_context import AgendaContextBuilder
from scribe.meeting.meeting_config import (
    MEETING_TIME,
    meeting_location_for_type,
    next_meeting_type_for_date,
)
from scribe.meeting.meeting_dates import cycle_from_meeting_date


class MeetingAgendaGeneratorTool(BaseTool):
    """
    Tool for generating meeting agendas by orchestrating multiple tools.
    
    This tool accepts a meeting date, uses MeetingCalendarTool to enrich the context,
    LaTeXAgendaTool to render a .tex agenda file, and LaTeXCompilerTool to compile
    the .tex to .pdf.
    """
    
    name: str = "MeetingAgendaGeneratorTool"
    description: str = "Tool for generating meeting agendas as PDF files"
    _TEMPLATE_BY_MEETING_TYPE = {
        "regular": "agenda_regular.tex.j2",
        "open": "agenda_open.tex.j2",
        "association": "agenda_association.tex.j2",
    }

    def _run(self, meeting_info: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Generate a meeting agenda PDF by orchestrating multiple tools.
        
        Args:
            meeting_info (Dict[str, Any]): Dictionary containing meeting information
                Required keys:
                - meetingDate: date of the meeting in YYYY-MM-DD format
                
        Returns:
            Dict[str, Any]: A dictionary containing:
                - "success": True if the PDF was successfully created, else False
                - "pdfPath": full path to the generated PDF (if success)
                - "logPath": full path to the log file
                - "log": log output from LaTeX compilation
        """
        try:
            # Validate required fields - prioritize ISO format "date" key over formatted "meetingDate"
            meeting_date_iso = meeting_info.get("date") or meeting_info.get("meetingDate")
            if not meeting_date_iso:
                return {
                    "success": False,
                    "pdfPath": None,
                    "log": "Error: Required field 'date' or 'meetingDate' is missing from meeting_info"
                }
            logging.info(f"Generating agenda for meeting date: {meeting_date_iso}")

            # Step 1: Use MeetingCalendarTool to enrich the context (requires ISO format)
            calendar_tool = MeetingCalendarTool()
            calendar_result = calendar_tool._run(meeting_date=meeting_date_iso)
            
            # Check for errors from MeetingCalendarTool
            if "error" in calendar_result and calendar_result["error"]:
                return {
                    "success": False,
                    "pdfPath": None,
                    "log": f"Error from MeetingCalendarTool: {calendar_result['message']}"
                }
            
            # Merge the calendar result with the input meeting_info
            enriched_info = {**calendar_result, **meeting_info}

            # Keep meeting type/template/location internally consistent.
            resolved_meeting_type = str(
                meeting_info.get("meetingType") or calendar_result.get("meetingType") or ""
            ).strip().lower()
            if not resolved_meeting_type:
                return {
                    "success": False,
                    "pdfPath": None,
                    "log": "Error: Could not resolve meetingType from meeting_info/calendar result",
                }
            if resolved_meeting_type not in self._TEMPLATE_BY_MEETING_TYPE:
                return {
                    "success": False,
                    "pdfPath": None,
                    "log": f"Error: Unsupported meetingType '{resolved_meeting_type}'",
                }
            enriched_info["meetingType"] = resolved_meeting_type

            template_name = self._TEMPLATE_BY_MEETING_TYPE[resolved_meeting_type]
            templates_dir = Path(__file__).resolve().parent.parent / "assets" / "templates"
            enriched_info["agendaTemplate"] = str((templates_dir / template_name).resolve())

            if not enriched_info.get("location"):
                enriched_info["location"] = meeting_location_for_type(resolved_meeting_type)
            
            # Canonical meeting time for all meeting types
            enriched_info["meetingTime"] = MEETING_TIME

            if "cycle" not in enriched_info:
                enriched_info["cycle"] = cycle_from_meeting_date(meeting_date_iso)
            
            # Calculate next meeting type and location from the current meeting date
            meeting_date_obj = datetime.fromisoformat(meeting_date_iso).date()
            next_meeting_type = next_meeting_type_for_date(meeting_date_obj)
            next_meeting_location = meeting_location_for_type(next_meeting_type)

            # Set venue information for templates
            enriched_info["thisVenue"] = enriched_info.get("location")
            enriched_info["nextMeetingLocation"] = next_meeting_location

            enriched_info = AgendaContextBuilder.build(enriched_info)
            
            logging.info("Meeting information enriched successfully")
            
            # Step 2: Use LaTeXAgendaTool to render the .tex file
            latex_agenda_tool = LaTeXAgendaTool()
            tex_result = latex_agenda_tool._run(meeting_info=enriched_info)
            
            # Check for errors from LaTeXAgendaTool
            if "error" in tex_result:
                return {
                    "success": False,
                    "pdfPath": None,
                    "log": f"Error from LaTeXAgendaTool: {tex_result['error']}"
                }
            
            # Extract the tex file path from the result
            if "texPath" not in tex_result:
                return {
                    "success": False,
                    "pdfPath": None,
                    "log": "Error: LaTeXAgendaTool did not return a texPath"
                }
                
            tex_file_path = tex_result["texPath"]
            logging.info(f"LaTeX agenda file generated successfully: {tex_file_path}")
            
            # Step 3: Use LaTeXCompilerTool to compile the .tex to PDF
            compiler_tool = LaTeXCompilerTool()
            compilation_result = compiler_tool._run(tex_file_path=tex_file_path)
            
            logging.info(f"LaTeX compilation completed with success={compilation_result['success']}")
            
            # Return the compilation result
            return compilation_result
            
        except Exception as e:
            logging.error(f"Error in MeetingAgendaGeneratorTool: {str(e)}")
            return {
                "success": False,
                "pdfPath": None,
                "log": f"An unexpected error occurred: {str(e)}"
            }


# Test the tool if this script is run directly
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create an instance of the tool
    tool = MeetingAgendaGeneratorTool()
    
    # Test with the specified meeting date
    meeting_date = "2025-08-07"
    print(f"Testing MeetingAgendaGeneratorTool with meeting date: {meeting_date}")
    
    # Call the tool
    result = tool._run(meeting_info={"meetingDate": meeting_date})
    
    # Print the result
    print("\nResult:")
    print(f"Success: {result['success']}")
    print(f"PDF Path: {result['pdfPath']}")
    print(f"Log (first 500 characters): {result['log'][:500]}...")
    
    # Check if the PDF was created
    if result["success"] and result["pdfPath"] and os.path.exists(result["pdfPath"]):
        print(f"\nPDF file created successfully: {result['pdfPath']}")
    else:
        print("\nFailed to create PDF file.")
