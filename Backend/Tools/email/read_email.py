# # # My_Agentic_Ai\Backend\Tools\email\read_email.py

# # import email
# # import json
# # from typing import Type, Union, List, Dict, Any # <-- MAKE SURE THESE ARE IMPORTED

# # from pydantic import BaseModel, Field
# # import sys
# # import os
# # PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
# # if PROJECT_ROOT not in sys.path:
# #     sys.path.append(PROJECT_ROOT)

# # from Backend.Helper.imap_email import ImapEmail
# # from Backend.Helper.read_email_helper import ReadEmail
# # # --- CORRECTED IMPORT ---
# # from Backend.Helper.token_counter import UniversalTokenCounter 
# # from Backend.tool_framework.base_tool import BaseTool


# # class ReadEmailInput(BaseModel):
# #     imap_folder: str = Field(..., description="Email folder to read from. default value is \"INBOX\"")
# #     page: int = Field(...,
# #                       description="The index of the page result the function should resturn. Defaults to 0, the first page.")
# #     limit: int = Field(..., description="Number of emails to fetch in one cycle. Defaults to 5.")


# # class ReadEmailTool(BaseTool):
# #     """
# #     Read emails from an IMAP mailbox

# #     Attributes:
# #         name : The name of the tool.
# #         description : The description of the tool.
# #         args_schema : The args schema.
# #     """
# #     name: str = "Read_Email"
# #     args_schema: Type[BaseModel] = ReadEmailInput
# #     description: str = "Read emails from an IMAP mailbox"

# #     def _execute(self, imap_folder: str = "INBOX", page: int = 0, limit: int = 5) -> Union[str, List[Dict[str, Any]]]:
# #         """
# #         Execute the read email tool with robust error handling and token management.
# #         """
# #         # 1. --- SETUP: Get configurations and instantiate helpers ---
# #         email_sender = self.get_tool_config('EMAIL_ADDRESS')
# #         email_password = self.get_tool_config('EMAIL_PASSWORD')
# #         imap_server = self.get_tool_config('EMAIL_IMAP_SERVER')
# #         model_name = self.get_tool_config('LLM_MODEL')

# #         if not email_sender or not email_password or not imap_server:
# #             return "Error: Email credentials (EMAIL_ADDRESS, EMAIL_PASSWORD, or EMAIL_IMAP_SERVER) are not configured."

# #         if not model_name:
# #             print("Warning: LLM_MODEL not set in config, defaulting to 'gpt-4'.")
# #             model_name = "gpt-4"

# #         token_counter = UniversalTokenCounter()
# #         imap_helper = ImapEmail()
# #         read_email_helper = ReadEmail()

# #         # 2. --- RESOURCE MANAGEMENT: Open connection in a try...finally block ---
# #         try:
# #             conn = imap_helper.imap_open(imap_folder, email_sender, email_password, imap_server)
# #         except Exception as e:
# #             return f"Error connecting to IMAP server: {e}"

# #         try:
# #             # 3. --- CORE LOGIC: Fetch and process emails ---
# #             status, messages_data = conn.select(imap_folder)
# #             if status != 'OK':
# #                 return f"Error selecting IMAP folder '{imap_folder}'."

# #             num_of_messages = int(messages_data[0])
# #             messages = []

# #             for i in range(num_of_messages, num_of_messages - limit, -1):
# #                 if i <= 0:
# #                     break
                
# #                 res, msg_data = conn.fetch(str(i), "(RFC822)")
# #                 email_msg = {}
                
# #                 self._process_message(email_msg, msg_data, read_email_helper)
                
# #                 if email_msg:
# #                     messages.append(email_msg)

# #                 current_tokens = token_counter.count_text_tokens(
# #                     text=json.dumps(messages),
# #                     model_name=model_name
# #                 )
                
# #                 if current_tokens > self.max_token_limit:
# #                     print(f"Token limit reached ({current_tokens}/{self.max_token_limit}). Stopping email fetch.")
# #                     break
            
# #             if not messages:
# #                 return f"There are no emails in your folder '{imap_folder}'."
            
# #             return messages

# #         except Exception as e:
# #             return f"An error occurred while fetching emails: {e}"
        
