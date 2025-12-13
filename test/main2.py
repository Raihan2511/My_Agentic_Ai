# # Save this as main_langgraph.py
# import sys
# import os
# from dotenv import load_dotenv
# from typing import List, Annotated
# from langchain_core.messages import BaseMessage, ToolMessage
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain.tools import StructuredTool

# # --- LangGraph Imports ---
# from langgraph.graph import StateGraph, END
# from langgraph.graph.message import MessagesState # A convenient way to manage message history
# from langgraph.prebuilt import ToolNode

# # --- Your Custom Toolkit Imports ---
# from Backend.Tools.email.email_toolkit import EmailToolkit # Adjust path if necessary

# # --- Load Environment Variables ---
# load_dotenv()
# google_api_key = os.getenv("GOOGLE_API_KEY")

# if not google_api_key:
#     raise ValueError("GEMINI_API_KEY not found in .env file. Please set it.")


# # --- 1. Load and Prepare Your Custom Tools ---
# # This part is the same as before. We convert your tools to LangChain's format.
# email_toolkit = EmailToolkit()
# custom_email_tools = email_toolkit.get_tools()
# langchain_tools = []
# for tool in custom_email_tools:
#     langchain_tools.append(
#         StructuredTool.from_function(
#             name=tool.name,
#             description=tool.description,
#             func=tool._execute,
#             args_schema=tool.args_schema
#         )
#     )
# print("--- Agent Tools Loaded ---")
# for t in langchain_tools:
#     print(f"- {t.name}")
# print("--------------------------")


# # --- 2. Initialize the Language Model and Bind Tools ---
# llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", google_api_key=google_api_key)
# llm_with_tools = llm.bind_tools(langchain_tools)


# # --- 3. Define the Graph's State ---
# class AgentState(MessagesState):
#     pass

# # --- 4. Define the Graph's Nodes (The Steps) ---

# # The "Brain" Node
# def call_model(state: AgentState):
#     """Calls the LLM to decide the next action."""
#     messages = state["messages"]
#     response = llm_with_tools.invoke(messages)
#     # The response (which could be a tool call or a final answer) is added to the state
#     return {"messages": [response]}


# tool_node = ToolNode(langchain_tools)


# # --- 5. Define the Graph's Edges (The Logic) ---
# # Edges connect the nodes. A conditional edge acts like an IF/ELSE statement,
# # deciding which node to go to next based on the current state.

# def should_continue(state: AgentState) -> str:
#     """
#     This function decides the next step after the LLM has been called.
#     - If the LLM made a tool call, we go to the tool_node.
#     - If the LLM did not make a tool call, we are finished.
#     """
#     last_message = state["messages"][-1]
#     # Check if the last message contains tool calls
#     if last_message.tool_calls:
#         # If yes, we continue to the tool execution node
#         return "continue"
#     else:
#         # If no, we have our final answer and can end the process
#         return "end"

# # --- 6. Assemble the Graph ---
# # Now we wire all our nodes and edges together into a flowchart.

# # Create a new graph
# workflow = StateGraph(AgentState)

# # Add the "brain" node
# workflow.add_node("agent", call_model)
# # Add the "hands" node
# workflow.add_node("action", tool_node)

# # Set the entry point - the first node to be called
# workflow.set_entry_point("agent")

# # Add the conditional edge. After the "agent" node runs, the `should_continue`
# # function will be called to decide where to go next.
# workflow.add_conditional_edges(
#     "agent",
#     should_continue,
#     {
#         # If `should_continue` returns "continue", go to the "action" node.
#         "continue": "action",
#         # If `should_continue` returns "end", go to the special END node.
#         "end": END,
#     },
# )

# # Add a normal edge. After the "action" node (tool execution) runs, it
# # should always go back to the "agent" node so the brain can see the results.
# workflow.add_edge("action", "agent")

# # Compile the graph into a runnable application
# app = workflow.compile()


