import os
from dotenv import load_dotenv
from typing import List

# --- LangChain Imports ---
from langchain_core.messages import BaseMessage
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
from Backend.Tools.Auto_sync.auto_sync_toolkit import AutoSyncToolkit
from Backend.Tools.rag_system.rag_toolkit import RAGToolkit


# ===============================
# 1. ENV + BASE LLM
# ===============================

load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    raise ValueError("GOOGLE_API_KEY not found in .env file. Please set it.")

# Base LLM factory
def make_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        google_api_key=google_api_key,
    )


# ===============================
# 2. LOAD TOOLKITS
# ===============================

print("Loading toolkits...")
email_toolkit = EmailToolkit()
university_toolkit = UniversityToolkit()
auto_sync_toolkit = AutoSyncToolkit()
rag_toolkit = RAGToolkit()
print("Toolkits loaded.")


# Helper: convert your custom tools to LangChain StructuredTool objects
def to_langchain_tools(tool_list):
    lc_tools = []
    for tool in tool_list:
        lc_tools.append(
            StructuredTool.from_function(
                name=tool.name,
                description=tool.description,
                func=tool._execute,
                args_schema=tool.args_schema,
            )
        )
    return lc_tools


# ===============================
# 3. GROUP TOOLS PER WORKFLOW/AGENT
# ===============================

# TEST → Export_Timetable (Fixed Name)
test_tools_raw = [
    t for t in auto_sync_toolkit.get_tools()
    if t.name == "Export_Timetable"  # <--- FIXED: Matches your tool definition
]

# READ → Query_Student_Timetable
read_tools_raw = [
    t for t in rag_toolkit.get_tools()
    if t.name == "Query_Student_Timetable"
]

# WRITE → Read_Email + Add_Offering_to_Batch_File + Query_Student_Timetable
write_tools_raw = [
    t for t in email_toolkit.get_tools()
    if t.name == "Read_Email"
] + [
    t for t in university_toolkit.get_tools()
    if t.name == "Add_Offering_to_Batch_File"
] + [
    t for t in rag_toolkit.get_tools()
    if t.name == "Query_Student_Timetable"
]


# SYNC → Export_Timetable (Fixed Name) + Refresh_RAG_Database
sync_tools_raw = [
    t for t in auto_sync_toolkit.get_tools()
    if t.name == "Export_Timetable"  # <--- FIXED: Matches your tool definition
] + [
    t for t in rag_toolkit.get_tools()
    if t.name == "Refresh_RAG_Database"
]

# IMPORT → Import_Batch_File_to_Unitime
import_tools_raw = [
    t for t in university_toolkit.get_tools()
    if t.name == "Import_Batch_File_to_Unitime"
]

# Convert to LangChain tools
test_tools_lc = to_langchain_tools(test_tools_raw)
read_tools_lc = to_langchain_tools(read_tools_raw)
write_tools_lc = to_langchain_tools(write_tools_raw)
sync_tools_lc = to_langchain_tools(sync_tools_raw)
import_tools_lc = to_langchain_tools(import_tools_raw)

print("\n--- Tools per agent ---")
print("TEST tools:", [t.name for t in test_tools_lc])
print("READ tools:", [t.name for t in read_tools_lc])
print("WRITE tools:", [t.name for t in write_tools_lc])
print("SYNC tools:", [t.name for t in sync_tools_lc])
print("IMPORT tools:", [t.name for t in import_tools_lc])
print("------------------------\n")


# ===============================
# 4. ROUTER AGENT
# ===============================

router_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a router that decides which workflow should handle the user's request.\n"
            "You MUST respond with exactly one word from this list:\n"
            "TEST, READ, WRITE, SYNC, IMPORT.\n\n"
            "Rules:\n"
            "- TEST: user says 'test export', 'test selenium', or wants to test the export bot.\n"
            "- READ: user asks about class times, locations, instructors, or timetable questions.\n"
            "- WRITE: user wants to **add**, **update**, or **modify** a class/offering or process inbox emails.\n"
            "- SYNC: user says 'run the sync', 'refresh the database', or 'run the auto-sync'.\n"
            "- IMPORT: user says 'import the batch file', 'run the import', or 'push batch data to unitime'.\n\n"
            "If unsure, choose the closest match.\n"
            "Again, output ONLY one of: TEST, READ, WRITE, SYNC, IMPORT."
        ),
        ("user", "{input}"),
    ]
)

router_llm = make_llm()
router_chain = router_prompt | router_llm


# ===============================
# 5. WORKFLOW AGENTS (PROMPTS + CHAINS)
# ===============================

# --- TEST Agent ---
test_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are the TEST agent. Your job is to test the export/selenium workflow.\n"
            "When the user asks to 'test export' or 'test selenium', you MUST:\n"
            "1. Call the `Export_Timetable` tool.\n"
            "2. Report the result clearly to the user.\n"
        ),
        ("placeholder", "{messages}"),
    ]
)
test_llm = make_llm().bind_tools(test_tools_lc)
test_chain = test_prompt | test_llm


