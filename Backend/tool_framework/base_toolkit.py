# tool_framework/base_toolkit.py
from abc import ABC, abstractmethod
from typing import List
from pydantic import BaseModel

from tool_framework.base_tool import BaseTool
from tool_framework.tool_config import ToolConfiguration

class BaseToolkit(BaseModel, ABC):
    """Abstract Base Class for a collection of tools."""
    name: str
    description: str

    @abstractmethod
    def get_tools(self) -> List[BaseTool]:
        """
        Must be implemented by subclasses to return a list of tool instances.
        """
        pass

    @abstractmethod
    def get_env_keys(self) -> List[ToolConfiguration]:
        """
        Must be implemented by subclasses to declare required environment variables.
        """
        pass