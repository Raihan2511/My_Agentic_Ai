import os
import warnings
from dotenv import load_dotenv

# --- LangChain Imports ---
from langchain_core.prompts import ChatPromptTemplate
# CHANGED: Use OpenAI wrapper for Krutrim (since the API is OpenAI-compatible)
from langchain_openai import ChatOpenAI 
from langchain_core.tools import StructuredTool

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
# 0. SETUP & CONFIG
# ===============================

# Suppress Pydantic warnings about 'title' fields
warnings.filterwarnings("ignore", message="Key 'title' is not supported in schema")

load_dotenv()
krutrim_api_key = os.getenv("KRUTRIM_API_KEY")

if not krutrim_api_key:
    # Fallback/Check for the key
    print("⚠️ WARNING: KRUTRIM_API_KEY not found in .env file.")

# ===============================
# 1. BASE LLM FACTORY (KRUTRIM)
# ===============================

def make_llm():
    """
    Creates the LLM instance using Krutrim's OpenAI-compatible endpoint.
    Ref: https://cloud.olakrutrim.com/v1/chat/completions
    """
    return ChatOpenAI(
        # EXACT model name from your snippet
        model="Qwen3-Next-80B-A3B-Instruct", 
        
        # Point to Krutrim Cloud
        base_url="https://cloud.olakrutrim.com/v1", 
        
        api_key=krutrim_api_key,
        temperature=0.0
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

# TEST → Export_Timetable
test_tools_raw = [
    t for t in auto_sync_toolkit.get_tools()
    if t.name == "Export_Timetable"
]

# READ → Query_Student_Timetable
read_tools_raw = [
    t for t in rag_toolkit.get_tools()
    if t.name == "Query_Student_Timetable"
]

# WRITE → All admin tools (Email, Add, Update, Prefs, Factory)
write_tools_raw = [
    t for t in email_toolkit.get_tools()
    if t.name == "Read_Email"
] + [
    t for t in university_toolkit.get_tools()
    if t.name == "Add_Offering_to_Batch_File"
] + [
    t for t in university_toolkit.get_tools()
    if t.name == "Update_Course_File"
] + [
    t for t in rag_toolkit.get_tools()
    if t.name == "Query_Student_Timetable"
] + [
    t for t in university_toolkit.get_tools()
    if t.name == "Model_Prompt_Factory"
] + [
    t for t in university_toolkit.get_tools()
    if t.name == "Add_Preference_to_Batch"
]


# SYNC → Export_Timetable + Refresh_RAG_Database
sync_tools_raw = [
    t for t in auto_sync_toolkit.get_tools()
    if t.name == "Export_Timetable"
] + [
    t for t in rag_toolkit.get_tools()
    if t.name == "Refresh_RAG_Database"
]

# IMPORT → Import_File_to_Unitime
import_tools_raw = [
    t for t in university_toolkit.get_tools()
    if t.name == "Import_File_to_Unitime"
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
            "- IMPORT: user says 'import', 'import batch', 'import update', 'push data to unitime'.\n\n"
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
            "You are the WRITE agent. You are responsible for safe, accurate updates to course data.\n\n"
            
            "TOOLS:\n"
            "- `Read_Email`: Fetches recent emails.\n"
            "- `Add_Offering_to_Batch_File`: Appends NEW courses to 'unitime_batch.xml'.\n"
            "- `Add_Preference_to_Batch`: Appends NEW preferences to 'unitime_batch.xml'.\n"
            "- `Update_Course_File`: Overwrites 'unitime_update.xml' with modifications.\n"
            "- `Query_Student_Timetable`: Fetches current course details (Room, Time, Title, etc.).\n"
            "- `Model_Prompt_Factory`: Converts data into the EXACT training string for updates.\n\n"
            
            "WORKFLOW 1: UPDATING A COURSE\n"
            "If user wants to update/modify a course (e.g., 'Change title of DLCS 101'):\n"
            "1. **FETCH:** Call `Query_Student_Timetable` for the ID.\n"
            "2. **MERGE:** Compare Current vs. Request.\n"
            "3. **FORMAT:** Call `Model_Prompt_Factory`.\n"
            "4. **EXECUTE:** Call `Update_Course_File`.\n"
            "5. **REPORT:** Success.\n\n"
            
            "WORKFLOW 2: ADDING DATA\n"
            "- If adding a **COURSE**: Call `Add_Offering_to_Batch_File` with the request text.\n"
            "- If adding a **PREFERENCE**: Call `Add_Preference_to_Batch` with the request text.\n\n"
            
            "WORKFLOW 3: PROCESSING EMAILS (CRITICAL)\n"
            "If the user says 'Check email' or 'Process inbox':\n"
            "1. Call `Read_Email`.\n"
            "2. **FILTER STEP:** When you receive the list of emails, IGNORE any emails from 'Uber', 'Medium', 'LinkedIn', or obvious marketing/spam.\n"
            "3. **ACTION STEP:** Look strictly for Course/University related subjects (e.g. 'Request to Add', 'Update Class', 'Preference').\n"
            "   - Found a **NEW COURSE** request? -> IMMEDIATELY Call `Add_Offering_to_Batch_File` with that email's body.\n"
            "   - Found a **PREFERENCE** request? -> IMMEDIATELY Call `Add_Preference_to_Batch` with that email's body.\n"
            "   - Found an **UPDATE** request? -> Use Workflow 1 logic.\n"
            "4. **REPORT:** Tell the user exactly which email you processed and which you ignored."
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
            "3. Finally, inform the user that the sync is complete and the chatbot is updated.\n"
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
            "Your job is to import local XML files into UniTime.\n\n"
            "TOOLS:\n"
            "- `Import_File_to_Unitime`: Imports a specific XML file. You MUST specify the `filename` argument.\n\n"
            "WORKFLOW 4: IMPORT BATCH (Admin Task)\n"
            "1. If the user asks to 'import the batch file' or 'import new courses', call the tool with `filename='unitime_batch.xml'`.\n"
            "2. If the user asks to 'import the update' or 'apply the changes', call the tool with `filename='unitime_update.xml'`.\n"
            "3. If unsure, ask the user which file they want to import.\n"
            "4. Report the result clearly.\n"
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


# Router node itself doesn't change messages
def router_node(state: AgentState):
    return {"messages": state["messages"]}


def route_decision(state: AgentState) -> str:
    """Decide which workflow (TEST/READ/WRITE/SYNC/IMPORT) to route to."""
    last_message = state["messages"][-1]
    user_text = getattr(last_message, "content", str(last_message))
    try:
        route = router_chain.invoke({"input": user_text})
        choice = route.content.strip().upper()
    except Exception as e:
        print(f"Router Error: {e}. Defaulting to READ.")
        choice = "READ"
        
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
        {
            "continue": tools_name,
            "end": END
        },
    )
    workflow.add_edge(tools_name, agent_name)

app = workflow.compile()


# ===============================
# 8. CLI LOOP
# ===============================

if __name__ == "__main__":
    print("✅ Multi-Agent University Assistant Initialized (Krutrim Powered).")
    print("---")
    print("Examples:")
    print("  'Where is my CG 101 class?'             -> READ")
    print("  'Process the new request in the inbox.' -> WRITE (Emails -> Add/Update/Pref)")
    print("  'Add a new offering: CS 4500 ...'       -> WRITE (Insert Course)")
    print("  'Instructor Doe needs a projector.'     -> WRITE (Insert Preference)")
    print("  'Update DLCS 101 to title \"Advanced AI\"' -> WRITE (Update Course)")
    print("  'Run the full auto-sync now.'           -> SYNC")
    print("  'Import the batch file.'                -> IMPORT (Batch)")
    print("  'Import the update.'                    -> IMPORT (Update)")
    print("  'Test export with selenium.'            -> TEST")
    print("  'quit' to exit.")
    print("---")

    while True:
        human_input = input("\n> ")
        if human_input.lower() in ["quit", "exit"]:
            print("Shutting down...")
            break

        print("\n--- EXECUTING ---")
        state = {"messages": [("user", human_input)]}

        try:
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
        except Exception as e:
            print(f"❌ Execution Error: {e}")
            print("This may happen if the Krutrim API endpoint or Key is invalid.")
            
        print("--- TASK COMPLETE. Awaiting next command. ---")