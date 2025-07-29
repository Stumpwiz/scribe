import logging
from scribe.tools.meeting_calendar_tool import MeetingCalendarTool
from scribe.tools.latex_agenda_tool import LaTeXAgendaTool
from scribe.tools.latex_compiler_tool import LaTeXCompilerTool
from scribe.tools.email_writer_tool import EmailWriterTool
from scribe.tools.email_service import EmailService
from scribe.tools.recipient_loader_tool import RecipientLoaderTool

logging.basicConfig(level=logging.DEBUG)

def send_meeting_reminder(meeting_date: str):
    logging.info(f"Sending reminder for meeting date: {meeting_date}")

    # Step 1: Gather meeting metadata
    calendar_tool = MeetingCalendarTool()
    meeting_info = calendar_tool.run(meeting_date)

    if not isinstance(meeting_info, dict):
        logging.error(f"MeetingCalendarTool returned non-dict: {repr(meeting_info)}")
        return

    logging.debug(f"[AFTER calendar_tool] Meeting info: {repr(meeting_info)}")

    if not meeting_info.get("meetingType"):
        logging.error("Failed to retrieve meeting context.")
        return

    # Step 2: Generate LaTeX agenda
    latex_tool = LaTeXAgendaTool()
    tex_path = latex_tool.run(meeting_info)
    if not tex_path:
        logging.error("Failed to render LaTeX agenda.")
        return

    # Step 3: Compile PDF
    compiler = LaTeXCompilerTool()
    pdf_result = compiler.run(tex_path)
    if not pdf_result.get("success"):
        logging.error("Failed to compile LaTeX agenda.")
        logging.error(f"Compilation log:\n{pdf_result.get('log')}")
        return

    pdf_path = pdf_result.get("pdfPath")

    # Step 4: Write email content
    email_writer = EmailWriterTool()
    email_text = email_writer.run(meeting_info).get("emailContent")

    # Step 5: Load recipients
    recipients_tool = RecipientLoaderTool()
    email_list = recipients_tool.run(meeting_info.get("meetingType")).get("emails")

    # Step 6: Send email with attachment
    email_service = EmailService()
    for recipient in email_list:
        response = email_service.send_reminder(
            recipient_email=recipient,
            subject=email_text.splitlines()[0].replace("Subject: ", ""),
            message="\n".join(email_text.splitlines()[1:]),
            attachment_path=pdf_path
        )
        if response.get("success"):
            logging.info(f"Email sent to {recipient}")
        else:
            logging.warning(f"Failed to send email to {recipient}: {response.get('error')}")

if __name__ == "__main__":
    send_meeting_reminder("2025-08-07")
