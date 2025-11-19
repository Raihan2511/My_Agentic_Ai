# # Backend/Tools/university/import_batch_file.py

# import os
# import sys
# import requests
# from requests.auth import HTTPBasicAuth
# from pydantic import BaseModel, Field
# from typing import Type, ClassVar # <-- 1. IMPORTED ClassVar
# import datetime 

# # --- Project Path Setup ---
# PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
# if PROJECT_ROOT not in sys.path:
#     sys.path.append(PROJECT_ROOT)

# from Backend.tool_framework.base_tool import BaseTool

# # --- Pydantic Input Schema ---
# class ImportBatchInput(BaseModel):
#     pass 

# # --- Tool Class Definition ---
# class ImportBatchFileTool(BaseTool):
#     """
#     Imports the *entire* 'unitime_batch.xml' file to UniTime.
#     On success, this will clear the batch file for the next run.
#     """
#     name: str = "Import_Batch_File_to_Unitime"
#     description: str = "Imports the entire batch XML file into the UniTime system. This will reset the queue on success."
#     args_schema: Type[BaseModel] = ImportBatchInput
    
#     # Define the name of your permanent batch file
#     BATCH_FILE_NAME: ClassVar[str] = "unitime_batch.xml" # <-- 2. ANNOTATED

#     def _get_batch_file_path(self) -> str:
#         """Helper to get the full path to the batch file."""
#         return os.path.join(PROJECT_ROOT, self.BATCH_FILE_NAME)

#     def _reset_batch_file(self) -> str:
#         """
#         Resets the batch file to a clean, empty template after a
#         successful import.
#         """
#         batch_file_path = self._get_batch_file_path()
#         timestamp = datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Z %Y")
        
#         xml_header = f"""<?xml version="1.0" encoding="UTF-8"?>
# <offerings campus="woebegon" year="2010" term="Fal" dateFormat="yyyy/M/d" timeFormat="HHmm" created="{timestamp}" includeExams="none">"""
        
#         xml_footer = """
# </offerings>"""

#         try:
#             with open(batch_file_path, "w", encoding="utf-8") as f:
#                 f.write(f"{xml_header}\n{xml_footer}")
#             return "Success: Batch file reset."
#         except Exception as e:
#             return f"Warning: Could not reset batch file: {e}"

#     def _execute(self) -> str:
        
#         batch_file_path = self._get_batch_file_path()

#         if not os.path.exists(batch_file_path):
#             return "Error: The batch file 'unitime_batch.xml' does not exist. Nothing to import."

#         with open(batch_file_path, "r", encoding="utf-8") as f:
#             final_xml_data = f.read()

#         api_url = self.get_tool_config("UNITIME_API_URL")
#         username = self.get_tool_config("UNITIME_USERNAME")
#         password = self.get_tool_config("UNITIME_PASSWORD")
        
#         if not api_url or not username or not password:
#             return "Error: Missing UNITIME_API_URL, UNITIME_USERNAME, or UNITIME_PASSWORD in the environment configuration."

#         headers = {
#             "Content-Type": "application/xml;charset=UTF-8"
#         }
        
#         try:
#             print(f"--- ATTEMPTING TO POST BATCH XML TO {api_url} using Basic Auth ---")
            
#             response = requests.post(
#                 api_url, 
#                 data=final_xml_data.encode('utf-8'),
#                 headers=headers,
#                 auth=HTTPBasicAuth(username, password)
#             )
            
#             response.raise_for_status() 

#             print("--- Batch import successful. Resetting batch file. ---")
#             reset_status = self._reset_batch_file()
#             print(f"--- {reset_status} ---")

#             if "text/html" in response.headers.get("Content-Type", ""):
#                  return f"Successfully imported batch data to UniTime. Server returned an HTML success page (Status: {response.status_code}). Batch file has been reset."
            
#             return f"Successfully imported batch data to UniTime. Server response: {response.text}. Batch file has been reset."
        
#         except requests.exceptions.HTTPError as http_err:
#             return f"Error: HTTP error occurred during UniTime batch import. THE BATCH FILE WAS NOT RESET. {http_err} - Response: {http_err.response.text}"
#         except requests.exceptions.RequestException as req_err:
#             return f"Error: A critical request error occurred. THE BATCH FILE WAS NOT RESET. {req_err}"

















import os
import sys
import requests
from requests.auth import HTTPBasicAuth 
from pydantic import BaseModel, Field
from typing import Type

# --- Project Path Setup ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from Backend.tool_framework.base_tool import BaseTool

# --- Pydantic Input Schema ---
class ImportBatchFileInput(BaseModel):
    # KEY CHANGE: We ask the AI to tell us WHICH file to import
    filename: str = Field(..., description="The name of the XML file to import. Use 'unitime_batch.xml' for new courses (inserts) or 'unitime_update.xml' for updates.")

# --- Tool Class Definition ---
class ImportBatchFileTool(BaseTool):
    """
    A tool that reads XML data from a specified local file and sends it to the 
    UniTime dataexchange API endpoint for processing.
    """
    name: str = "Import_File_to_Unitime" 
    description: str = "Imports a specific local XML file into UniTime. You must specify if you are importing the batch file or the update file."
    args_schema: Type[BaseModel] = ImportBatchFileInput
    
    def _execute(self, filename: str) -> str:
        
        # --- Step 1: Read XML Data from the Requested File ---
        file_path = os.path.join(PROJECT_ROOT, filename)
        
        if not os.path.exists(file_path):
            return f"Error: The file '{filename}' was not found. Please generate the file first before importing."
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                unitime_xml_data = f.read()
        except Exception as e:
            return f"Error: Failed to read content from file '{filename}': {e}"
        
        # --- Step 2: Load Credentials ---
        api_url = self.get_tool_config("UNITIME_API_URL")
        username = self.get_tool_config("UNITIME_USERNAME") 
        password = self.get_tool_config("UNITIME_PASSWORD") 
        
        if not api_url or not username or not password:
            return "Error: Missing UNITIME credentials in configuration."

        headers = {
            "Content-Type": "application/xml;charset=UTF-8"
        }
        
        # --- Step 3: API Request ---
        try:
            print(f"--- ATTEMPTING TO POST XML from '{filename}' TO UniTime ---")
            
            response = requests.post(
                api_url, 
                data=unitime_xml_data.encode('utf-8'), 
                headers=headers,
                auth=HTTPBasicAuth(username, password)
            )
            
            response.raise_for_status() 
            
            if "text/html" in response.headers.get("Content-Type", ""):
                 return f"Successfully imported {filename}. Server returned HTML status: {response.status_code}."
            
            return f"Successfully imported {filename}. Server response: {response.text}"
        
        except requests.exceptions.HTTPError as http_err:
            return f"Error: HTTP error during import of {filename}: {http_err}"
        except requests.exceptions.RequestException as req_err:
            return f"Error: Critical request error for {filename}: {req_err}"