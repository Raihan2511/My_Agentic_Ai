# refresh_rag_database.py
import os
import sys
from typing import Type
import pandas as pd
from pydantic import BaseModel, Field

# --- Project Path Setup ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from Backend.tool_framework.base_tool import BaseTool

# --- LangChain Imports ---
from langchain.docstore.document import Document
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

# --- Pydantic Input Schema ---
class RefreshRAGInput(BaseModel):
    # This tool could take a path, but it's more robust
    # to read it from the central config.
    pass

# --- Tool Class Definition ---
class RefreshRAGDatabaseTool(BaseTool):
    """
    Reads the exported schedule CSV, processes it, and builds
    (or rebuilds) the FAISS vector database.
    """
    name: str = "Refresh_RAG_Database"
    description: str = "Rebuilds the RAG vector database from the exported schedule CSV file."
    args_schema: Type[BaseModel] = RefreshRAGInput

    def _execute(self) -> str:
        # --- 1. Get Configuration ---
        print("--- [RAG Refresh]: Starting ---")
        csv_path = self.get_tool_config("SCHEDULE_EXPORT_PATH")
        index_path = self.get_tool_config("RAG_INDEX_PATH")

        if not os.path.exists(csv_path):
            return f"Error: [RAG Refresh] Exported schedule file not found at {csv_path}. Did the Selenium bot run?"

        # --- 2. Load and Process Data ---
        try:
            print(f"--- [RAG Refresh]: Loading CSV from {csv_path} ---")
            df = pd.read_csv(csv_path)
            
            # This is a basic conversion. You can get much more detailed here
            # by combining columns to make a nice "page_content".
            # For example: "Course BIOL 101 meets on Monday at 10:30 in EDUC 101."
            
            # For now, we'll just convert each row to a string
            df['combined_text'] = df.apply(
                lambda row: ". ".join(f"{col}: {val}" for col, val in row.items() if pd.notna(val)), 
                axis=1
            )
            
            # Create LangChain Document objects
            documents = [
                Document(
                    page_content=row['combined_text'],
                    # You MUST add metadata for filtering
                    metadata={col: row[col] for col in df.columns if col != 'combined_text'} 
                ) for _, row in df.iterrows()
            ]
            
            print(f"--- [RAG Refresh]: Loaded {len(documents)} documents from CSV. ---")

        except Exception as e:
            return f"Error: [RAG Refresh] Failed to read or process CSV file. {e}"

        # --- 3. Build Vector Index ---
        try:
            # Use a fast, local embedding model
            print("--- [RAG Refresh]: Initializing embedding model... ---")
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            
            print("--- [RAG Refresh]: Building FAISS index... ---")
            # Create the vector store from the documents
            db = FAISS.from_documents(documents, embeddings)
            
            # Save the index to disk
            db.save_local(index_path)
            print(f"--- [RAG Refresh]: Success! RAG database saved to {index_path} ---")
            
            return f"Success: RAG database has been refreshed with {len(documents)} entries."

        except Exception as e:
            return f"Error: [RAG Refresh] Failed to build or save vector index. {e}"