
# run_solver.py
import os
import sys
import time
from typing import Type
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException

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
    Opens UniTime timetable page and exports CSV automatically.
    """
    name: str = "Export_Timetable"
    description: str = "Exports the timetable CSV from UniTime without using the solver."
    args_schema: Type[BaseModel] = RunExportInput

    def _wait_for_download(self, download_dir: str, timeout: int = 30):
        """
        Wait for any .crdownload file to finish.
        """
        seconds = 0
        while seconds < timeout:
            time.sleep(1)
            downloading = any(f.endswith(".crdownload") for f in os.listdir(download_dir))
            if not downloading:
                return True
            seconds += 1
        return False

    def _execute(self) -> str:
        print("--- [Export Bot] Starting Export ---")

        base_url = self.get_tool_config("UNITIME_BASE_URL", "http://localhost:8080/UniTime")
        export_target = self.get_tool_config("SCHEDULE_EXPORT_PATH")

        download_dir = os.path.dirname(export_target)

        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        options.add_experimental_option("prefs", {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True
        })

        driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()),
            options=options
        )

        wait = WebDriverWait(driver, 20)

        try:
            # --- 1. Open the timetable page ---
            timetable_url = f"{base_url}/gwt.jsp?page=timetable"
            print(f"--- [Export Bot] Opening: {timetable_url} ---")
            driver.get(timetable_url)

            # --- 2. Click the Export button ---
            print("--- [Export Bot] Clicking Export button ---")
            export_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Export']"))
            )
            export_button.click()

            # --- 3. Wait for download ---
            print("--- [Export Bot] Waiting for file download... ---")

            if not self._wait_for_download(download_dir):
                return "Error: Download timed out."

            # Identify the most recent CSV file
            files = [os.path.join(download_dir, f) for f in os.listdir(download_dir) if f.endswith(".csv")]
            if not files:
                return "Error: No CSV downloaded."

            latest_file = max(files, key=os.path.getctime)

            # Rename/move to target path
            if os.path.exists(export_target):
                os.remove(export_target)

            os.rename(latest_file, export_target)

            print(f"--- [Export Bot] CSV saved to: {export_target} ---")
            return f"Success: Timetable exported to {export_target}"

        except TimeoutException:
            return "Error: UI element not found. UniTime UI may be different."
        except Exception as e:
            return f"Error: {str(e)}"
        finally:
            driver.quit()
            print("--- [Export Bot] WebDriver closed. ---")
