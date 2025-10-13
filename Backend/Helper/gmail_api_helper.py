# Save this as Helper/gmail_api_helper.py

import os
import base64
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class GmailApiHelper:
    """A helper class to handle all Gmail API interactions using OAuth2."""

    def __init__(self, credentials_path='credentials.json', token_path='token.json'):
        self.creds = self._get_credentials(credentials_path, token_path)
        self.service = build('gmail', 'v1', credentials=self.creds)

    def _get_credentials(self, credentials_path, token_path):
        creds = None
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        return creds

    def read_emails(self, limit=1, labels=['INBOX']):
        """
        Reads emails from the user's mailbox using the Gmail API.
        """
        try:
            results = self.service.users().messages().list(userId='me', labelIds=labels, maxResults=limit).execute()
            messages_info = results.get('messages', [])

            if not messages_info:
                return "No new messages found."

            emails = []
            for msg_info in messages_info:
                msg = self.service.users().messages().get(userId='me', id=msg_info['id']).execute()
                payload = msg.get('payload', {})
                headers = payload.get('headers', [])
                
                email_data = {
                    'Subject': next((h['value'] for h in headers if h['name'] == 'Subject'), ''),
                    'From': next((h['value'] for h in headers if h['name'] == 'From'), ''),
                    'Date': next((h['value'] for h in headers if h['name'] == 'Date'), ''),
                    'Body': '',
                    'Snippet': msg.get('snippet', '')
                }

                if 'parts' in payload:
                    for part in payload['parts']:
                        if part['mimeType'] == 'text/plain':
                            body_data = part['body'].get('data')
                            if body_data:
                                email_data['Body'] = base64.urlsafe_b64decode(body_data.encode('ASCII')).decode('utf-8')
                                break
                elif 'body' in payload:
                     body_data = payload['body'].get('data')
                     if body_data:
                        email_data['Body'] = base64.urlsafe_b64decode(body_data.encode('ASCII')).decode('utf-8')
                
                emails.append(email_data)
            
            return emails

        except Exception as e:
            return f"An error occurred with the Gmail API: {e}"