# #         finally:
# #             # 4. --- CLEANUP: Ensure connection is always closed ---
# #             if 'conn' in locals() and conn.state == 'SELECTED':
# #                 conn.logout()
# #                 print("IMAP connection closed.")
                
# #     def _process_message(self, email_msg: Dict, response_part: List, read_email_helper: ReadEmail):
# #         """
# #         Processes a single email response part.
# #         This method is updated to accept a ReadEmail helper instance for efficiency.
# #         """
# #         for response in response_part:
# #             if isinstance(response, tuple):
# #                 msg = email.message_from_bytes(response[1])
# #                 email_msg["From"], email_msg["To"], email_msg["Date"], email_msg[
# #                     "Subject"] = read_email_helper.obtain_header(msg)
# #                 if msg.is_multipart():
# #                     for part in msg.walk():
# #                         content_type = part.get_content_type()
# #                         content_disposition = str(part.get("Content-Disposition"))
# #                         try:
# #                             body = part.get_payload(decode=True).decode()
# #                         except:
# #                             pass
# #                         if content_type == "text/plain" and "attachment" not in content_disposition:
# #                             # --- CORRECTED HELPER CALL ---
# #                             email_msg["Message Body"] = read_email_helper.clean_email_body(body)
# #                         elif "attachment" in content_disposition:
# #                             # --- CORRECTED HELPER CALL ---
# #                             read_email_helper.download_attachment(part, email_msg["Subject"])
# #                 else:
# #                     content_type = msg.get_content_type()
# #                     body = msg.get_payload(decode=True).decode()
# #                     if content_type == "text/plain":
# #                         # --- CORRECTED HELPER CALL ---
# #                         email_msg["Message Body"] = read_email_helper.clean_email_body(body)


















































# # My_Agentic_Ai\Backend\Tools\email\read_email.py

# import email
# import json
# import re # <--- 1. ADDED IMPORT
# from typing import Type, Union, List, Dict, Any 

# from pydantic import BaseModel, Field
# import sys
# import os
# PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
# if PROJECT_ROOT not in sys.path:
#     sys.path.append(PROJECT_ROOT)

# from Backend.Helper.imap_email import ImapEmail
# from Backend.Helper.read_email_helper import ReadEmail
# from Backend.Helper.token_counter import UniversalTokenCounter 
# from Backend.tool_framework.base_tool import BaseTool


# class ReadEmailInput(BaseModel):
#     imap_folder: str = Field(..., description="Email folder to read from. default value is \"INBOX\"")
#     page: int = Field(...,
#                       description="The index of the page result the function should resturn. Defaults to 0, the first page.")
#     limit: int = Field(..., description="Number of emails to fetch in one cycle. Defaults to 5.")


# class ReadEmailTool(BaseTool):
#     """
#     Read emails from an IMAP mailbox
#     """
#     name: str = "Read_Email"
#     args_schema: Type[BaseModel] = ReadEmailInput
#     description: str = "Read emails from an IMAP mailbox"

#     # <--- 2. ADDED NEW HELPER FUNCTION ---
#     def _clean_reply_chain(self, body: str) -> str:
#         """
#         Strips away quoted reply chains from an email body.
#         """
#         # Pattern to find common reply headers
#         # e.g., "On Sun, 26 Oct 2025 at 15:09, Raihan wrote:"
#         reply_pattern = re.compile(r"(\nOn .* wrote:|\n>.*)", re.DOTALL)
        
#         match = reply_pattern.search(body)
        
#         if match:
#             # If a match is found, return only the text *before* it
#             return body[:match.start()].strip()
#         else:
#             # No reply chain found, return the original body
#             return body.strip()

#     def _execute(self, imap_folder: str = "INBOX", page: int = 0, limit: int = 5) -> Union[str, List[Dict[str, Any]]]:
#         """
#         Execute the read email tool.
#         """
#         # ... (This whole _execute function is correct, no changes needed) ...
#         email_sender = self.get_tool_config('EMAIL_ADDRESS')
#         email_password = self.get_tool_config('EMAIL_PASSWORD')
#         imap_server = self.get_tool_config('EMAIL_IMAP_SERVER')
#         model_name = self.get_tool_config('LLM_MODEL')

#         if not email_sender or not email_password or not imap_server:
#             return "Error: Email credentials (EMAIL_ADDRESS, EMAIL_PASSWORD, or EMAIL_IMAP_SERVER) are not configured."

