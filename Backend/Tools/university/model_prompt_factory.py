from typing import Type
from pydantic import BaseModel, Field
from Backend.tool_framework.base_tool import BaseTool

class PromptFactoryInput(BaseModel):
    subject: str = Field(..., description="Course Subject (e.g., DLCS)")
    number: str = Field(..., description="Course Number (e.g., 101)")
    title: str = Field(..., description="The Course Title (e.g., 'Advanced AI')")
    building: str = Field(..., description="Full Building Name (e.g., Engineering)")
    room: str = Field(..., description="Room Number (e.g., 205)")
    days: str = Field(..., description="Days (e.g., MWF)")
    start_time: str = Field(..., description="Start Time HHmm (e.g., 0830)")
    end_time: str = Field(..., description="End Time HHmm (e.g., 0920)")
    capacity: int = Field(..., description="Class Limit (e.g., 30)")

class ModelPromptFactoryTool(BaseTool):
    name: str = "Model_Prompt_Factory"
    description: str = "Constructs the exact training prompt string required by the AI model for updates."
    args_schema: Type[BaseModel] = PromptFactoryInput

    def _execute(self, subject: str, number: str, title: str, building: str, room: str, days: str, start_time: str, end_time: str, capacity: int) -> str:
        # MATCHES YOUR V2 DATASET GENERATOR EXACTLY
        prompt = (
            f"Update course {subject} {number} "
            f"to title '{title}', room {building} {room}, "
            f"meeting {days} at {start_time}-{end_time} "
            f"and capacity {capacity}."
        )
        return prompt