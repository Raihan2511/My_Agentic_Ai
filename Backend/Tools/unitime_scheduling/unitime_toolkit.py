# # unitimr_toolkit.py

# from superagi.tools.base_tool import BaseToolkit
# from typing import List, Type
# from superagi.tools.base_tool import BaseTool

# # from .generate_xml_tool import GenerateXMLTool
# from superagi.tools.unitime_scheduling.generate_xml_tool import GenerateXMLTool
# # from .validate_xml_tool import ValidateXMLTool
# from superagi.tools.unitime_scheduling.validate_xml_tool import ValidateXMLTool
# # from .import_xml_tool import ImportXMLTool
# from superagi.tools.unitime_scheduling.import_xml_tool import ImportXMLTool

# class UnitimeToolkit(BaseToolkit):
#     name = "UnitimeToolkit"
#     description = "Toolkit for generating, validating, and importing UniTime-compatible XML"

#     def get_tools(self) -> List[Type[BaseTool]]:
#         return [GenerateXMLTool, ValidateXMLTool, ImportXMLTool]

#     def get_env_keys(self) -> List[str]:
#         return [
#             "HF_API_TOKEN",
#             "HF_MODEL_ENDPOINT",
#             "UNITIME_IMPORT_URL"
#         ]


# unitime_toolkit.py
from abc import ABC
from typing import List
import os
import sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from Backend.tool_framework.base_tool import BaseTool
from Backend.tool_framework.base_toolkit import BaseToolkit
from Backend.tool_framework.tool_config import ToolConfiguration

from Backend.Tools.unitime_scheduling.unitime_workflow_tool import UnitimeWorkflowTool
from Backend.Tools.unitime_scheduling.generate_xml_tool import GenerateXMLTool
from Backend.Tools.unitime_scheduling.validate_xml_tool import ValidateXMLTool
from Backend.Tools.unitime_scheduling.import_xml_tool import ImportXMLTool
from Backend.types.key_type import ToolConfigKeyType

class UnitimeToolkit(BaseToolkit, ABC):
    name: str = "UniTime Scheduling Toolkit"
    description: str = "Toolkit for generating, validating, and importing UniTime-compatible XML schedules"

    def get_tools(self) -> List[BaseTool]:
        return [UnitimeWorkflowTool(), GenerateXMLTool(), ValidateXMLTool(), ImportXMLTool()]

    def get_env_keys(self) -> List[ToolConfiguration]:
        return [
            ToolConfiguration(
                key="HF_API_TOKEN", 
                key_type=ToolConfigKeyType.STRING, 
                is_required=True, 
                is_secret=True
            ),
            ToolConfiguration(
                key="HF_MODEL_ENDPOINT", 
                key_type=ToolConfigKeyType.STRING, 
                is_required=True, 
                is_secret=False
            ),
            ToolConfiguration(
                key="UNITIME_IMPORT_URL", 
                key_type=ToolConfigKeyType.STRING, 
                is_required=True, 
                is_secret=False
            )
        ]