# # refresh_rag_database.py
# import os
# import sys
# from typing import Type
# import pandas as pd
# from pydantic import BaseModel

# PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
# if PROJECT_ROOT not in sys.path:
#     sys.path.append(PROJECT_ROOT)

# from Backend.tool_framework.base_tool import BaseTool

# # from langchain.docstore.document import Document
# from langchain_core.documents import Document
# from langchain_community.vectorstores import FAISS
# from langchain_community.embeddings import HuggingFaceEmbeddings


# class RefreshRAGInput(BaseModel):
#     pass


# class RefreshRAGDatabaseTool(BaseTool):
#     name: str = "Refresh_RAG_Database"
#     description: str = "Rebuilds the RAG FAISS index from exported schedule CSV."
#     args_schema: Type[BaseModel] = RefreshRAGInput

#     def _default(self, key, fallback):
#         """Helper: return config or a safe default."""
#         value = self.get_tool_config(key)
#         return value if value not in (None, "") else fallback

#     def _execute(self):
#         print("--- [RAG Refresh]: Starting ---")

#         # -------------------------
#         # CONFIG / DEFAULT PATHS
#         # -------------------------
#         csv_path = self._default(
#             "SCHEDULE_EXPORT_PATH",
#             os.path.join(PROJECT_ROOT, "data/schedule_export.csv")
#         )

#         index_path = self._default(
#             "RAG_INDEX_PATH",
#             os.path.join(PROJECT_ROOT, "data/rag_index")
#         )

#         # Ensure directory exists
#         os.makedirs(index_path, exist_ok=True)

#         if not os.path.exists(csv_path):
#             return f"Error: CSV not found at {csv_path}"

#         # -------------------------
#         # LOAD CSV
#         # -------------------------
#         try:
#             print(f"--- [RAG Refresh]: Loading CSV {csv_path} ---")
#             df = pd.read_csv(csv_path)

#             df["combined_text"] = df.apply(
#                 lambda row: ". ".join(
#                     f"{col}: {val}" for col, val in row.items() if pd.notna(val)
#                 ),
#                 axis=1
#             )

#             documents = [
#                 Document(
#                     page_content=row["combined_text"],
#                     metadata={col: row[col] for col in df.columns if col != "combined_text"}
#                 )
#                 for _, row in df.iterrows()
#             ]

#         except Exception as e:
#             return f"Error reading CSV: {e}"

#         # -------------------------
#         # BUILD & SAVE INDEX
#         # -------------------------
#         try:
#             print("--- Initializing embeddings model ---")
#             embeddings = HuggingFaceEmbeddings(
#                 model_name="sentence-transformers/all-MiniLM-L6-v2"
#             )

#             print("--- Building FAISS index ---")
#             db = FAISS.from_documents(documents, embeddings)

#             print(f"--- Saving FAISS index to {index_path} ---")
#             db.save_local(index_path)

#             return (
#                 f"Success: RAG index refreshed. Documents: {len(documents)}.\n"
#                 f"Location: {index_path}"
#             )

#         except Exception as e:
#             return f"Error saving FAISS index: {e}"



import os
import sys
import pandas as pd
from typing import Type, Optional
from pydantic import BaseModel

# --- Project Path Setup ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from Backend.tool_framework.base_tool import BaseTool

# --- LangChain Imports ---
from langchain_community.vectorstores import FAISS
# Note: Use the modern import if available, otherwise fallback is handled by your env
from langchain_huggingface import HuggingFaceEmbeddings 
from langchain_core.documents import Document

class RefreshRAGInput(BaseModel):
    query: Optional[str] = "trigger"

class RefreshRAGDatabaseTool(BaseTool):
    name: str = "Refresh_RAG_Database"
    description: str = "Reads the exported CSV and rebuilds the RAG memory with smart sentence conversion."
    args_schema: Type[BaseModel] = RefreshRAGInput

    def _execute(self, query: str = "trigger") -> str:
        print("--- [RAG Refresh]: Starting ---")
        
        # 1. Define Paths (FORCE CSV extension)
        csv_path = os.path.join(PROJECT_ROOT, "data/exported_timetable.csv")
        index_path = os.path.join(PROJECT_ROOT, "data/rag_index")

        if not os.path.exists(csv_path):
            # Fallback for the XML naming confusion
            xml_path = os.path.join(PROJECT_ROOT, "data/exported_timetable.xml")
            if os.path.exists(xml_path):
                print(f"--- [RAG Refresh]: Found .xml file, renaming to .csv for processing ---")
                csv_path = xml_path
            else:
                return f"Error: Source file not found at {csv_path}. Please run 'Export_Timetable' first."

        print(f"--- [RAG Refresh]: Loading CSV {csv_path} ---")

        try:
            # 2. Read CSV with Pandas (Handles quotes and commas correctly)
            # header=0 means the first row contains "Name", "Section", etc.
            df = pd.read_csv(csv_path, dtype=str).fillna("")
            
            # 3. Convert Rows to "Smart Sentences"
            documents = []
            for _, row in df.iterrows():
                # Extract columns based on YOUR csv structure
                name = row.get("Name", "Unknown Class")         # ALG 101
                title = row.get("Title", "")                    # Algebra I
                room = row.get("Location", "Unknown Room")      # EDUC 103
                time_start = row.get("Published Start", "")     # 9:30a
                days = row.get("Day Of Week", "")               # MWF
                instructor = row.get("Instructor / Sponsor", "") # Doe, J

                # Create the sentence the AI will actually read
                page_content = (
                    f"Class: {name}. "
                    f"Title: {title}. "
                    f"Location: {room}. "
                    f"Time: {time_start} on {days}. "
                    f"Instructor: {instructor}."
                )

                # Add metadata for filtering
                metadata = {"source": "timetable", "course_name": name}
                documents.append(Document(page_content=page_content, metadata=metadata))

            print(f"--- [RAG Refresh]: Converted {len(documents)} rows into clean sentences. ---")

            # 4. Build Vector Index
            print("--- Initializing embeddings model ---")
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

            print("--- Building FAISS index ---")
            db = FAISS.from_documents(documents, embeddings)

            print(f"--- Saving FAISS index to {index_path} ---")
            db.save_local(index_path)

            return f"Success: RAG index refreshed with {len(documents)} classes."

        except Exception as e:
            return f"Error during RAG refresh: {str(e)}"