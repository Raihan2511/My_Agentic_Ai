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
from Backend.Tools.rag_system.refresh_rag_database import RefreshRAGDatabaseTool
from Backend.Tools.rag_system.query_student_timetable import QueryStudentTimetableTool

class RAGToolkit(BaseToolkit, ABC):
    name: str = "RAG Toolkit"
    description: str = "Toolkit for building, refreshing, and querying the student-facing RAG chatbot."

    def get_tools(self) -> List[BaseTool]:
        """Returns a list of tools available in this toolkit."""
        return [RefreshRAGDatabaseTool(), QueryStudentTimetableTool()]

    def get_env_keys(self) -> List[ToolConfiguration]:
        """Defines the environment variables required for the tools in this toolkit."""
        return [
            ToolConfiguration(key="SCHEDULE_EXPORT_PATH", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=False, default=os.path.join(PROJECT_ROOT, "schedule_export.csv")),
            ToolConfiguration(key="RAG_INDEX_PATH", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=False, default=os.path.join(PROJECT_ROOT, "faiss_index")),
            # CHANGED: Switched to KRUTRIM_API_KEY
            ToolConfiguration(key="KRUTRIM_API_KEY", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=True)
        ]