# # --- 7. Run the Agent ---
# if __name__ == "__main__":
#     human_input = "Read my first email from the INBOX folder and then send a  summary containing just content of it to 'ru241795@gmail.com' with the subject 'AI Summary'"
#     print(f"\nExecuting task: '{human_input}'\n")

#     # Use the .stream() method to see the output from each step as it happens
#     for event in app.stream({"messages": [("user", human_input)]}):
#         for node, output in event.items():
#             print(f"--- Output from node: '{node}' ---")
#             print(output)
#             print("--- End of Node Output ---\n")

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
from langgraph.graph.message import MessagesState # A convenient way to manage message history
from langgraph.prebuilt import ToolNode

# --- Your Custom Toolkit Imports ---
from Backend.Tools.email.email_toolkit import EmailToolkit # Adjust path if necessary

# --- Load Environment Variables ---
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")

if not google_api_key:
    raise ValueError("GOOGLE_API_KEY not found in .env file. Please set it.")


# --- 1. Load and Prepare Your Custom Tools ---
# This part remains the same. It correctly loads your custom tools.
email_toolkit = EmailToolkit()
custom_email_tools = email_toolkit.get_tools()
langchain_tools = []
for tool in custom_email_tools:
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


# --- 3. Define the Prompt Template (THE FIX) ---
# This is the crucial change. We define the powerful system prompt that tells the
# agent to be autonomous and complete multi-step tasks without asking for confirmation.
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an autonomous email assistant. Your goal is to complete the user's request fully, using the available tools in sequence as needed. "
            "If a request involves multiple steps (like reading and then sending an email), you must execute all steps to complete the entire task. "
            "Do not stop and ask for confirmation unless the user's request is ambiguous."
        ),
        # The placeholder "{messages}" will be dynamically filled with the conversation history.
        ("placeholder", "{messages}"),
    ]
)

# --- 4. Create the Agent Chain ---
# We chain the prompt and the LLM together. This ensures the system prompt is always used.
agent_chain = prompt | llm_with_tools


# --- 5. Define the Graph's State ---
# MessagesState is a convenient way to track the list of messages in the conversation.
class AgentState(MessagesState):
    pass


# --- 6. Define the Graph's Nodes (The Steps) ---

# The "Brain" Node - Modified to use the new agent_chain
def call_model(state: AgentState):
    """Calls the LLM to decide the next action."""
    # The `agent_chain` formats the messages with the system prompt before calling the LLM.
    response = agent_chain.invoke({"messages": state["messages"]})
    # The response (which could be a tool call or a final answer) is added to the state
    return {"messages": [response]}

# The "Hands" Node - No changes needed here
tool_node = ToolNode(langchain_tools)


# --- 7. Define the Graph's Edges (The Logic) ---
# This logic correctly checks if the LLM's last response was a tool call or a final answer.
def should_continue(state: AgentState) -> str:
    """
    Decides the next step after the LLM has been called.
    - If the LLM made a tool call, we go to the tool_node.
    - If the LLM did not make a tool call, we are finished.
    """
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "continue"
    else:
        return "end"

# --- 8. Assemble the Graph ---
# Wiring all our nodes and edges together into a flowchart.
workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("action", tool_node)

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "action",
        "end": END,
    },
)

workflow.add_edge("action", "agent")

# Compile the graph into a runnable application
app = workflow.compile()


# --- 9. Run the Agent ---
if __name__ == "__main__":
    # The multi-step user request
    human_input = "Read my first email from the INBOX folder and then send a summary containing just the content of it to 'ru241795@gmail.com' with the subject 'AI Summary'"
    print(f"\nExecuting task: '{human_input}'\n")

    # Use the .stream() method to see the output from each step as it happens
    # The input is a dictionary where the key "messages" matches the placeholder in our prompt
    for event in app.stream({"messages": [("user", human_input)]}):
        for node, output in event.items():
            print(f"--- Output from node: '{node}' ---")
            print(output)
            print("--- End of Node Output ---\n")