from crewai import Crew, Task
from scribe.config.loader import load_agent_from_yaml, load_task_from_yaml
from scribe.tools.meeting_agenda_generator_tool import MeetingAgendaGeneratorTool

# Load the agent from YAML
reminder_agent = load_agent_from_yaml("ReminderAgent")

# Define task context
context = {
    "meeting_type": "regular",
    "meeting_date": "2025-08-07",
    "meeting_time": "10:00",
    "location": "McAuley Conference Room"
}

# Load the reminder task from YAML
reminder_task = load_task_from_yaml(
    "send_meeting_notification",
    context={
        "meeting_date": "2025-08-12",  # You can dynamically set this if desired
        "location": "Conference Room A",
        "email_recipients": ["user2@example.com"],
        "include_agenda_template": True,
        "agenda_type": "council"  # Optional, but helps select the right template
    }
)

# Create the agenda generation task
agenda_context = {
    "meeting_date": "2025-08-12",
    "location": "Conference Room A",
    "agenda_type": "council",
    "log": True
}

# Create a tool instance
meeting_agenda_tool = MeetingAgendaGeneratorTool()

# Create the agenda task with proper context
agenda_task = Task(
    description=f"Generate a meeting agenda for the council meeting on {agenda_context['meeting_date']} in {agenda_context['location']}. Use the MeetingAgendaGeneratorTool with meetingDate={agenda_context['meeting_date']}.",
    expected_output="A properly formatted meeting agenda in PDF format stored in output/agendas",
    agent=reminder_agent,  # Use the same agent for both tasks
    tools=[meeting_agenda_tool]
)

# Create and run the crew with task dependency
crew = Crew(
    agents=[reminder_agent],
    tasks=[agenda_task, reminder_task],  # Add both tasks in order: agenda first, then reminder
    verbose=True
)

# Define a callback function to extract the TEX file path from agenda task and pass it to reminder task
def process_agenda_result(task_output):
    if task_output and hasattr(task_output, 'raw'):
        # Print the raw output for debugging
        print("\n\nDEBUG - Agenda Task Raw Output:")
        print(task_output.raw)
        print("\n")
        
        # Try to extract TEX file path from the raw output
        import re
        import os
        import glob
        from pathlib import Path
        
        # First, check if any .tex files were created in the output/agendas directory
        agendas_dir = Path(__file__).parent.parent / "src" / "scribe" / "output" / "agendas"
        tex_files = list(agendas_dir.glob("*.tex"))
        
        if tex_files:
            # Use the most recently created .tex file
            latest_tex_file = max(tex_files, key=os.path.getmtime)
            print(f"Found TEX file in agendas directory: {latest_tex_file}")
            # Update the reminder task with the TEX file path
            reminder_task.context = {"attachment_path": str(latest_tex_file)}
            return
            
        # If no .tex files found, try to extract path from the output
        tex_match = re.search(r'texPath["']?\s*:\s*["']?(.*?\.tex)["']?', task_output.raw)
        if tex_match:
            tex_path = tex_match.group(1)
            print(f"Found TEX path with regex: {tex_path}")
            # Update the reminder task with the TEX path
            reminder_task.context = {"attachment_path": tex_path}
            return
            
        print("Could not find TEX file path in agenda task output")

# Set the callback for the agenda task
agenda_task.callback = process_agenda_result

if __name__ == "__main__":
    result = crew.kickoff()
    print(result)
