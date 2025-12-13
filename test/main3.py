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
# <-- THIS IS THE MAIN CHANGE ---
# prompt = ChatPromptTemplate.from_messages(
#     [
#         (
#             "system",
#             "You are an advanced, autonomous university administration assistant. Your primary goal is to process incoming emails according to specific procedures. "
#             "You must be autonomous and complete all steps of a task without asking for confirmation."
            
#             "\n\nHERE ARE YOUR TOOLS AND PROCEDURES:"
#             "\n- Use the 'Email Toolkit' for general email tasks like reading and sending."
#             "\n- Use the 'University Toolkit' for specialized tasks related to student and course data."
            
#             "\n\n**CRITICAL PROCEDURE: Processing University Emails**"
#             "\nWhen you are asked to process an email, you MUST follow these steps in this exact order:"
#             "\n1. First, use the `Read_Email` tool to get the full content of the email."
#             "\n2. Second, pass the *entire* email content (as the 'query_text') to the `Invoke_University_AI_Model` tool. This tool will classify the email and attempt to generate XML."
            
#             "\n\n**VALIDATION STEP (CRITICAL!):**"
#             "\n3. After you get the response from `Invoke_University_AI_Model`, you MUST inspect it."
#             "\n   - **IF** the response is valid XML (e.g., it starts with '<'), then proceed to the next step."
#             "\n   - **IF** the response is an **error message** (e.g., it starts with 'Error: Query classified as Other'), you MUST **STOP** immediately. Do NOT try to import the data. Your final response should state that the email was read but was not a processable administrative task, and include the error message."
            
#             "\n\n**FINAL STEPS (Only if validation passed):**"
#             "\n4. Third, use the `Import_Data_to_Unitime` tool, passing the XML you received."
#             "\n5. Finally, confirm that the entire process was successful."
#         ),
#         ("placeholder", "{messages}"),
#     ]
# )

# --- 3. Define the Prompt Template ---

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an advanced, autonomous university administration assistant. You have two main workflows:"
            "\n1. Processing and queueing new requests."
            "\n2. Importing the entire queue."
            
            "\n\nHERE ARE YOUR TOOLS AND PROCEDURES:"
            "\n- 'Read_Email': Fetches a list of recent emails."
            "\n- 'Add_Offering_to_Queue': Processes a *single* email body and adds its XML to a batch file. This does NOT import."
            "\n- 'Import_Queue_to_Unitime': Imports the *entire batch* of previously queued items into UniTime."
            
            "\n\n**WORKFLOW 1: Adding to Queue**"
            "\nWhen you are asked to process a new email (e.g., 'process the inbox for a course request'):"
            "\n1. **Fetch Emails:** First, use the `Read_Email` tool."
            "\n2. **Find Target Email:** You must mentally loop through the list. Find the *first* email that is relevant to the user's task (e.g., 'adding course', 'instructor preference'). **You MUST ignore** all irrelevant emails."
            "\n3. **Handle Findings:**"
            "\n   - **IF** you find a relevant email: Pass its 'Message Body' to the `Add_Offering_to_Queue` tool."
            "\n   - **IF** you scan all emails and *none* are relevant: Your final response MUST be that you read the inbox but found no processable requests."
            "\n4. **Report:** After `Add_Offering_to_Queue` is successful, your *only* job is to report its success message (e.g., 'Success: The request has been added to the import queue.'). **Do NOT call the import tool.**"
            
            "\n\n**WORKFLOW 2: Importing the Queue**"
            "\nWhen the user explicitly asks you to 'import the queue', 'run the import', or 'process the batch':"
            "\n1. **Call Import Tool:** You MUST call the `Import_Queue_to_Unitime` tool. This tool takes no arguments."
            "\n2. **Report Result:** Report the final success or error message from the tool."
        ),
        ("placeholder", "{messages}"),
    ]
)
# <-- END OF PROMPT ---

