from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from email.mime.text import MIMEText
import base64
import os

# Adjust path to match your actual token.json location
TOKEN_PATH = os.path.join("src", "scribe", "google_auth", "token.json")

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
service = build("gmail", "v1", credentials=creds)

message = MIMEText("This is a test email from the direct API.")
message["to"] = "georgemartinwright@gmail.com"
message["from"] = "georgemartinwright@gmail.com"
message["subject"] = "Test Email via Direct API"

raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
body = {"raw": raw}

sent_message = service.users().messages().send(userId="me", body=body).execute()
print(f"✅ Sent message ID: {sent_message['id']}")
