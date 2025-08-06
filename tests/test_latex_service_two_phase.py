from scribe.tools.latex_service import LaTeXService
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Prepare dummy meeting context
meeting_data = {
    "meetingType": "regular",
    "meetingDate": "2025-08-07",
    "meetingBody": "Residents Council",
    "location": "McAuley Conference Room",
    "thisVenue": "McAuley Conference Room",         # for LaTeX template
    "thisMeetingDate": "August 7, 2025",            # formatted for LaTeX
    "thisMeetingBody": "Residents Council",         # etc.
    "thisMeetingType": "Regular",
}

# Define paths
template_path = "assets/templates/agenda_regular.tex.j2"
output_file = "src/scribe/output/agendas/test_two_phase_agenda.tex"

# Ensure output directory exists
os.makedirs(os.path.dirname(output_file), exist_ok=True)

# Instantiate LaTeXService
latex_tool = LaTeXService()

# Test the two-phase workflow
def test_two_phase_workflow():
    logger.info("Testing two-phase LaTeX workflow")
    
    # Phase 1: Generate the LaTeX document
    logger.info("Phase 1: Generating LaTeX document...")
    tex_file_path = latex_tool._run(
        action="generate",
        template=template_path,
        content=None,  # unused for now
        variables=meeting_data,
        output_file=output_file
    )
    logger.info(f"Generated LaTeX file: {tex_file_path}")
    
    # Verify the .tex file was created
    if os.path.exists(tex_file_path):
        logger.info(f"LaTeX file exists: {tex_file_path}")
        logger.info(f"File size: {os.path.getsize(tex_file_path)} bytes")
    else:
        logger.error(f"LaTeX file not found: {tex_file_path}")
        return False
    
    # Phase 2: Compile the LaTeX document
    logger.info("Phase 2: Compiling LaTeX document...")
    compile_result = latex_tool._run(
        action="compile",
        output_file=tex_file_path
    )
    logger.info(f"Compilation result: {compile_result}")
    
    # Verify the PDF was created
    pdf_path = os.path.splitext(tex_file_path)[0] + ".pdf"
    if os.path.exists(pdf_path):
        logger.info(f"PDF file exists: {pdf_path}")
        logger.info(f"File size: {os.path.getsize(pdf_path)} bytes")
        return True
    else:
        logger.error(f"PDF file not found: {pdf_path}")
        return False

if __name__ == "__main__":
    success = test_two_phase_workflow()
    if success:
        logger.info("Two-phase workflow test completed successfully!")
    else:
        logger.error("Two-phase workflow test failed!")