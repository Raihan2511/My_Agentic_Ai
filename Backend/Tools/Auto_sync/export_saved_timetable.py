# /home/sysadm/Music/My_Agentic_Ai/Backend/Tools/Auto_sync/export_saved_timetable.py
import os
import sys
import requests
from typing import Type
from pydantic import BaseModel

# --- BaseTool import ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from Backend.tool_framework.base_tool import BaseTool

class RunExportInput(BaseModel):
    pass

class ExportTimetableTool(BaseTool):
    """
    Exports the timetable CSV directly using UniTime export API.
    """
    name: str = "Export_Timetable"
    description: str = "Exports the timetable CSV from UniTime without using the solver."
    args_schema: Type[BaseModel] = RunExportInput

    def _execute(self) -> str:
        print("--- [Export Bot] Starting Export ---")

        # ----------------------------------------
        # 1. DYNAMIC URL CONFIGURATION
        # ----------------------------------------
        # We prefer the new explicit EXPORT_BASE_URL from .env
        # If not set, we default to localhost for safety.
        base_url = self.get_tool_config("EXPORT_BASE_URL")
        
        if not base_url:
            print("Warning: EXPORT_BASE_URL not found, using default localhost.")
            base_url = "http://localhost:8080/UniTime"
        
        # Strip trailing slash if present to avoid double slashes
        if base_url.endswith("/"):
            base_url = base_url[:-1]

        # The specific export query hash
        # NOTE: If you got a 400 error previously, this token might be expired.
        # Ensure this string matches a fresh "Copy Link Address" from your browser.
        export_query = "q=b9kAn3dLYLA0JdKiMThY0R8V0Kcl9J2NgSA9Rv7ZwT6Z-2sPBFMEsUxU9-dMhkuHExJv2kYc5iTWNGd4Q6cuRzyW9q09RAeQqGhgOLVSD2M"
        
        # Construct the full URL dynamically
        # Expected: http://100.73.202.1:8080/UniTime/export?q=...
        export_url = f"{base_url}/export?{export_query}"
        
        print(f"--- [Export Bot] Target URL: {export_url} ---")

        # ----------------------------------------
        # 2. PATH ALIGNMENT (CRITICAL)
        # ----------------------------------------
        # We FORCE the path to match the RAG system's hardcoded expectation
        export_target_absolute = os.path.join(PROJECT_ROOT, "data/schedule_export.csv")
        
        # Ensure data directory exists
        export_dir = os.path.dirname(export_target_absolute)
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)

        # ----------------------------------------
        # 3. EXECUTE EXPORT
        # ----------------------------------------
        try:
            print("--- [Export Bot] Sending Request... ---")
            response = requests.get(export_url, timeout=30)

            if response.status_code != 200:
                return f"Error: UniTime returned status {response.status_code}. The 'q' token might be expired or the URL is wrong."

            if not response.content:
                return "Error: Received empty response from UniTime."

            # Remove existing file to ensure clean write
            if os.path.exists(export_target_absolute):
                os.remove(export_target_absolute)

            # Write the CSV
            with open(export_target_absolute, "wb") as f:
                f.write(response.content)

            print(f"--- [Export Bot] CSV successfully saved to: {export_target_absolute} ---")
            return f"Success: Timetable exported to {export_target_absolute}"

        except Exception as e:
            return f"Error during export: {str(e)}"