from scribe.tools.email_service import EmailService

email_tool = EmailService()

result = email_tool._run(
    action="send",
    to=["user4@example.com"],
    subject="Test Email with PDF Attachment",
    body="This is a test email sent via EmailService with an attached agenda.",
    attachments=["src/scribe/output/agendas/agenda_2025-08-12_regular.pdf"]
)


print(result)