# --- READ Agent ---
read_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are the READ agent for a university timetable assistant.\n"
            "Your job is to answer student questions about class times, locations, instructors, etc.\n"
            "You MUST use the `Query_Student_Timetable` tool whenever needed to answer the question.\n"
            "Be accurate and concise in your final answer.\n"
        ),
        ("placeholder", "{messages}"),
    ]
)
read_llm = make_llm().bind_tools(read_tools_lc)
read_chain = read_prompt | read_llm


# --- WRITE Agent ---
write_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are the WRITE agent for university admin tasks. You manage adding and modifying offerings in the local batch file.\n\n"
            "TOOLS:\n"
            "- `Read_Email`: Fetches a list of recent emails and their contents.\n"
            "- `Add_Offering_to_Batch_File`: Processes natural language (from an email or direct request) and either **appends (insert)** or **finds and replaces (update)** the corresponding XML block in **unitime_batch.xml**.\n"
            "- `Query_Student_Timetable`: Used to look up existing course data *before* an update.\n\n"
            "WORKFLOW 2: WRITE (Admin Task)\n"
            
            "\n-- NEW INSERTIONS --"
            "If the user gives you a request for a *new* course or preference (e.g., 'Create a new class...', 'Add an instructor preference...'):\n"
            "1. Call the `Add_Offering_to_Batch_File` tool. Pass the user's natural language command as the `query_text`.\n"
            "2. Report the success message.\n\n"
            
            "\n-- MODIFICATIONS/UPDATES (New Multi-Step Flow) --"
            "If the user explicitly asks to **'Update'** or **'Modify'** a course (e.g., 'Update the capacity of DRL 101'):\n"
            "1. **First, Query Existing Data:** Call the `Query_Student_Timetable` tool using the course name/number to retrieve the existing data.\n"
            "2. **Second, Wait for Confirmation:** Based on the query result, you MUST then ask the user to specify the **exact field and new value** they want to change (e.g., 'I found DRL 101 has title X. What is the new title?').\n"
            "3. **Third, Execute Modification:** Once the user provides the specific change, call the `Add_Offering_to_Batch_File` tool with the *full, specific update command*.\n"
            "4. **Report:** Report the success message.\n\n"
            
            "If the user asks to 'process the inbox' or 'add a new class' from an email (can be insert or update):\n"
            "1. Use `Read_Email` to find the relevant email(s).\n"
            "2. Call the `Add_Offering_to_Batch_File` tool and pass the full email body as `query_text`.\n"
            "3. Report the success status.\n"
        ),
        ("placeholder", "{messages}"),
    ]
)
write_llm = make_llm().bind_tools(write_tools_lc)
write_chain = write_prompt | write_llm


# --- SYNC Agent ---
sync_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are the SYNC agent. You run the full auto-sync for the timetable system.\n\n"
            "TOOLS:\n"
            "- `Export_Timetable`: Selenium bot to export the current timetable as CSV.\n"
            "- `Refresh_RAG_Database`: Rebuilds the RAG database from the exported CSV.\n\n"
            "WORKFLOW 3: SYNC (The Full Auto-Sync)\n"
            "If the user asks to 'run the sync', 'refresh the database', or 'run the auto-sync':\n"
            "You MUST perform these steps in order:\n"
            "1. Call `Export_Timetable` to get the currently active schedule.\n"
            "2. AFTER step 1 succeeds, call `Refresh_RAG_Database`.\n"
            "3. Finally, inform the user that the sync is complete and the chatbot is updated.\n\n"
            "You may need multiple tool calls in sequence. Make sure to inspect previous tool results.\n"
        ),
        ("placeholder", "{messages}"),
    ]
)
sync_llm = make_llm().bind_tools(sync_tools_lc)
sync_chain = sync_prompt | sync_llm


# --- IMPORT Agent ---
import_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are the IMPORT agent for university admin tasks.\n\n"
            "Your job is to import the local batch file into UniTime.\n\n"
            "TOOLS:\n"
            "- `Import_Batch_File_to_Unitime`: Imports the pending batch file into UniTime.\n\n"
            "WORKFLOW 4: IMPORT BATCH (Admin Task)\n"
            "If the user asks to 'import the batch file', 'run the import', or 'push batch data to unitime':\n"
            "1. You MUST call the `Import_Batch_File_to_Unitime` tool.\n"
            "2. Report the result of the import clearly to the user.\n"
        ),
        ("placeholder", "{messages}"),
    ]
)
import_llm = make_llm().bind_tools(import_tools_lc)
import_chain = import_prompt | import_llm


# ===============================
# 6. LANGGRAPH STATE + NODES
# ===============================

class AgentState(MessagesState):
    """State: just a list of LangChain messages."""
    pass


