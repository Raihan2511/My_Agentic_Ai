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
parser=PydanticOutputParser(pydantic_object=Mymodel)
from langchain.prompts import PromptTemplate




agent_prompt = PromptTemplate(
    input_variables=[
        "system",
        "chat_history",
        "human_input",
        "agent_scratchpad"
    ],
    template="""
[System]
{system}

--- Chat History (most recent last) ---
{chat_history}

--- Human Query ---
{human_input}

--- Agent Scratchpad (planning / tool calls — keep private) ---
{agent_scratchpad}

Instructions:
1. Think step-by-step before answering.
2. If a tool should be used, call it and record results into the scratchpad.
3. Only reveal intermediate reasoning in the response if explicitly requested by the user.
4. Always finish with a clear **Final Answer** section.

Begin reasoning now.
"""
)

agent=create_tool_calling_agent(
    llm=llm,
    prompt=agent_prompt,
    tools=[]
)

agent_executor = AgentExecutor(
    agent=agent,
    tools=[],
    verbose=True
)
# --- Invoking the Agent (Corrected Code) ---

# This is the string that will be passed to the {system} variable in the prompt.
system_prompt_content = "You are a helpful and friendly AI assistant."

# Now, we invoke the agent. Notice how the keys in this dictionary
# EXACTLY match the 'input_variables' in the PromptTemplate.
raw_response = agent_executor.invoke({
    # The key is 'human_input', not 'query'
    "human_input": "What is the capital of France?",
    
    # We provide the content for the 'system' variable
    "system": system_prompt_content,
    
    # For a new conversation, 'chat_history' can be an empty list.
    # The agent framework often expects a list of messages here.
    "chat_history": []
})

print("\n\n--- FINAL RESPONSE ---")
print(raw_response)