#         if not model_name:
#             print("Warning: LLM_MODEL not set in config, defaulting to 'gpt-4'.")
#             model_name = "gpt-4"

#         token_counter = UniversalTokenCounter()
#         imap_helper = ImapEmail()
#         read_email_helper = ReadEmail()

#         try:
#             conn = imap_helper.imap_open(imap_folder, email_sender, email_password, imap_server)
#         except Exception as e:
#             return f"Error connecting to IMAP server: {e}"

#         try:
#             status, messages_data = conn.select(imap_folder)
#             if status != 'OK':
#                 return f"Error selecting IMAP folder '{imap_folder}'."

#             num_of_messages = int(messages_data[0])
#             messages = []

#             for i in range(num_of_messages, num_of_messages - limit, -1):
#                 if i <= 0:
#                     break
                
#                 res, msg_data = conn.fetch(str(i), "(RFC822)")
#                 email_msg = {}
                
#                 self._process_message(email_msg, msg_data, read_email_helper)
                
#                 if email_msg:
#                     messages.append(email_msg)

#                 current_tokens = token_counter.count_text_tokens(
#                     text=json.dumps(messages),
#                     model_name=model_name
#                 )
                
#                 if current_tokens > self.max_token_limit:
#                     print(f"Token limit reached ({current_tokens}/{self.max_token_limit}). Stopping email fetch.")
#                     break
            
#             if not messages:
#                 return f"There are no emails in your folder '{imap_folder}'."
            
#             return messages

#         except Exception as e:
#             return f"An error occurred while fetching emails: {e}"
        
#         finally:
#             if 'conn' in locals() and conn.state == 'SELECTED':
#                 conn.logout()
#                 print("IMAP connection closed.")
                
#     def _process_message(self, email_msg: Dict, response_part: List, read_email_helper: ReadEmail):
#         """
#         Processes a single email response part.
#         """
#         for response in response_part:
#             if isinstance(response, tuple):
#                 msg = email.message_from_bytes(response[1])
#                 email_msg["From"], email_msg["To"], email_msg["Date"], email_msg[
#                     "Subject"] = read_email_helper.obtain_header(msg)
#                 if msg.is_multipart():
#                     for part in msg.walk():
#                         content_type = part.get_content_type()
#                         content_disposition = str(part.get("Content-Disposition"))
#                         try:
#                             body = part.get_payload(decode=True).decode()
#                         except:
#                             pass
#                         if content_type == "text/plain" and "attachment" not in content_disposition:
#                             # <--- 3. THIS IS THE CHANGED LINE ---
#                             dirty_body = read_email_helper.clean_email_body(body)
#                             email_msg["Message Body"] = self._clean_reply_chain(dirty_body)
#                         elif "attachment" in content_disposition:
#                             read_email_helper.download_attachment(part, email_msg["Subject"])
#                 else:
#                     content_type = msg.get_content_type()
#                     body = msg.get_payload(decode=True).decode()
#                     if content_type == "text/plain":
#                         # <--- 3. THIS IS THE OTHER CHANGED LINE ---
#                         dirty_body = read_email_helper.clean_email_body(body)
#                         email_msg["Message Body"] = self._clean_reply_chain(dirty_body)







import email
import json
import re # <--- 1. ADDED IMPORT
from typing import Type, Union, List, Dict, Any 

from pydantic import BaseModel, Field
import sys
import os
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from Backend.Helper.imap_email import ImapEmail
from Backend.Helper.read_email_helper import ReadEmail
from Backend.Helper.token_counter import UniversalTokenCounter 
from Backend.tool_framework.base_tool import BaseTool


class ReadEmailInput(BaseModel):
    imap_folder: str = Field(..., description="Email folder to read from. default value is \"INBOX\"")
    page: int = Field(...,
                      description="The index of the page result the function should resturn. Defaults to 0, the first page.")
    limit: int = Field(..., description="Number of emails to fetch in one cycle. Defaults to 5.")


