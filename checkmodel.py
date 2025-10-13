import google.generativeai as genai
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Retrieve API Key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("API_KEY is not set. Please check your .envfile.")

# Configure the API key
genai.configure(api_key=api_key)

# List available models
try:
    models = genai.list_models()
    for model in models:
        print(model.name)
except Exception as e:
    print(f"Error fetching models: {e}")