import os
import sys
from abc import ABC
from typing import List

# --- Project Path Setup ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# --- Framework Imports ---
from Backend.tool_framework.base_tool import BaseTool
from Backend.tool_framework.base_toolkit import BaseToolkit
from Backend.tool_framework.tool_config import ToolConfiguration
from Backend.types.key_type import ToolConfigKeyType

# --- Tool Imports ---
# <-- FIXED: Changed import from 'run_solver' to the new filename 'export_saved_timetable'
from Backend.Tools.Auto_sync.export_saved_timetable import ExportTimetableTool

class AutoSyncToolkit(BaseToolkit, ABC):
    name: str = "Auto-Sync Toolkit"
    description: str = "Toolkit containing the Selenium bot to export the final schedule from UniTime."

    def get_tools(self) -> List[BaseTool]:
        """Returns a list of tools available in this toolkit."""
        return [ExportTimetableTool()]

    def get_env_keys(self) -> List[ToolConfiguration]:
        """Defines the environment variables required for the tools in this toolkit."""
        return [
            ToolConfiguration(key="UNITIME_USERNAME", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=True),
            ToolConfiguration(key="UNITIME_PASSWORD", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=True),
            ToolConfiguration(key="UNITIME_BASE_URL", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=False, default="http://localhost:8080/UniTime"),
            ToolConfiguration(key="SCHEDULE_EXPORT_PATH", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=False, default=os.path.join(PROJECT_ROOT, "schedule_export.csv"))
        ]