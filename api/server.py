from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from multi_agent import app as agent_app

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserMessage(BaseModel):
    message: str

@app.post("/chat")
async def chat_with_agent(payload: UserMessage):
    state = {"messages": [("user", payload.message)]}
    final_response = ""
    for event in agent_app.stream(state):
        for node, output in event.items():
            if "agent" in node:
                msg = output["messages"][-1]
                if not getattr(msg, "tool_calls", None):
                    final_response = msg.content
    return {"response": final_response}


