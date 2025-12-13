import sys
import os

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_ROOT)


from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from llama_cpp import Llama
from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai
import os
from langchain.prompts import PromptTemplate
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.agents import create_tool_calling_agent,AgentExecutor
from langchain.prompts import PromptTemplate
from Backend.Tools.custom_tool.hello import print_hello_tool





load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

# model_path = "/home/sysadm/Music/HF_MODELS/models--TheBloke--Mistral-7B-Instruct-v0.1-GGUF/snapshots/731a9fc8f06f5f5e2db8a0cf9d256197eb6e05d1/mistral-7b-instruct-v0.1.Q5_K_M.gguf"

# llm= ChatOpenai(model="gpt-3.5-turbo")
# llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")

# USING LLAMA CPP
# llm = Llama(
#     model_path=model_path,
#     n_ctx=2048,       
#     n_gpu_layers=-1,  
#     verbose=True     
# )
# prompt = "<s>[INST] What is LLM model? [/INST]"
# output = llm(prompt, max_tokens=256)
# print(output["choices"][0]["text"].strip())

class Mymodel(BaseModel):
    topic:str
    content:str
    summary:str
    sources:list[str]
    tool_used:list[str]



# USING GOOGLE GENERATIVE AI
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-thinking-exp-1219",google_api_key=api_key)
# response=llm.invoke("Hello, how are you?")
# print(response)



# Get the parser and instructions
parser = PydanticOutputParser(pydantic_object=Mymodel)
format_instructions = parser.get_format_instructions()

agent_prompt = PromptTemplate(
    input_variables=["system", "chat_history", "human_input", "agent_scratchpad", "format_instructions"],
    template="""
[System]
{system}

--- Chat History ---
{chat_history}

--- Human Query ---
{human_input}

--- Agent Scratchpad ---
{agent_scratchpad}

You must format your final response as a JSON object that matches this schema:
{format_instructions}
"""
)

tools=[print_hello_tool]
agent = create_tool_calling_agent(
    llm=llm,
    prompt=agent_prompt.partial(format_instructions=format_instructions),
    tools=tools
)

agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# raw_response = agent_executor.invoke({
#     "human_input": "What is the essence of langgraph?",
#     "system": "You are a helpful and friendly AI assistant.",
#     "chat_history": []
# })

# raw_response = agent_executor.invoke({
#     "human_input": "Can you teel which tools are available in this system?",
#     "system": "You are a helpful and friendly AI assistant.",
#     "chat_history": []
# })

raw_response = agent_executor.invoke({
    "human_input": "Please use the hello tool to say hello.",
    "system": "You are a helpful and friendly AI assistant.",
    "chat_history": []
})


# print("\n--- RAW RESPONSE ---")
# print(raw_response)

# Now this works because output is valid JSON for Mymodel

try:
    structure_response = parser.parse(raw_response.get("output"))
    print("\n--- STRUCTURED RESPONSE ---")
    print(structure_response)
except Exception as e:
    print("\n--- ERROR PARSING RESPONSE ---")
    print(f"Error: {e}")
    print("Raw output was:")
    print(raw_response.get("output"))