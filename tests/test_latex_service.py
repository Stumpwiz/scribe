from scribe.tools.latex_service import LaTeXService
from datetime import datetime

# Prepare dummy meeting context
meeting_data = {
    "meetingType": "regular",
    "meetingDate": "2025-08-07",
    "meetingBody": "Residents Council",
    "location": "McAuley Conference Room",
    "submissionDeadline": "2025-08-02",
    "thisVenue": "McAuley Conference Room",         # for LaTeX template
    "thisMeetingDate": "August 7, 2025",            # formatted for LaTeX
    "thisMeetingBody": "Residents Council",         # etc.
    "thisMeetingType": "Regular",
}

# Define paths
template_path = "assets/templates/agenda_regular.tex.j2"
output_file = "src/scribe/output/agendas/test_agenda.tex"

# Instantiate and run
latex_tool = LaTeXService()
result = latex_tool._generate_document(
    template=template_path,
    content=None,  # unused for now
    variables=meeting_data,
    output_file=output_file
)

print(result)
