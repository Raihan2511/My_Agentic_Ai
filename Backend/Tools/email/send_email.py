# import imaplib
# import smtplib
# import time
# from email.message import EmailMessage
# from typing import Type
# import os
# import sys
# PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
# sys.path.append(PROJECT_ROOT)

# from pydantic import BaseModel, Field
# from Backend.Helper.imap_email import ImapEmail
# from Backend.tool_framework.base_tool import BaseTool


# class SendEmailInput(BaseModel):
#     to: str = Field(..., description="Email Address of the Receiver, default email address is 'example@example.com'")
#     subject: str = Field(..., description="Subject of the Email to be sent")
#     body: str = Field(..., description="Email Body to be sent. Escape special characters in the body. Do not add senders details and end it with Warm Regards without entering any name.")


# class SendEmailTool(BaseTool):
#     """
#     Send an Email tool

#     Attributes:
#         name : The name.
#         description : The description.
#         args_schema : The args schema.
#     """
#     name: str = "Send_Email"
#     args_schema: Type[BaseModel] = SendEmailInput
#     description: str = "Send an Email"
    
#     def _execute(self, to: str, subject: str, body: str) -> str:
#         """
#         Execute the send email tool.

#         Args:
#             to : The email address of the receiver.
#             subject : The subject of the email.
#             body : The body of the email.

#         Returns:
#             success or error message.
#         """
#         email_sender = self.get_tool_config('EMAIL_ADDRESS')
#         email_password = self.get_tool_config('EMAIL_PASSWORD')
#         if email_sender is None or email_sender == "" or email_sender.isspace():
#             return "Error: Email Not Sent. Enter a valid Email Address."
#         if email_password is None or email_password == "" or email_password.isspace():
#             return "Error: Email Not Sent. Enter a valid Email Password."
#         message = EmailMessage()
#         message["Subject"] = subject
#         message["From"] = email_sender
#         message["To"] = to
#         signature = self.get_tool_config('EMAIL_SIGNATURE')
#         if signature:
#             body += f"\n{signature}"
#         message.set_content(body.replace('\\n', '\n'))
#         send_to_draft = self.get_tool_config('EMAIL_DRAFT_MODE') or "FALSE"
#         if send_to_draft.upper() == "TRUE":
#             send_to_draft = True
#         else:
#             send_to_draft = False

#         if send_to_draft:
#             draft_folder = self.get_tool_config('EMAIL_DRAFT_FOLDER') or "Drafts"
#             imap_server = self.get_tool_config('EMAIL_IMAP_SERVER')
#             conn = ImapEmail().imap_open(draft_folder, email_sender, email_password, imap_server)
#             conn.append(
#                 draft_folder,
#                 "",
#                 imaplib.Time2Internaldate(time.time()),
#                 str(message).encode("UTF-8")
#             )
#             return f"Email went to {draft_folder}"
        
#         if message["To"] == "example@example.com":
#             return "Error: Email Not Sent. Enter an Email Address."
        
#         else:
#             smtp_host = self.get_tool_config('EMAIL_SMTP_HOST')
#             smtp_port = self.get_tool_config('EMAIL_SMTP_PORT')
#             with smtplib.SMTP(smtp_host, smtp_port) as smtp:
#                 smtp.ehlo()
#                 smtp.starttls()
#                 smtp.login(email_sender, email_password)
#                 smtp.send_message(message)
#                 smtp.quit()
#             return f"Email was sent to {to}"



# My_Agentic_Ai/Backend/Tools/email/send_email.py

# --- Standard Library Imports ---
import smtplib
import ssl
import time
import imaplib
import os
import sys
from email.message import EmailMessage
from typing import Type

# --- Third-party Imports ---
from pydantic import BaseModel, Field

# --- Project-specific Imports ---
# Add the project root to the Python path to ensure imports work correctly
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from Backend.Helper.imap_email import ImapEmail
from Backend.tool_framework.base_tool import BaseTool


