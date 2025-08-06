from scribe.tools.latex_service import LaTeXService
from datetime import datetime
import os

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
output_file = "src/scribe/output/agendas/test_agenda.tex"

# Ensure output directory exists
os.makedirs(os.path.dirname(output_file), exist_ok=True)

# Instantiate LaTeX service
latex_tool = LaTeXService()

# Step 1: Generate the LaTeX document
print("Step 1: Generating LaTeX document...")
generate_result = latex_tool._generate_document(
    template=template_path,
    content=None,  # unused for now
    variables=meeting_data,
    output_file=output_file
)
print(generate_result)

# Step 2: Compile the LaTeX document
print("\nStep 2: Compiling LaTeX document...")
compile_result = latex_tool._compile_document(output_file)
print(compile_result)

# Step 3: Check if PDF was created
pdf_path = os.path.splitext(output_file)[0] + ".pdf"
if os.path.exists(pdf_path):
    print(f"\nSuccess! PDF file created at: {pdf_path}")
    print(f"File size: {os.path.getsize(pdf_path)} bytes")
else:
    print(f"\nError: PDF file not found at: {pdf_path}")