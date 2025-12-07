import os
import sys
from typing import Type
from pydantic import BaseModel, Field

# --- Project Path Setup ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from Backend.tool_framework.base_tool import BaseTool

# --- LangChain Imports ---
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
# CHANGED: Switched from Google to OpenAI (Krutrim compatible)
from langchain_openai import ChatOpenAI 
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# --- Pydantic Input Schema ---
class QueryTimetableInput(BaseModel):
    query: str = Field(..., description="The student's natural language question about their schedule.")

# --- Tool Class Definition ---
class QueryStudentTimetableTool(BaseTool):
    name: str = "Query_Student_Timetable"
    description: str = "Answers student questions about class times, locations, or instructors."
    args_schema: Type[BaseModel] = QueryTimetableInput

    def _execute(self, query: str) -> str:
        print(f"--- [RAG Query]: Received query: {query} ---")

        # ------------------------------
        # 1. LOAD CONFIG OR FALLBACK
        # ------------------------------
        index_path = (
            self.get_tool_config("RAG_INDEX_PATH")
            or os.path.join(PROJECT_ROOT, "data/rag_index")
        )

        # Ensure index path is a directory
        if not isinstance(index_path, str):
            return "Error: RAG index path must be a string."

        if not os.path.exists(index_path):
            return f"Error: [RAG Query] RAG index not found at {index_path}"

        # ------------------------------
        # 2. LOAD LLM & VECTOR INDEX
        # ------------------------------
        try:
            print("--- [RAG Query]: Initializing LLM and embeddings... ---")
            
            # --- KRUTRIM CONFIGURATION ---
            krutrim_api_key = os.getenv("KRUTRIM_API_KEY")
            # Default to the model you specified if not found in env
            model_name = os.getenv("LLM_MODEL", "Qwen3-Next-80B-A3B-Instruct")

            if not krutrim_api_key:
                return "Error: KRUTRIM_API_KEY not found in environment variables."

            llm = ChatOpenAI(
                model=model_name,
                api_key=krutrim_api_key,
                base_url="https://cloud.olakrutrim.com/v1",
                temperature=0.0
            )
            # -----------------------------

            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

            print(f"--- [RAG Query]: Loading FAISS index from {index_path} ---")
            db = FAISS.load_local(
                index_path,
                embeddings,
                allow_dangerous_deserialization=True
            )

            retriever = db.as_retriever(search_kwargs={"k": 3})

        except Exception as e:
            return f"Error: [RAG Query] Failed to load RAG components. {e}"

        # ------------------------------
        # 3. BUILD RAG CHAIN
        # ------------------------------
        template = """
        You are a helpful university assistant. Answer ONLY from the context below.
        If the information is missing, reply:
        "I'm sorry, I don't have that information in the schedule."

        Context:
        {context}

        Question:
        {question}

        Answer:
        """

        prompt = ChatPromptTemplate.from_template(template)

        rag_chain = (
            {"context": retriever, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )

        # ------------------------------
        # 4. RUN QUERY
        # ------------------------------
        try:
            print("--- [RAG Query]: Invoking RAG chain... ---")
            answer = rag_chain.invoke(query)
            return answer

        except Exception as e:
            return f"Error: [RAG Query] Error during query execution. {e}"