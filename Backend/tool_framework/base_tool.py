# tool_framework/base_tool.py
import os
from abc import abstractmethod, ABC
from functools import wraps
from inspect import signature
from typing import Type, Callable, Any, Union, Dict, Tuple, Optional
from pydantic import BaseModel, create_model, validate_arguments, Extra
from dotenv import load_dotenv

# Load environment variables from a .env file if it exists
load_dotenv()

class SchemaSettings:
    """Configuration for the pydantic model generation."""
    extra = Extra.forbid
    arbitrary_types_allowed = True

def create_function_schema(schema_name: str, function: Callable) -> Type[BaseModel]:
    """Create a pydantic schema from a function's signature."""
    validated = validate_arguments(function, config=SchemaSettings)
    inferred_type = validated.model
    # The 'run_manager' is likely an internal argument we don't want exposed in the schema
    if "run_manager" in inferred_type.__fields__:
        del inferred_type.__fields__["run_manager"]
    
    # Re-create the model without the unwanted fields
    fields = {
        field: (details.type_, details.default)
        for field, details in inferred_type.__fields__.items()
    }
    return create_model(schema_name, **fields)

class BaseToolkitConfiguration:
    """Handles retrieval of configuration values from environment variables."""
    def get_tool_config(self, key: str) -> Optional[str]:
        """Retrieve a value from the environment variables."""
        if not isinstance(key, str):
            return None
        return os.getenv(key)

class BaseTool(BaseModel, ABC):
    """Abstract Base Class for all Tools."""
    name: str
    description: str
    args_schema: Optional[Type[BaseModel]] = None
    toolkit_config: BaseToolkitConfiguration = BaseToolkitConfiguration()

    class Config:
        arbitrary_types_allowed = True

    @property
    def args(self) -> dict:
        """
        Get the arguments schema for the tool. If not provided, it's inferred
        from the _execute method's signature.
        """
        if self.args_schema:
            return self.args_schema.schema()["properties"]
        
        # Auto-generate schema from the _execute method
        schema_name = f"{self.name.replace(' ', '')}Schema"
        inferred_schema = create_function_schema(schema_name, self._execute)
        return inferred_schema.schema()["properties"]

    @abstractmethod
    def _execute(self, *args: Any, **kwargs: Any) -> Any:
        """
        The core logic of the tool. Must be implemented by subclasses.
        This is where you'd make API calls, interact with files, etc.
        """
        pass

    def _to_args_and_kwargs(self, tool_input: Union[str, Dict]) -> Tuple[Tuple, Dict]:
        """Helper to parse input into positional and keyword arguments."""
        if isinstance(tool_input, str):
            return (tool_input,), {}
        return (), tool_input

    def execute(self, tool_input: Union[str, Dict], **kwargs: Any) -> Any:
        """
        Public-facing wrapper to run the tool with input validation and error handling.
        """
        # Note: We are simplifying the parsing logic from the original for clarity.
        # A more robust implementation would validate the tool_input against the args_schema.
        try:
            tool_args, tool_kwargs = self._to_args_and_kwargs(tool_input)
            # Combine kwargs for flexibility
            all_kwargs = {**tool_kwargs, **kwargs}
            return self._execute(*tool_args, **all_kwargs)
        except Exception as e:
            # Proper error handling is important for agent stability
            return f"Error in tool '{self.name}': {e}"
            
    def get_tool_config(self, key: str) -> Optional[str]:
        """Convenience method to get a configuration value for this tool."""
        return self.toolkit_config.get_tool_config(key=key)