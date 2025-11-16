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
# ALL TOOLKITS ARE NOW LOADED
from Backend.Tools.email.email_toolkit import EmailToolkit
from Backend.Tools.university.university_toolkit import UniversityToolkit
from Backend.Tools.Auto_sync.auto_sync_toolkit import AutoSyncToolkit
from Backend.Tools.rag_system.rag_toolkit import RAGToolkit

# --- Load Environment Variables ---
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")

if not google_api_key:
    raise ValueError("GOOGLE_API_KEY not found in .env file. Please set it.")


# --- 1. Load and Prepare ALL Custom Tools ---
print("Loading tools...")
email_toolkit = EmailToolkit()
university_toolkit = UniversityToolkit()
auto_sync_toolkit = AutoSyncToolkit()
rag_toolkit = RAGToolkit()

# Combine all tools from all toolkits
all_custom_tools = (
    email_toolkit.get_tools() +
    university_toolkit.get_tools() +
    auto_sync_toolkit.get_tools() +
    rag_toolkit.get_tools()
)

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
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", google_api_key=google_api_key)
llm_with_tools = llm.bind_tools(langchain_tools)


# --- 3. Define the Master Router Prompt ---
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are the Master Control Agent for a university. You have three main workflows:"
            "\n1. READ (Student Queries): Answer questions about schedules."
            "\n2. WRITE (Admin Tasks): Add new data to the system via email or NLP."
            "\n3. SYNC (Admin Task): Run the full, automated sync process."
            
            "\n\nHERE ARE YOUR TOOLS AND PROCEDURES:"
            "\n- 'Read_Email': Fetches a list of recent emails."
            "\n- 'Add_Offering_to_Batch_File': Processes NLP text or email and adds to the batch file."
            "\n- 'Import_Batch_File_to_Unitime': Imports the pending batch file to UniTime."
            "\n- 'Run_Solver_and_Export': Selenium bot to run the solver and export the CSV."
            "\n- 'Refresh_RAG_Database': Rebuilds the RAG database from the exported CSV."
            "\n- 'Query_Student_Timetable': Answers a student's question using RAG."
            
            "\n\n**WORKFLOW 1: READ (Student Query)**"
            "\nIf the user asks a question about class times, locations, or instructors (e.g., 'Where is my class?', 'Who teaches CS101?'):"
            "\n1. You MUST use the `Query_Student_Timetable` tool."
            "\n2. Report the answer directly to the user."
            
            "\n\n**WORKFLOW 2: WRITE (Admin Task)**"
            "\nIf the user asks to 'process the inbox' or 'add a new class' from an email:"
            "\n1. **Fetch Email:** Use `Read_Email` to find the relevant email."
            "\n2. **Add to Batch:** Pass the *email body* to the `Add_Offering_to_Batch_File` tool."
            "\n3. **Report:** Report the success message (e.g., 'Success: Added to batch.')."
            
            "\nIf the user gives you a *new* request directly (e.g., 'Create a new class...'):"
            "\n1. **Add to Batch:** Pass the user's *natural language command* to the `Add_Offering_to_Batch_File` tool."
            "\n2. **Report:** Report the success message."
            
            "\n\n**WORKFLOW 3: SYNC (The Full Auto-Sync)**"
            "\nIf the user explicitly asks to 'run the sync', 'refresh the database', or 'run the auto-sync':"
            "\nThis is a multi-step process. You MUST call these tools in this *exact* order:"
            "\n1. First, call `Import_Batch_File_to_Unitime` to import any pending changes."
            "\n2. Second, *after* step 1 is successful, call `Run_Solver_and_Export`."
            "\n3. Third, *after* step 2 is successful, call `Refresh_RAG_Database`."
            "\n4. Finally, report that the full sync is complete and the chatbot is updated."
        ),
        ("placeholder", "{messages}"),
    ]
)
# <-- END OF PROMPT ---


# --- 4. Create the Agent Chain ---
agent_chain = prompt | llm_with_tools


# --- 5. Define the Graph's State ---
class AgentState(MessagesState):
    pass


# --- 6. Define the Graph's Nodes (The Steps) ---
def call_model(state: AgentState):
    """Calls the LLM to decide the next action."""
    response = agent_chain.invoke({"messages": state["messages"]})
    return {"messages": [response]}

tool_node = ToolNode(langchain_tools)


# --- 7. Define the Graph's Edges (The Logic) ---
def should_continue(state: AgentState) -> str:
    """Decides the next step after the LLM has been called."""
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "continue"
    else:
        return "end"

# --- 8. Assemble the Graph ---
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


# --- 9. Run the Agent (NEW: Controller Loop) ---
if __name__ == "__main__":
    
    app = workflow.compile()
    
    print("✅ Master Agent Initialized. Ready for commands.")
    print("---")
    print("Examples:")
    print("  'Where is my CG 101 class?'          (Workflow 1: RAG Query)")
    print("  'Process the new request in the inbox.' (Workflow 2: Write from Email)")
    print("  'Run the full auto-sync now.'         (Workflow 3: Sync)")
    print("  'quit' to exit.")
    print("---")

    while True:
        human_input = input("\n> ")
        if human_input.lower() in ["quit", "exit"]:
            print("Shutting down...")
            break
            
        print(f"\n--- EXECUTING ---")
        
        state = {"messages": [("user", human_input)]}
        
        for event in app.stream(state):
            for node, output in event.items():
                # Print agent actions
                if node == "agent" and output.get("messages"):
                    last_msg = output["messages"][-1]
                    if last_msg.tool_calls:
                        print(f"--- [Agent]: Calling {len(last_msg.tool_calls)} tool(s)...")
                    else:
                        print(f"--- [Agent]: {last_msg.content}")
                
                # Print tool results
                if node == "action":
                    for tool_msg in output["messages"]:
                        print(f"--- [Tool Result: {tool_msg.name}]: {tool_msg.content}")
        
        print("--- TASK COMPLETE. Awaiting next command. ---")