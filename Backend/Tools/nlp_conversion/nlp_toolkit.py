import os
import sys
from abc import ABC
from typing import List

# --- Project Path Setup ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# --- Framework Imports ---
from Backend.tool_framework.base_tool import BaseTool
from Backend.tool_framework.base_toolkit import BaseToolkit
from Backend.tool_framework.tool_config import ToolConfiguration
from Backend.types.key_type import ToolConfigKeyType

# --- Tool Imports ---
from Backend.Tools.nlp_conversion.nlp_to_xml_tool import NLPToXMLTool

class NLPToolkit(BaseToolkit, ABC):
    """
    Toolkit for converting natural language into UniTime XML
    using fine-tuned transformer models.
    """
    name: str = "NLP Conversion Toolkit"
    description: str = "Tools for converting NLP text to UniTime XML."

    def get_tools(self) -> List[BaseTool]:
        """Returns a list of tools available in this toolkit."""
        return [NLPToXMLTool()]

    def get_env_keys(self) -> List[ToolConfiguration]:
        """
        Defines the environment variables required for the tools.
        These keys tell the tool where to find the fine-tuned models.
        """
        return [
            ToolConfiguration(
                key="OFFERING_MODEL_PATH", 
                key_type=ToolConfigKeyType.STRING, 
                is_required=True, 
                is_secret=False,
                # Using the exact path you provided as the default
                default="/home/sysadm/Music/unitime_nlp/test/Offereing-nlp-to-xml/checkpoint-462"
            ),
            ToolConfiguration(
                key="PREFERENCE_MODEL_PATH", 
                key_type=ToolConfigKeyType.STRING, 
                is_required=True, 
                is_secret=False,
                # Using the exact path you provided as the default
                default="/home/sysadm/Music/unitime_nlp/test/Preference-nlp-to-xml/checkpoint-308"
            )
        ]