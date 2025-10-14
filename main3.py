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
# <-- CHANGE 1 START: Import both toolkits ---
from Backend.Tools.email.email_toolkit import EmailToolkit
from Backend.Tools.university.university_toolkit import UniversityToolkit
# <-- CHANGE 1 END ---

# --- Load Environment Variables ---
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")

if not google_api_key:
    raise ValueError("GOOGLE_API_KEY not found in .env file. Please set it.")


# --- 1. Load and Prepare Your Custom Tools ---
# <-- CHANGE 2 START: Load tools from both toolkits and combine them ---
print("Loading tools...")
email_toolkit = EmailToolkit()
university_toolkit = UniversityToolkit()

# Combine the lists of tools from both toolkits
custom_email_tools = email_toolkit.get_tools()
custom_university_tools = university_toolkit.get_tools()
all_custom_tools = custom_email_tools + custom_university_tools
# <-- CHANGE 2 END ---

langchain_tools = []
# Loop over the combined list of all tools
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
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", google_api_key=google_api_key)
llm_with_tools = llm.bind_tools(langchain_tools)


# --- 3. Define the Prompt Template ---
# <-- CHANGE 3 START: Enhance the system prompt with the new procedure ---
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an advanced, autonomous university administration assistant. Your primary goal is to process incoming emails according to specific procedures. "
            "You must be autonomous and complete all steps of a task without asking for confirmation. "
            
            "\n\nHERE ARE YOUR TOOLS AND PROCEDURES:"
            "\n- Use the 'Email Toolkit' for general email tasks like reading and sending."
            "\n- Use the 'University Toolkit' for specialized tasks related to student and course data."
            
            "\n\n**CRITICAL PROCEDURE: Course Registration Emails**"
            "\nWhen you are asked to process a course registration email, you MUST follow these steps in this exact order:"
            "\n1. First, use the `Read_Email` tool to get the full content of the email."
            "\n2. From the email content, extract the necessary information (student name, course ID, query text)."
            "\n3. Second, use the `Invoke_University_AI_Model` tool with the extracted information to get the processed data as XML."
            "\n4. Third, use the `Import_Data_to_Unitime` tool, passing the XML you received from the previous step."
            "\n5. Finally, confirm that the entire process was successful."
        ),
        ("placeholder", "{messages}"),
    ]
)
# <-- CHANGE 3 END ---


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
app = workflow.compile()


# --- 9. Run the Agent ---
if __name__ == "__main__":
    # <-- CHANGE 4 START: Update the input to trigger the new workflow ---
    # This new input is designed to match the "Course Registration" procedure in the system prompt.
    human_input = "There is a new student course registration email in the INBOX. Please process it and update the university system accordingly."
    # <-- CHANGE 4 END ---

    print(f"\nExecuting task: '{human_input}'\n")

    for event in app.stream({"messages": [("user", human_input)]}):
        for node, output in event.items():
            print(f"--- Output from node: '{node}' ---")
            print(output)
            print("--- End of Node Output ---\n")