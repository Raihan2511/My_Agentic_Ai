# refresh_rag_database.py
import os
import sys
from typing import Type
import pandas as pd
from pydantic import BaseModel

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from Backend.tool_framework.base_tool import BaseTool

from langchain.docstore.document import Document
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings


class RefreshRAGInput(BaseModel):
    pass


class RefreshRAGDatabaseTool(BaseTool):
    name: str = "Refresh_RAG_Database"
    description: str = "Rebuilds the RAG FAISS index from exported schedule CSV."
    args_schema: Type[BaseModel] = RefreshRAGInput

    def _default(self, key, fallback):
        """Helper: return config or a safe default."""
        value = self.get_tool_config(key)
        return value if value not in (None, "") else fallback

    def _execute(self):
        print("--- [RAG Refresh]: Starting ---")

        # -------------------------
        # CONFIG / DEFAULT PATHS
        # -------------------------
        csv_path = self._default(
            "SCHEDULE_EXPORT_PATH",
            os.path.join(PROJECT_ROOT, "data/schedule_export.csv")
        )

        index_path = self._default(
            "RAG_INDEX_PATH",
            os.path.join(PROJECT_ROOT, "data/rag_index")
        )

        # Ensure directory exists
        os.makedirs(index_path, exist_ok=True)

        if not os.path.exists(csv_path):
            return f"Error: CSV not found at {csv_path}"

        # -------------------------
        # LOAD CSV
        # -------------------------
        try:
            print(f"--- [RAG Refresh]: Loading CSV {csv_path} ---")
            df = pd.read_csv(csv_path)

            df["combined_text"] = df.apply(
                lambda row: ". ".join(
                    f"{col}: {val}" for col, val in row.items() if pd.notna(val)
                ),
                axis=1
            )

            documents = [
                Document(
                    page_content=row["combined_text"],
                    metadata={col: row[col] for col in df.columns if col != "combined_text"}
                )
                for _, row in df.iterrows()
            ]

        except Exception as e:
            return f"Error reading CSV: {e}"

        # -------------------------
        # BUILD & SAVE INDEX
        # -------------------------
        try:
            print("--- Initializing embeddings model ---")
            embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )

            print("--- Building FAISS index ---")
            db = FAISS.from_documents(documents, embeddings)

            print(f"--- Saving FAISS index to {index_path} ---")
            db.save_local(index_path)

            return (
                f"Success: RAG index refreshed. Documents: {len(documents)}.\n"
                f"Location: {index_path}"
            )

        except Exception as e:
            return f"Error saving FAISS index: {e}"