class ReadEmailTool(BaseTool):
    """
    Read emails from an IMAP mailbox
    """
    name: str = "Read_Email"
    args_schema: Type[BaseModel] = ReadEmailInput
    description: str = "Read emails from an IMAP mailbox"

    # <--- 2. ADDED NEW HELPER FUNCTION ---
    def _clean_reply_chain(self, body: str) -> str:
        """
        Strips away quoted reply chains from an email body.
        """
        # Pattern to find common reply headers
        # e.g., "On Sun, 26 Oct 2025 at 15:09, Raihan wrote:"
        reply_pattern = re.compile(r"(\nOn .* wrote:|\n>.*)", re.DOTALL)
        
        match = reply_pattern.search(body)
        
        if match:
            # If a match is found, return only the text *before* it
            return body[:match.start()].strip()
        else:
            # No reply chain found, return the original body
            return body.strip()

    def _execute(self, imap_folder: str = "INBOX", page: int = 0, limit: int = 5) -> Union[str, List[Dict[str, Any]]]:
        """
        Execute the read email tool.
        """
        # ... (This whole _execute function is correct, no changes needed) ...
        email_sender = self.get_tool_config('EMAIL_ADDRESS')
        email_password = self.get_tool_config('EMAIL_PASSWORD')
        imap_server = self.get_tool_config('EMAIL_IMAP_SERVER')
        model_name = self.get_tool_config('LLM_MODEL')

        if not email_sender or not email_password or not imap_server:
            return "Error: Email credentials (EMAIL_ADDRESS, EMAIL_PASSWORD, or EMAIL_IMAP_SERVER) are not configured."

        if not model_name:
            print("Warning: LLM_MODEL not set in config, defaulting to 'gpt-4'.")
            model_name = "gpt-4"

        token_counter = UniversalTokenCounter()
        imap_helper = ImapEmail()
        read_email_helper = ReadEmail()

        try:
            conn = imap_helper.imap_open(imap_folder, email_sender, email_password, imap_server)
        except Exception as e:
            return f"Error connecting to IMAP server: {e}"

        try:
            status, messages_data = conn.select(imap_folder)
            if status != 'OK':
                return f"Error selecting IMAP folder '{imap_folder}'."

            num_of_messages = int(messages_data[0])
            messages = []

            for i in range(num_of_messages, num_of_messages - limit, -1):
                if i <= 0:
                    break
                
                res, msg_data = conn.fetch(str(i), "(RFC822)")
                email_msg = {}
                
                self._process_message(email_msg, msg_data, read_email_helper)
                
                if email_msg:
                    messages.append(email_msg)

                current_tokens = token_counter.count_text_tokens(
                    text=json.dumps(messages),
                    model_name=model_name
                )
                
                if current_tokens > self.max_token_limit:
                    print(f"Token limit reached ({current_tokens}/{self.max_token_limit}). Stopping email fetch.")
                    break
            
            if not messages:
                return f"There are no emails in your folder '{imap_folder}'."
            
            return messages

        except Exception as e:
            return f"An error occurred while fetching emails: {e}"
        
        finally:
            if 'conn' in locals() and conn.state == 'SELECTED':
                conn.logout()
                print("IMAP connection closed.")
                
    def _process_message(self, email_msg: Dict, response_part: List, read_email_helper: ReadEmail):
        """
        Processes a single email response part.
        """
        for response in response_part:
            if isinstance(response, tuple):
                msg = email.message_from_bytes(response[1])
                email_msg["From"], email_msg["To"], email_msg["Date"], email_msg[
                    "Subject"] = read_email_helper.obtain_header(msg)
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition"))
                        try:
                            body = part.get_payload(decode=True).decode()
                        except:
                            pass
                        if content_type == "text/plain" and "attachment" not in content_disposition:
                            # <--- 3. THIS IS THE CHANGED LINE ---
                            dirty_body = read_email_helper.clean_email_body(body)
                            email_msg["Message Body"] = self._clean_reply_chain(dirty_body)
                        elif "attachment" in content_disposition:
                            read_email_helper.download_attachment(part, email_msg["Subject"])
                else:
                    content_type = msg.get_content_type()
                    body = msg.get_payload(decode=True).decode()
                    if content_type == "text/plain":
                        # <--- 3. THIS IS THE OTHER CHANGED LINE ---
                        dirty_body = read_email_helper.clean_email_body(body)
                        email_msg["Message Body"] = self._clean_reply_chain(dirty_body)