# Pydantic model for defining the tool's input arguments and their types.
# This helps the LLM understand what parameters to provide.
class SendEmailInput(BaseModel):
    to: str = Field(..., description="The email address of the receiver.")
    subject: str = Field(..., description="The subject of the email to be sent.")
    body: str = Field(..., description="The body content of the email to be sent.")


# The main tool class that inherits from your BaseTool.
class SendEmailTool(BaseTool):
    """
    A tool to send an email using a secure SMTP connection.
    It is self-contained and handles its own connection, authentication, and error reporting.
    """
    name: str = "Send_Email"
    args_schema: Type[BaseModel] = SendEmailInput
    description: str = "Sends an email to a specified recipient with a subject and body."

    def _execute(self, to: str, subject: str, body: str) -> str:
        """
        Executes the send email tool with a secure, self-contained connection
        and robust error handling.

        Args:
            to: The email address of the receiver.
            subject: The subject of the email.
            body: The body of the email.

        Returns:
            A string indicating success or providing a detailed error message.
        """
        # 1. --- Get Credentials from Configuration ---
        email_sender = self.get_tool_config('EMAIL_ADDRESS')
        # For Gmail/Google, this must be an "App Password", not your regular password.
        email_password = self.get_tool_config('EMAIL_PASSWORD')

        # 2. --- Validate Credentials ---
        if not all([email_sender, email_password]):
            return "Error: Email credentials (EMAIL_ADDRESS, EMAIL_PASSWORD) are not configured. Please set them."

        # 3. --- Construct the Email Message ---
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = email_sender
        message["To"] = to

        signature = self.get_tool_config('EMAIL_SIGNATURE')
        if signature:
            body += f"\n\n{signature}" # Add newlines for better formatting

        message.set_content(body.replace('\\n', '\n'))

        # 4. --- Handle Optional "Save to Drafts" Logic ---
        # This part uses IMAP to save a copy, not SMTP to send.
        send_to_draft = str(self.get_tool_config('EMAIL_DRAFT_MODE') or "FALSE").upper() == "TRUE"
        if send_to_draft:
            try:
                draft_folder = self.get_tool_config('EMAIL_DRAFT_FOLDER') or "Drafts"
                imap_server = self.get_tool_config('EMAIL_IMAP_SERVER')
                conn = ImapEmail().imap_open(draft_folder, email_sender, email_password, imap_server)
                conn.append(
                    draft_folder,
                    "",
                    imaplib.Time2Internaldate(time.time()),
                    str(message).encode("utf-8")
                )
                conn.logout()
                return f"Email successfully saved to the '{draft_folder}' folder."
            except Exception as e:
                return f"Error: Failed to save email to drafts. Details: {e}"

        # 5. --- Connect, Authenticate, and Send Email via SMTP ---
        # Get SMTP server details from config, providing sensible defaults for Gmail.
        smtp_host = self.get_tool_config('EMAIL_SMTP_HOST') or "smtp.gmail.com"
        smtp_port = int(self.get_tool_config('EMAIL_SMTP_PORT') or 465)

        try:
            # Create a secure SSL context for the connection.
            context = ssl.create_default_context()

            # The 'with' statement ensures the connection is automatically and safely
            # closed, even if errors occur. This is the main fix.
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as smtp_server:
                smtp_server.login(email_sender, email_password)
                smtp_server.send_message(message)

            return f"Email was sent successfully to {to}."

        # Provide specific, helpful error messages for common problems.
        except smtplib.SMTPAuthenticationError:
            return "Error: Email not sent. The username or password is not correct. For Gmail, ensure you are using an 'App Password'."
        except smtplib.SMTPRecipientsRefused:
            return f"Error: Email not sent. The recipient address '{to}' was refused by the server. Please check the address."
        except ConnectionRefusedError:
            return f"Error: Email not sent. The connection was refused by the server {smtp_host}. Check the SMTP host and port."
        except Exception as e:
            # Catch any other potential errors (e.g., network issues)
            return f"Error: An unexpected error occurred while sending the email: {e}"