# Backend/Tools/university/university_toolkit.py

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
from Backend.Tools.university.invoke_hf_model import InvokeHFModelTool
from Backend.Tools.university.import_to_unitime import ImportToUnitimeTool


class UniversityToolkit(BaseToolkit, ABC):
    name: str = "University Toolkit"
    description: str = "Toolkit containing all tools for interacting with university-specific systems like the custom AI model and Unitime."

    def get_tools(self) -> List[BaseTool]:
        """Returns a list of tools available in this toolkit."""
        return [InvokeHFModelTool(), ImportToUnitimeTool()]

    def get_env_keys(self) -> List[ToolConfiguration]:
        """Defines the environment variables required for the tools in this toolkit."""
        return [
            ToolConfiguration(key="HF_TOKEN", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=True),
            ToolConfiguration(key="HF_MODEL_REPO", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=False),
            ToolConfiguration(key="UNITIME_API_URL", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=False),
            ToolConfiguration(key="UNITIME_API_KEY", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=True)
        ]