from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sys
import os
import logging

# Add parent directory to path to import multiagent
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the compiled graph from your multi_agent.py
# Ensure multi_agent.py has `app = workflow.compile()` accessible
from kurt_multi_agent import app as langgraph_app

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="University Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Updated Data Models ---
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[Message] = [] # New: Accept chat history

class ChatResponse(BaseModel):
    response: str
    agent: Optional[str] = None
    tool_calls: List[str] = []

@app.get("/")
async def root():
    return {"message": "University Assistant API is running"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process a chat message with history through the multi-agent system
    """
    try:
        logger.info(f"Received message: {request.message}")
        
        # 1. Reconstruct the state from history
        # LangGraph expects a list of tuples or objects for messages
        # We map 'user' -> 'human' and 'bot' -> 'ai' for LangChain/LangGraph compatibility
        messages = []
        for msg in request.history:
            if msg.role == "user":
                messages.append(("user", msg.content))
            elif msg.role == "bot":
                messages.append(("assistant", msg.content))
        
        # Append the new user message
        messages.append(("user", request.message))
        
        state = {"messages": messages}
        
        # 2. Run the graph
        agent_used = "READ" # Default
        tools_called = []
        final_response = ""

        # Stream through the graph to capture events
        for event in langgraph_app.stream(state):
            for node, output in event.items():
                
                # Detect Agent
                if "agent" in node:
                    if "test_agent" in node: agent_used = "TEST"
                    elif "read_agent" in node: agent_used = "READ"
                    elif "write_agent" in node: agent_used = "WRITE"
                    elif "sync_agent" in node: agent_used = "SYNC"
                    elif "import_agent" in node: agent_used = "IMPORT"

                    # Capture the latest message content from this node
                    if "messages" in output:
                        last_msg = output["messages"][-1]
                        
                        # Check for tool calls in this message
                        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                            for tc in last_msg.tool_calls:
                                tools_called.append(tc.get("name", "Unknown"))
                        
                        # If it's a text response, update final_response
                        if hasattr(last_msg, "content") and last_msg.content:
                            final_response = last_msg.content

                # Also capture tools from tool nodes explicitly if needed
                if "tools" in node and "messages" in output:
                    for tool_msg in output["messages"]:
                        name = getattr(tool_msg, "name", None)
                        if name and name not in tools_called:
                            tools_called.append(name)

        # Fallback if response is empty
        if not final_response:
            final_response = "Task processed, but no text output was generated."

        return ChatResponse(
            response=final_response,
            agent=agent_used,
            tool_calls=tools_called
        )

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return ChatResponse(
            response=f"System Error: {str(e)}",
            agent="DEFAULT",
            tool_calls=[]
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000,reload=True)