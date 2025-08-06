"""
Meeting agenda generator tool for the Scribe project.

This module provides the MeetingAgendaGeneratorTool class for generating meeting agendas
by orchestrating multiple tools: MeetingCalendarTool, LaTeXAgendaTool, and LaTeXCompilerTool.
"""

import os
import logging
from typing import Dict, Any, Optional
from crewai.tools import BaseTool

from scribe.tools.meeting_calendar_tool import MeetingCalendarTool
from scribe.tools.latex_agenda_tool import LaTeXAgendaTool
from scribe.tools.latex_compiler_tool import LaTeXCompilerTool


class MeetingAgendaGeneratorTool(BaseTool):
    """
    Tool for generating meeting agendas by orchestrating multiple tools.
    
    This tool accepts a meeting date, uses MeetingCalendarTool to enrich the context,
    LaTeXAgendaTool to render a .tex agenda file, and LaTeXCompilerTool to compile
    the .tex to .pdf.
    """
    
    name: str = "MeetingAgendaGeneratorTool"
    description: str = "Tool for generating meeting agendas as PDF files"
    
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
            # Validate required fields - accept both "meetingDate" and "date" keys
            meeting_date = meeting_info.get("meetingDate") or meeting_info.get("date")
            if not meeting_date:
                return {
                    "success": False,
                    "pdfPath": None,
                    "log": "Error: Required field 'meetingDate' or 'date' is missing from meeting_info"
                }
            logging.info(f"Generating agenda for meeting date: {meeting_date}")
            
            # Step 1: Use MeetingCalendarTool to enrich the context
            calendar_tool = MeetingCalendarTool()
            calendar_result = calendar_tool._run(meeting_date=meeting_date)
            
            # Check for errors from MeetingCalendarTool
            if "error" in calendar_result and calendar_result["error"]:
                return {
                    "success": False,
                    "pdfPath": None,
                    "log": f"Error from MeetingCalendarTool: {calendar_result['message']}"
                }
            
            # Merge the calendar result with the input meeting_info
            enriched_info = {**calendar_result, **meeting_info}
            
            # Add additional required fields for the template if not already present
            if "meetingTime" not in enriched_info:
                enriched_info["meetingTime"] = "7:30"  # Default meeting time
            
            # Calculate next meeting date (for example, add 1 month)
            # In a real implementation, this would be more sophisticated
            if "nextMeetingDate" not in enriched_info:
                # Simple example: use a fixed next meeting date
                enriched_info["nextMeetingDate"] = "2025-09-04"
            
            # Set venue information
            enriched_info["thisVenue"] = enriched_info["location"]
            enriched_info["mextVenue"] = "Performing Arts Center (PAC)"  # Default next venue
            
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