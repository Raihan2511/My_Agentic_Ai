# main3.py

import sys
import os
from dotenv import load_dotenv
from typing import List

# --- LangChain Imports ---
from langchain_core.messages import BaseMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import StructuredTool

# --- LangGraph Imports ---
from langgraph.graph import StateGraph, END
from langgraph.graph.message import MessagesState
from langgraph.prebuilt import ToolNode

# --- Your Custom Toolkit Imports ---
from Backend.Tools.email.email_toolkit import EmailToolkit
from Backend.Tools.university.university_toolkit import UniversityToolkit

# --- Load Environment Variables ---
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")

if not google_api_key:
    raise ValueError("GOOGLE_API_KEY not found in .env file. Please set it.")


# --- 1. Load and Prepare Your Custom Tools ---
# (No changes here)
print("Loading tools...")
email_toolkit = EmailToolkit()
university_toolkit = UniversityToolkit()

custom_email_tools = email_toolkit.get_tools()
custom_university_tools = university_toolkit.get_tools()
all_custom_tools = custom_email_tools + custom_university_tools

langchain_tools = []
for tool in all_custom_tools:
    langchain_tools.append(
        StructuredTool.from_function(
            name=tool.name,
            description=tool.description,
            func=tool._execute,
            args_schema=tool.args_schema
        )
    )
print("--- Agent Tools Loaded ---")
for t in langchain_tools:
    print(f"- {t.name}")
print("--------------------------")


# --- 2. Initialize the Language Model and Bind Tools ---
# (No changes here)
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", google_api_key=google_api_key)
llm_with_tools = llm.bind_tools(langchain_tools)


# --- 3. Define the Prompt Template ---
# <-- THIS ENTIRE SECTION IS REPLACED ---
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an advanced, autonomous university administration assistant. You have two main workflows:"
            "\n1. Processing and queueing new requests."
            "\n2. Importing the entire batch."
            
            "\n\nHERE ARE YOUR TOOLS AND PROCEDURES:"
            "\n- 'Read_Email': Fetches a list of recent emails."
            "\n- 'Add_Offering_to_Batch_File': Processes a *single* email body and inserts its XML into a persistent batch file. This does NOT import."
            "\n- 'Import_Batch_File_to_Unitime': Imports the *entire batch* of previously queued items into UniTime. This resets the batch file on success."
            
            "\n\n**WORKFLOW 1: Adding to Batch File**"
            "\nWhen you are asked to process a new email (e.g., 'process the inbox for a course request'):"
            "\n1. **Fetch Emails:** First, use the `Read_Email` tool."
            "\n2. **Find Target Email:** You must mentally loop through the list. Find the *first* email that is relevant to the user's task (e.g., 'adding course', 'instructor preference'). **You MUST ignore** all irrelevant emails."
            "\n3. **Handle Findings:**"
            "\n   - **IF** you find a relevant email: Pass its 'Message Body' to the `Add_Offering_to_Batch_File` tool."
            "\n   - **IF** you scan all emails and *none* are relevant: Your final response MUST be that you read the inbox but found no processable requests."
            "\n4. **Report:** After `Add_Offering_to_Batch_File` is successful, your *only* job is to report its success message (e.g., 'Success: The request has been added to the batch file.'). **Do NOT call the import tool.**"
            
            "\n\n**WORKFLOW 2: Importing the Batch File**"
            "\nWhen the user explicitly asks you to 'import the batch', 'run the import', or 'process the batch file':"
            "\n1. **Call Import Tool:** You MUST call the `Import_Batch_File_to_Unitime` tool. This tool takes no arguments."
            "\n2. **Report Result:** Report the final success or error message from the tool."
        ),
        ("placeholder", "{messages}"),
    ]
)
# <-- END OF PROMPT ---


# --- 4. Create the Agent Chain ---
# (No changes here)
agent_chain = prompt | llm_with_tools


# --- 5. Define the Graph's State ---
# (No changes here)
class AgentState(MessagesState):
    pass


# --- 6. Define the Graph's Nodes (The Steps) ---
# (No changes here)
def call_model(state: AgentState):
    """Calls the LLM to decide the next action."""
    response = agent_chain.invoke({"messages": state["messages"]})
    return {"messages": [response]}

tool_node = ToolNode(langchain_tools)


# --- 7. Define the Graph's Edges (The Logic) ---
# (No changes here)
def should_continue(state: AgentState) -> str:
    """Decides the next step after the LLM has been called."""
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "continue"
    else:
        return "end"

# --- 8. Assemble the Graph ---
# (No changes here)
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("action", tool_node)
workflow.set_entry_point("agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {"continue": "action", "end": END},
)
workflow.add_edge("action", "agent")
app = workflow.compile()

# --- 9. GENERATE THE DIAGRAM (Optional) ---
print("Generating graph diagram...")
try:
    with open("graph_diagram.png", "wb") as f:
        f.write(app.get_graph().draw_mermaid_png())
    print("✅ Graph diagram saved to 'graph_diagram.png'")
except Exception as e:
    print(f"❌ Failed to generate diagram. Is graphviz installed? Error: {e}")
# --- END OF NEW CODE ---


# # --- 10. Run the Agent ---
# # <-- THIS SECTION IS REPLACED ---
# if __name__ == "__main__":
    
#     # ---
#     # TEST WORKFLOW 1: Add a request to the batch file
#     # This will find the email and call 'Add_Offering_to_Batch_File'.
#     # The agent will stop after reporting "Success: The request has been added to the batch file."
#     # ---
#     human_input = "There is a request for adding course email in the INBOX. Please process it."
    
    
#     # ---
#     # TEST WORKFLOW 2: Import the batch file
#     # After you have queued one or more items, run the script again with this input:
#     # ---
#     # human_input = "All requests are in the file. Please import the batch file now."
#     # ---

#     print(f"\nExecuting task: '{human_input}'\n")

#     for event in app.stream({"messages": [("user", human_input)]}):
#         for node, output in event.items():
#             print(f"--- Output from node: '{node}' ---")
#             print(output)
#             print("--- End of Node Output ---\n")



# --- 10. Run the Agent ---
if __name__ == "__main__":
    
    # This input will trigger WORKFLOW 2
    human_input = "All requests are in the file. Please import the batch file now."
    
    print(f"\nExecuting task: '{human_input}'\n")

    for event in app.stream({"messages": [("user", human_input)]}):
        for node, output in event.items():
            print(f"--- Output from node: '{node}' ---")
            print(output)
            print("--- End of Node Output ---\n")