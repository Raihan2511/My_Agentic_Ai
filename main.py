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
agent_prompt = PromptTemplate(
    input_variables=["role", "goal", "tools", "user_input"],
    template="""
You are a {role} AI agent.

Your Goal:
{goal}

Available Tools:
{tools}

Instructions:
1. Think through the problem step-by-step before answering.
2. If tools are available, decide if one should be used.
3. Clearly explain intermediate reasoning only if needed.
4. Always provide a **Final Answer** section with your solution.

User Request:
{user_input}

Begin reasoning now.
"""
)


