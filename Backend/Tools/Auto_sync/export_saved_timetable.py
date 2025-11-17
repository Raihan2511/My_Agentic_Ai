import os
import sys
import time
import requests
from typing import Type
from pydantic import BaseModel

# --- BaseTool import ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from Backend.tool_framework.base_tool import BaseTool

# --- Input schema ---
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

        # --- 1. BASE URL CONFIG ---
        base_url_config = self.get_tool_config("UNITIME_BASE_URL")
        # Fallback for safety
        base_url = base_url_config if base_url_config else "http://localhost:8080/UniTime"

        # --- 2. EXPORT PATH CONFIG ---
        export_target_relative = self.get_tool_config("SCHEDULE_EXPORT_PATH")
        if not export_target_relative:
            return "Error: SCHEDULE_EXPORT_PATH is not configured."

        export_target_absolute = os.path.abspath(export_target_relative)
        export_dir = os.path.dirname(export_target_absolute)
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)

        # --- 3. STATIC DIRECT EXPORT URL ---
        export_url = (
            "http://100.73.202.1:8080/UniTime/export"
            "?q=b9kAn3dLYLA0JdKiMThY0R8V0Kcl9J2NgSA9Rv7ZwT6Z-2sPBFMEsUxU9-dMhkuHExJv2kYc5iTWNGd4Q6cuRzyW9q09RAeQqGhgOLVSD2M"
        )

        print(f"--- [Export Bot] Calling Direct Export URL ---\n{export_url}")

        try:
            response = requests.get(export_url, timeout=20)

            if response.status_code != 200:
                return f"Error: Export URL returned status {response.status_code}"

            # Remove existing file if exists
            if os.path.exists(export_target_absolute):
                os.remove(export_target_absolute)

            # Write the CSV
            with open(export_target_absolute, "wb") as f:
                f.write(response.content)

            print(f"--- [Export Bot] CSV saved to: {export_target_absolute} ---")
            return f"Success: Timetable exported to {export_target_absolute}"

        except Exception as e:
            return f"Error: {str(e)}"
