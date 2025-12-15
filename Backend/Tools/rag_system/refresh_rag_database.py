import os
import sys
import pandas as pd
from typing import Type, Optional, Dict, List
from pydantic import BaseModel

# -------------------------------------------------
# Project Path Setup
# -------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from Backend.tool_framework.base_tool import BaseTool

# -------------------------------------------------
# LangChain Imports
# -------------------------------------------------
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document


# -------------------------------------------------
# Input Schema
# -------------------------------------------------
class RefreshRAGInput(BaseModel):
    query: Optional[str] = "trigger"


# -------------------------------------------------
# Tool Definition
# -------------------------------------------------
class RefreshRAGDatabaseTool(BaseTool):
    name: str = "Refresh_RAG_Database"
    description: str = (
        "Reads UniTime CSV (events), converts rows to JSON, "
        "creates semantic documents, and rebuilds the FAISS RAG index."
    )
    args_schema: Type[BaseModel] = RefreshRAGInput

    def _execute(self, query: str = "trigger") -> str:
        print("--- [RAG Refresh]: Starting ---")

        # -------------------------------------------------
        # Paths
        # -------------------------------------------------
        csv_path = os.path.join(PROJECT_ROOT, "data/schedule_export.csv")
        index_path = os.path.join(PROJECT_ROOT, "data/rag_index")

        if not os.path.exists(csv_path):
            return f"Error: CSV file not found at {csv_path}"

        try:
            # -------------------------------------------------
            # 1. LOAD CSV → JSON
            # -------------------------------------------------
            df = pd.read_csv(csv_path, dtype=str).fillna("")
            records: List[Dict] = df.to_dict(orient="records")

            print(f"--- [RAG Refresh]: Loaded {len(records)} rows from CSV ---")

            documents: List[Document] = []

            # -------------------------------------------------
            # 2. JSON → NATURAL LANGUAGE DOCUMENTS
            # -------------------------------------------------
            for r in records:
                course = r.get("Name", "Unknown Course")
                section = r.get("Section", "")
                class_type = r.get("Type", "")
                title = r.get("Title", "")
                days = r.get("Day Of Week", "")
                start = r.get("Published Start", "")
                end = r.get("Published End", "")
                location = r.get("Location", "")
                instructor = r.get("Instructor / Sponsor", "")

                # --- Embedding-friendly sentence ---
                page_content = (
                    f"{course}"
                    f"{f' ({title})' if title else ''}, "
                    f"section {section}, is a {class_type.lower()} "
                    f"scheduled from {start} to {end} on {days} "
                    f"in {location}. "
                    f"The instructor is {instructor}."
                )

                metadata = {
                    "source": "unitime_csv",
                    "course": course,
                    "section": section,
                    "type": class_type,
                    "day": days,
                    "location": location,
                    "instructor": instructor,
                }

                documents.append(
                    Document(
                        page_content=page_content.strip(),
                        metadata=metadata
                    )
                )

            if not documents:
                return "Error: No documents were created from the CSV."

            print(f"--- [RAG Refresh]: Created {len(documents)} documents ---")

            # -------------------------------------------------
            # 3. BUILD & SAVE FAISS INDEX
            # -------------------------------------------------
            embeddings = HuggingFaceEmbeddings(
                model_name="all-MiniLM-L6-v2"
            )

            db = FAISS.from_documents(documents, embeddings)
            db.save_local(index_path)

            print("--- [RAG Refresh]: FAISS index saved ---")

            return (
                f"Success: RAG database refreshed successfully.\n"
                f"• Documents indexed: {len(documents)}\n"
                f"• Index path: {index_path}\n"
                f"You can now query class times, rooms, instructors, and days."
            )

        except Exception as e:
            return f"Error during RAG refresh: {str(e)}"