# prompt = ChatPromptTemplate.from_messages(
#     [
#         (
#             "system",
#             "You are an advanced, autonomous university administration assistant. Your primary goal is to process incoming emails according to specific procedures. "
#             "You must be autonomous and complete all steps of a task without asking for confirmation."
            
#             "\n\nHERE ARE YOUR TOOLS AND PROCEDURES:"
#             "\n- 'Read_Email': Fetches a list of recent emails."
#             "\n- 'Invoke_University_AI_Model': Processes text to create XML."
#             "\n- 'Import_Data_to_Unitime': Imports XML data."
            
#             "\n\n**CRITICAL PROCEDURE: Processing University Emails**"
#             "\nWhen you are asked to process an email (e.g., 'process the inbox for a course request'), you MUST follow these steps in this exact order:"
            
#             "\n1. **Fetch Emails:** First, use the `Read_Email` tool. This tool will return a *list* of emails (as a JSON string)."
            
#             "\n2. **Find Target Email:** You must mentally loop through this list. Find the *first* email that is relevant to the user's task (e.g., 'adding course', 'instructor preference'). **You MUST ignore** all irrelevant emails like 'Security alert' or spam."
            
#             "\n3. **Handle Findings:**"
#             "\n   - **IF** you find a relevant email: Proceed to Step 4 with *only that one email's* 'Message Body'."
#             "\n   - **IF** you scan all emails and *none* are relevant: Your final response MUST be that you read the inbox but found no processable requests."
            
#             "\n4. **Process Target Email:** Pass the *entire 'Message Body'* of the single relevant email (as the 'query_text') to the `Invoke_University_AI_Model` tool."
            
#             "\n5. **Validate Response:**"
#             "\n   - **IF** the response is an **error message** (e.g., 'Error: Query classified as Other'), you MUST **STOP**. Your final response should state that the relevant email was read but was not a processable administrative task, and include the error message."
#             "\n   - **IF** the response is **valid XML** (e.g., starts with '<'), proceed to Step 6."
            
#             "\n6. **Import Data:** Call the `Import_Data_to_Unitime` tool, passing the XML you received as the 'unitime_xml_data' argument."
            
#             "\n7. **Final Confirmation:** After `Import_Data_to_Unitime` completes successfully, confirm that the entire process was successful."
#         ),
#         ("placeholder", "{messages}"),
#     ]
# )
# # <-- END OF PROMPT ---


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

# --- 9. GENERATE THE DIAGRAM (ADD THIS CODE) ---
print("Generating graph diagram...")
try:
    # This creates a PNG file named "graph_diagram.png" in your folder
    with open("graph_diagram.png", "wb") as f:
        f.write(app.get_graph().draw_mermaid_png())
    print("✅ Graph diagram saved to 'graph_diagram.png'")
except Exception as e:
    print(f"❌ Failed to generate diagram. Is graphviz installed? Error: {e}")
# --- END OF NEW CODE ---

# --- 10. Run the Agent ---
if __name__ == "__main__":
    
    # ---
    # TEST WORKFLOW 1: Add a request to the queue
    # This will find the email and call 'Add_Offering_to_Queue'.
    # The agent will stop after reporting "Success: The request has been added to the import queue."
    # ---
    human_input = "There is a request for adding course email in the INBOX. Please process it."
    
    
    # ---
    # TEST WORKFLOW 2: Import the queue
    # After you have queued one or more items, run the script again with this input:
    # ---
    # human_input = "All requests are queued. Please import the queue now."
    # ---

    print(f"\nExecuting task: '{human_input}'\n")

    # Clear the queue file before starting a new test run (optional but recommended)
    # try:
    #     with open("offering_queue.xml", "w") as f:
    #         f.write("")
    #     print("--- Cleared 'offering_queue.xml' for a fresh test run ---")
    # except Exception as e:
    #     print(f"--- Could not clear queue file: {e} ---")


    for event in app.stream({"messages": [("user", human_input)]}):
        for node, output in event.items():
            print(f"--- Output from node: '{node}' ---")
            print(output)
            print("--- End of Node Output ---\n")