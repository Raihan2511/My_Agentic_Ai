import os
import sys
import time
from typing import Type, ClassVar

from pydantic import BaseModel, Field
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException

# --- Project Path Setup ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from Backend.tool_framework.base_tool import BaseTool

# --- Pydantic Input Schema ---
class RunSolverInput(BaseModel):
    pass # This tool takes no arguments from the AI

# --- Tool Class Definition ---
class RunSolverAndExportTool(BaseTool):
    """
    A Selenium bot that logs into UniTime, runs the solver,
    waits for it to finish, and exports the final solution.
    """
    name: str = "Run_Solver_and_Export"
    description: str = "Logs into UniTime, runs the course solver, waits, and exports the final schedule."
    args_schema: Type[BaseModel] = RunSolverInput

    # --- Helper: Wait for download to complete ---
    def _wait_for_download(self, download_path: str, timeout: int = 60) -> bool:
        """Waits for a file to finish downloading."""
        seconds = 0
        dl_wait = True
        while dl_wait and seconds < timeout:
            time.sleep(1)
            dl_wait = False
            # Check for partially downloaded files
            for fname in os.listdir(os.path.dirname(download_path)):
                if fname.endswith('.crdownload'):
                    dl_wait = True
            seconds += 1
        return not dl_wait

    def _execute(self) -> str:
        # --- 1. Get Configuration ---
        print("--- [Selenium Bot]: Starting Auto-Sync ---")
        base_url = self.get_tool_config("UNITIME_BASE_URL", "http://localhost:8080/UniTime")
        username = self.get_tool_config("UNITIME_USERNAME")
        password = self.get_tool_config("UNITIME_PASSWORD")
        export_path = self.get_tool_config("SCHEDULE_EXPORT_PATH")

        if not username or not password:
            return "Error: [Selenium Bot] Missing UNITIME_USERNAME or UNITIME_PASSWORD in config."

        # --- 2. Set up Selenium WebDriver ---
        options = webdriver.ChromeOptions()
        options.add_argument("--headless") # Run in the background
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # Set download directory
        download_dir = os.path.dirname(export_path)
        options.add_experimental_option("prefs", {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        })

        try:
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            wait = WebDriverWait(driver, 20) # 20-second wait
            print(f"--- [Selenium Bot]: WebDriver initialized. Download dir: {download_dir} ---")
        except Exception as e:
            return f"Error: [Selenium Bot] Failed to initialize WebDriver. {e}"

        try:
            # --- 3. Log In ---
            print(f"--- [Selenium Bot]: Logging in to {base_url} ---")
            driver.get(f"{base_url}/login.jsp")
            
            # *** CRITICAL: You MUST find the real IDs/names for these elements ***
            wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(username)
            driver.find_element(By.NAME, "password").send_keys(password)
            driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click() # Guessing the login button
            
            # Wait for login to complete (e.g., wait for 'Administration' link)
            wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Administration")))
            print("--- [Selenium Bot]: Login successful. ---")

            # --- 4. Run the Solver ---
            # *** CRITICAL: You MUST find the real URL for the solver page ***
            solver_url = f"{base_url}/gwt.jsp?page=solver"
            print(f"--- [Selenium Bot]: Navigating to Solver: {solver_url} ---")
            driver.get(solver_url)
            
            # *** CRITICAL: You MUST find the real ID/XPath for the solve button ***
            solve_button_xpath = "//button[text()='Compute']" # This is a GUESS
            wait.until(EC.element_to_be_clickable((By.XPATH, solve_button_xpath))).click()
            print("--- [Selenium Bot]: Solver started. Waiting for completion... ---")

            # *** CRITICAL: Find text that appears ONLY when solving is done ***
            # We will wait up to 15 minutes (900 seconds) for this
            long_wait = WebDriverWait(driver, 900)
            completion_text = "Solution committed" # This is a GUESS
            long_wait.until(EC.presence_of_element_located((By.XPATH, f"//*[contains(text(), '{completion_text}')]")))
            print("--- [Selenium Bot]: Solver finished. ---")

            # --- 5. Export the Solution ---
            export_page_url = f"{base_url}/gwt.jsp?page=listSolutions"
            print(f"--- [Selenium Bot]: Navigating to Export: {export_page_url} ---")
            driver.get(export_page_url)

            # *** CRITICAL: Find the XPath for the *correct* export button ***
            # This XPath assumes you want the first "Export Solution" button on the page
            export_button_xpath = "(//button[text()='Export Solution'])[1]" # This is a GUESS
            wait.until(EC.element_to_be_clickable((By.XPATH, export_button_xpath))).click()
            print("--- [Selenium Bot]: Export started. Waiting for download... ---")

            # --- 6. Wait for Download ---
            if os.path.exists(export_path):
                os.remove(export_path) # Remove old file first
            
            # Wait for download to finish
            if self._wait_for_download(export_path):
                print(f"--- [Selenium Bot]: Download complete. File saved to {export_path} ---")
            else:
                raise TimeoutException("File download timed out.")
            
            # The downloaded file might have a different name. We need to rename it.
            # This assumes the *newest* file in the dir is the one we want.
            downloaded_file = max([os.path.join(download_dir, f) for f in os.listdir(download_dir)], key=os.path.getctime)
            os.rename(downloaded_file, export_path)
            print(f"--- [Selenium Bot]: File renamed to {export_path} ---")

            return f"Success: UniTime solved and exported. Schedule saved to: {export_path}"

        except TimeoutException as te:
            return f"Error: [Selenium Bot] A step timed out. The UniTime UI may have changed. {te}"
        except Exception as e:
            return f"Error: [Selenium Bot] An unexpected error occurred. {e}"
        finally:
            driver.quit()
            print("--- [Selenium Bot]: WebDriver closed. ---")