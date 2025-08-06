import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Import the get_google_credentials function
from src.scribe.google_auth.google_auth_helper import get_google_credentials

def create_message(sender, to, subject, message_text, attachments=None):
    """Create a message for an email.

    Args:
        sender: Email address of the sender.
        to: Email address of the receiver.
        subject: The subject of the email message.
        message_text: The text of the email message.
        attachments: List of file paths to be attached to the email.

    Returns:
        An object containing a base64url encoded email object.
    """
    message = MIMEMultipart()
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject

    # Add the text part
    msg = MIMEText(message_text)
    message.attach(msg)

    # Add attachments if any
    if attachments:
        for attachment_path in attachments:
            if os.path.exists(attachment_path):
                with open(attachment_path, 'rb') as f:
                    part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
                
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
                message.attach(part)

    # Encode the message
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw}

def send_message(service, user_id, message):
    """Send an email message.

    Args:
        service: Authorized Gmail API service instance.
        user_id: User's email address. The special value "me" can be used to indicate the authenticated user.
        message: Message to be sent.

    Returns:
        Sent Message.
    """
    try:
        message = service.users().messages().send(userId=user_id, body=message).execute()
        print(f'Message Id: {message["id"]}')
        return message
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

def main():
    """Shows basic usage of the Gmail API.
    Sends a test email with optional attachment.
    """
    # Get credentials
    creds = get_google_credentials()
    
    # Build the Gmail service
    service = build('gmail', 'v1', credentials=creds)
    
    # Get sender email from environment variable
    sender = os.getenv("EMAIL_FROM")
    if not sender:
        print("EMAIL_FROM environment variable is not set.")
        return
    
    # Create a test message
    to = "test@example.com"  # Replace with a real email for testing
    subject = "Test Email from Gmail API"
    body = "This is a test email sent using the Gmail API."
    
    # Optional: Add a test attachment
    # attachments = ["path/to/test/file.pdf"]
    attachments = []
    
    # Create and send the message
    message = create_message(sender, to, subject, body, attachments)
    send_message(service, "me", message)

if __name__ == '__main__':
    main()