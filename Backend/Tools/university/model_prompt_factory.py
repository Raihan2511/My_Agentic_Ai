# /home/sysadm/Music/My_Agentic_Ai/Backend/Tools/university/model_prompt_factory.py
from typing import Type
from pydantic import BaseModel, Field
from Backend.tool_framework.base_tool import BaseTool

class PromptFactoryInput(BaseModel):
    course_name: str = Field(..., description="Course Name (e.g., 'DLCS 000')")
    title: str = Field(..., description="The Course Title (e.g., 'Advanced AI')")
    location: str = Field(..., description="Full Location (e.g., 'EDUC 103')")
    days: str = Field(..., description="Days (e.g., MWF)")
    start_time: str = Field(..., description="Start Time HHmm (e.g., 0830)")
    end_time: str = Field(..., description="End Time HHmm (e.g., 0920)")
    capacity: int = Field(..., description="Class Limit (e.g., 30)")

class ModelPromptFactoryTool(BaseTool):
    name: str = "Model_Prompt_Factory"
    description: str = "Constructs the exact training prompt string required by the AI model for updates."
    args_schema: Type[BaseModel] = PromptFactoryInput

    def _execute(self, course_name: str, title: str, location: str, days: str, start_time: str, end_time: str, capacity: int) -> str:
        # CHANGED: Replaced 'capacity' with 'limit' to match the model's training data
        # CHANGED: Using combined course_name and location fields
        prompt = (
            f"Update course {course_name} "
            f"to title '{title}', room {location}, "
            f"meeting {days} at {start_time}-{end_time} "
            f"and limit {capacity}."
        )
        return prompt