def make_agent_node(chain):
    """Wrap a chain so it fits LangGraph node signature."""
    def _node(state: AgentState):
        response = chain.invoke({"messages": state["messages"]})
        return {"messages": [response]}
    return _node


# Agent nodes
test_agent_node = make_agent_node(test_chain)
read_agent_node = make_agent_node(read_chain)
write_agent_node = make_agent_node(write_chain)
sync_agent_node = make_agent_node(sync_chain)
import_agent_node = make_agent_node(import_chain)

# Tool nodes
test_tool_node = ToolNode(test_tools_lc)
read_tool_node = ToolNode(read_tools_lc)
write_tool_node = ToolNode(write_tools_lc)
sync_tool_node = ToolNode(sync_tools_lc)
import_tool_node = ToolNode(import_tools_lc)


# Router node itself doesn't change messages; routing is done via route_decision
def router_node(state: AgentState):
    return {"messages": state["messages"]}


def route_decision(state: AgentState) -> str:
    """Decide which workflow (TEST/READ/WRITE/SYNC/IMPORT) to route to."""
    last_message = state["messages"][-1]
    user_text = getattr(last_message, "content", str(last_message))
    route = router_chain.invoke({"input": user_text})
    choice = route.content.strip().upper()
    if choice not in ["TEST", "READ", "WRITE", "SYNC", "IMPORT"]:
        choice = "READ"  # default fallback
    print(f"[Router] Routing to: {choice}")
    return choice


def should_continue(state: AgentState) -> str:
    """Check if last LLM response has tool calls."""
    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "continue"
    return "end"


# ===============================
# 7. BUILD THE GRAPH
# ===============================

workflow = StateGraph(AgentState)

# Router
workflow.add_node("router", router_node)
workflow.set_entry_point("router")

# Agent + tools nodes
workflow.add_node("test_agent", test_agent_node)
workflow.add_node("test_tools", test_tool_node)

workflow.add_node("read_agent", read_agent_node)
workflow.add_node("read_tools", read_tool_node)

workflow.add_node("write_agent", write_agent_node)
workflow.add_node("write_tools", write_tool_node)

workflow.add_node("sync_agent", sync_agent_node)
workflow.add_node("sync_tools", sync_tool_node)

workflow.add_node("import_agent", import_agent_node)
workflow.add_node("import_tools", import_tool_node)

# Router → appropriate workflow
workflow.add_conditional_edges(
    "router",
    route_decision,
    {
        "TEST": "test_agent",
        "READ": "read_agent",
        "WRITE": "write_agent",
        "SYNC": "sync_agent",
        "IMPORT": "import_agent",
    },
)

# For each workflow agent, loop Agent ↔ Tools until no more tool calls
for agent_name, tools_name in [
    ("test_agent", "test_tools"),
    ("read_agent", "read_tools"),
    ("write_agent", "write_tools"),
    ("sync_agent", "sync_tools"),
    ("import_agent", "import_tools"),
]:
    workflow.add_conditional_edges(
        agent_name,
        should_continue,
        {"continue": tools_name, "end": END},
    )
    workflow.add_edge(tools_name, agent_name)

app = workflow.compile()


# ===============================
# 8. CLI LOOP
# ===============================

if __name__ == "__main__":
    print("✅ Multi-Agent University Assistant Initialized.")
    print("---")
    print("Examples:")
    print("  'Where is my CG 101 class?'            -> READ")
    print("  'Process the new request in the inbox.'-> WRITE")
    print("  'Add a new offering: CS 4500 ...'      -> WRITE (Insert)")
    print("  'Update the capacity for DRL 101 to 45.'-> WRITE (Multi-Step Update)")
    print("  'Run the full auto-sync now.'          -> SYNC")
    print("  'Import the batch file.'               -> IMPORT")
    print("  'Test export with selenium.'           -> TEST")
    print("  'quit' to exit.")
    print("---")

    while True:
        human_input = input("\n> ")
        if human_input.lower() in ["quit", "exit"]:
            print("Shutting down...")
            break

        print("\n--- EXECUTING ---")
        state = {"messages": [("user", human_input)]}

        for event in app.stream(state):
            for node, output in event.items():
                # Agent messages
                if "agent" in node and output.get("messages"):
                    last_msg = output["messages"][-1]
                    if getattr(last_msg, "tool_calls", None):
                        print(f"--- [{node}]: Calling {len(last_msg.tool_calls)} tool(s)...")
                    else:
                        print(f"--- [{node}]: {last_msg.content}")

                # Tool results
                if "tools" in node and output.get("messages"):
                    for tool_msg in output["messages"]:
                        name = getattr(tool_msg, "name", "UnknownTool")
                        content = getattr(tool_msg, "content", "")
                        print(f"--- [Tool Result: {name}]: {content}")

        print("--- TASK COMPLETE. Awaiting next command. ---")