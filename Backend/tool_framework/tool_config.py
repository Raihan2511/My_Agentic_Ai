# tool_framework/tool_config.py
from enum import Enum
from Backend.types.key_type import ToolConfigKeyType


# class ToolConfigKeyType(str, Enum):
#     """Enumeration for tool configuration key types."""
#     STRING = "STRING"
#     INTEGER = "INTEGER"
#     FILE = "FILE"
#     BOOLEAN = "BOOLEAN"

class ToolConfiguration:
    """A class to define a configuration requirement for a tool or toolkit."""
    def __init__(self, key: str, key_type: ToolConfigKeyType, is_required: bool = False, is_secret: bool = False):
        if not isinstance(key, str) or not key:
            raise ValueError("key must be a non-empty string")
        if not isinstance(key_type, ToolConfigKeyType):
            raise ValueError(f"key_type must be an instance of ToolConfigKeyType, not {type(key_type)}")
            
        self.key = key
        self.key_type = key_type
        self.is_required = bool(is_required)
        self.is_secret = bool(is_secret)

    def __repr__(self):
        return f"ToolConfiguration(key='{self.key}', key_type='{self.key_type.value}', required={self.is_required}, secret={self.is_secret})"