# Save this as Helper/gmail_helper.py

import os
import imaplib
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# This defines what permissions your script is asking for.
SCOPES = ['https://mail.google.com/']

class GmailHelper:
    """A helper class to handle Gmail authentication via OAuth2 and connect via IMAP."""

    def __init__(self, credentials_path='credentials.json', token_path='token.json'):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.creds = self._get_credentials()

    def _get_credentials(self):
        """
        Gets valid user credentials. If not available or expired,
        it triggers the OAuth 2.0 flow.
        """
        creds = None
        # The file token.json stores the user's access and refresh tokens.
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        return creds

    def imap_open(self, imap_folder="INBOX") -> imaplib.IMAP4_SSL:
        """
        Opens an IMAP connection to Gmail using the OAuth2 access token.
        This replaces the old password-based login.
        """
        # We need the user's email address and the fresh access token.
        email_address = self.creds.id_token_info.get('email')
        access_token = self.creds.token

        # This is the special XOAUTH2 authentication string.
        auth_string = f"user={email_address}\1auth=Bearer {access_token}\1\1"
        
        # Connect to the IMAP server
        conn = imaplib.IMAP4_SSL("imap.gmail.com")
        
        # Instead of conn.login(), we use conn.authenticate()
        conn.authenticate('XOAUTH2', lambda x: auth_string.encode())
        
        conn.select(imap_folder)
        return conn