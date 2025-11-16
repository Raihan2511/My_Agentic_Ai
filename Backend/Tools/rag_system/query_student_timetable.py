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
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# --- Pydantic Input Schema ---
class QueryTimetableInput(BaseModel):
    query: str = Field(..., description="The student's natural language question about their schedule.")

# --- Tool Class Definition ---
class QueryStudentTimetableTool(BaseTool):
    """
    Answers a student's question about their schedule by
    querying the RAG vector database.
    """
    name: str = "Query_Student_Timetable"
    description: str = "Answers student questions about class times, locations, or instructors."
    args_schema: Type[BaseModel] = QueryTimetableInput

    def _execute(self, query: str) -> str:
        # --- 1. Get Configuration ---
        print(f"--- [RAG Query]: Received query: {query} ---")
        index_path = self.get_tool_config("RAG_INDEX_PATH")
        google_api_key = self.get_tool_config("GOOGLE_API_KEY")

        if not os.path.exists(index_path):
            return "Error: [RAG Query] The RAG database index is not found. Please ask an admin to run the 'sync' process."

        # --- 2. Initialize LLM, Embeddings, and Vector Store ---
        try:
            llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", google_api_key=google_api_key, temperature=0.0)
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            
            print("--- [RAG Query]: Loading FAISS index... ---")
            db = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True) # Allow loading
            retriever = db.as_retriever(search_kwargs={"k": 3}) # Get top 3 results
            
        except Exception as e:
            return f"Error: [RAG Query] Failed to load RAG components. {e}"

        # --- 3. Build RAG Chain ---
        template = """
        You are a helpful university assistant. Answer the user's question based *only* on the following context.
        If the information is not in the context, say "I'm sorry, I don't have that information in the schedule."

        Context:
        {context}

        Question:
        {question}

        Answer:
        """
        prompt = ChatPromptTemplate.from_template(template)

        # This chain:
        # 1. Takes the "question"
        # 2. Passes it to the retriever to get "context"
        # 3. Passes "context" and "question" to the LLM
        # 4. Gets the final string output
        rag_chain = (
            {"context": retriever, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )

        # --- 4. Run Chain ---
        try:
            print("--- [RAG Query]: Invoking RAG chain... ---")
            answer = rag_chain.invoke(query)
            print(f"--- [RAG Query]: Answer generated: {answer} ---")
            return answer
            
        except Exception as e:
            return f"Error: [RAG Query] An error occurred during RAG chain invocation. {e}"