# # Backend/Tools/university/university_toolkit.py

# import os
# import sys
# from abc import ABC
# from typing import List

# # --- Project Path Setup ---
# PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
# if PROJECT_ROOT not in sys.path:
#     sys.path.append(PROJECT_ROOT)

# # --- Framework Imports ---
# from Backend.tool_framework.base_tool import BaseTool
# from Backend.tool_framework.base_toolkit import BaseToolkit
# from Backend.tool_framework.tool_config import ToolConfiguration
# from Backend.types.key_type import ToolConfigKeyType

# # --- Tool Imports ---
# from Backend.Tools.university.invoke_hf_model import InvokeHFModelTool
# from Backend.Tools.university.import_to_unitime import ImportToUnitimeTool


# class UniversityToolkit(BaseToolkit, ABC):
#     name: str = "University Toolkit"
#     description: str = "Toolkit containing all tools for interacting with university-specific systems like the custom AI model and Unitime."

#     def get_tools(self) -> List[BaseTool]:
#         """Returns a list of tools available in this toolkit."""
#         return [InvokeHFModelTool(), ImportToUnitimeTool()]

#     def get_env_keys(self) -> List[ToolConfiguration]:
#         """Defines the environment variables required for the tools in this toolkit."""
#         return [
#             ToolConfiguration(key="HF_TOKEN", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=True),
#             ToolConfiguration(key="HF_MODEL_REPO", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=False),
#             ToolConfiguration(key="UNITIME_API_URL", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=False),
#             ToolConfiguration(key="UNITIME_API_KEY", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=True)
#         ]

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

# --- Tool Imports (CHANGED) ---
from Backend.Tools.university.add_to_batch_file import AddToBatchFileTool
from Backend.Tools.university.import_batch_file import ImportBatchFileTool


class UniversityToolkit(BaseToolkit, ABC):
    name: str = "University Toolkit"
    description: str = "Toolkit containing all tools for interacting with university-specific systems like the custom AI model and Unitime."

    def get_tools(self) -> List[BaseTool]:
        """Returns a list of tools available in this toolkit."""
        # --- (CHANGED) ---
        return [AddToBatchFileTool(), ImportBatchFileTool()]

    def get_env_keys(self) -> List[ToolConfiguration]:
        """Defines the environment variables required for the tools in this toolkit."""
        # --- (CHANGED) ---
        return [
            # For the classifier LLM (in AddToBatchFileTool)
            ToolConfiguration(key="GOOGLE_API_KEY", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=True),
            
            # For the fine-tuned models (in AddToBatchFileTool)
            ToolConfiguration(key="BASE_MODEL_ID", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=False),
            ToolConfiguration(key="OFFERING_MODEL_PATH", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=False),
            ToolConfiguration(key="PREFERENCE_MODEL_PATH", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=False),
            
            # For the UniTime API (in ImportBatchFileTool)
            ToolConfiguration(key="UNITIME_API_URL", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=False),
            ToolConfiguration(key="UNITIME_USERNAME", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=True),
            ToolConfiguration(key="UNITIME_PASSWORD", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=True)
        ]