import os
import sys
from abc import ABC
from typing import List

# --- Project Path Setup ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from Backend.tool_framework.base_tool import BaseTool
from Backend.tool_framework.base_toolkit import BaseToolkit
from Backend.tool_framework.tool_config import ToolConfiguration
from Backend.types.key_type import ToolConfigKeyType

# --- Tool Imports ---
from Backend.Tools.university.add_to_batch_file import AddToBatchFileTool
from Backend.Tools.university.import_batch_file import ImportBatchFileTool
from Backend.Tools.university.update_course_file import UpdateCourseFileTool
from Backend.Tools.university.model_prompt_factory import ModelPromptFactoryTool
from Backend.Tools.university.add_preference_to_batch import AddPreferenceToBatchTool # <--- NEW IMPORT

class UniversityToolkit(BaseToolkit, ABC):
    name: str = "University Toolkit"
    description: str = "Toolkit containing all tools for interacting with university-specific systems."

    def get_tools(self) -> List[BaseTool]:
        return [
            AddToBatchFileTool(), 
            ImportBatchFileTool(),
            UpdateCourseFileTool(),
            ModelPromptFactoryTool(),
            AddPreferenceToBatchTool() # <--- NEW TOOL
        ]

    def get_env_keys(self) -> List[ToolConfiguration]:
        return [
            ToolConfiguration(key="GOOGLE_API_KEY", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=True),
            ToolConfiguration(key="BASE_MODEL_ID", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=False),
            ToolConfiguration(key="OFFERING_MODEL_PATH", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=False),
            ToolConfiguration(key="PREFERENCE_MODEL_PATH", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=False), # <--- CRITICAL FOR NEW TOOL
            ToolConfiguration(key="UNITIME_API_URL", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=False),
            ToolConfiguration(key="UNITIME_USERNAME", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=True),
            ToolConfiguration(key="UNITIME_PASSWORD", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=True)
        ]