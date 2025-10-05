# Backend\Helper\token_counter.py
import os
from typing import List, Dict, Any

# --- Library Imports with Fallbacks ---
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

try:
    from transformers import AutoTokenizer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

class UniversalTokenCounter:
    """
    A universal token counter that supports Google Gemini, OpenAI models (tiktoken),
    and open-source Hugging Face models (transformers).
    It caches loaded tokenizer or model client objects to avoid re-initialization.
    """
    def __init__(self):
        self.tokenizers = {}
        self._gemini_configured = False

    def _get_tokenizer_or_model(self, model_name: str):
        """
        Loads and caches the appropriate tokenizer or model client.
        """
        if model_name in self.tokenizers:
            return self.tokenizers[model_name]

        print(f"Initializing handler for model: {model_name}...")
        handler = None
        try:
            # Case 1: Google Gemini Models
            if "gemini" in model_name:
                if not GEMINI_AVAILABLE:
                    raise ImportError("google-generativeai is not installed. Please run 'pip install google-generativeai'")
                
                # Configure the API key once
                if not self._gemini_configured:
                    api_key = os.getenv("GOOGLE_API_KEY")
                    if not api_key:
                        raise ValueError("GOOGLE_API_KEY environment variable not found. Please set it in your .env file.")
                    genai.configure(api_key=api_key)
                    self._gemini_configured = True
                
                handler = genai.GenerativeModel(model_name)

            # Case 2: OpenAI GPT Models
            elif "gpt" in model_name:
                if not TIKTOKEN_AVAILABLE:
                    raise ImportError("tiktoken is not installed. Please run 'pip install tiktoken'")
                handler = tiktoken.get_encoding("cl100k_base")

            # Case 3: Hugging Face Open-Source Models
            else:
                if not TRANSFORMERS_AVAILABLE:
                    raise ImportError("transformers is not installed. Please run 'pip install transformers sentencepiece'")
                handler = AutoTokenizer.from_pretrained(model_name)
            
            self.tokenizers[model_name] = handler
            print("Handler initialized and cached.")
            return handler

        except Exception as e:
            print(f"Error initializing handler for '{model_name}': {e}")
            self.tokenizers[model_name] = None # Cache failure to avoid retrying
            return None

    def count_text_tokens(self, text: str, model_name: str) -> int:
        """
        Counts tokens in a text string using the appropriate method for the model.
        """
        if not isinstance(text, str):
            return 0
            
        handler = self._get_tokenizer_or_model(model_name)
        if handler is None:
            return len(text) // 4 # Fallback estimate

        try:
            # Gemini has a specific client method which makes an API call
            if "gemini" in model_name:
                # The handler is a GenerativeModel instance
                return handler.count_tokens(text).total_tokens
            
            # tiktoken and transformers have a compatible .encode() method
            else:
                # The handler is a tokenizer instance
                return len(handler.encode(text))
        except Exception as e:
            print(f"Error counting tokens for model '{model_name}': {e}")
            return len(text) // 4 # Fallback on error

# --- Example Usage ---
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv() # Load .env file for the GOOGLE_API_KEY

    token_counter = UniversalTokenCounter()
    
    # --- Test with a Gemini Model ---
    gemini_model = "gemini-1.5-flash-latest" # or "gemini-pro"
    gemini_text = "Hello, this is a test for the Google Gemini API."
    gemini_token_count = token_counter.count_text_tokens(gemini_text, model_name=gemini_model)
    print(f"\nModel: '{gemini_model}'")
    print(f"Text: '{gemini_text}'")
    print(f"Token Count: {gemini_token_count}")

    # --- Test with an OpenAI Model ---
    gpt_model = "gpt-4"
    gpt_text = "Hello, this is a test for OpenAI's tokenizer."
    gpt_token_count = token_counter.count_text_tokens(gpt_text, model_name=gpt_model)
    print(f"\nModel: '{gpt_model}'")
    print(f"Text: '{gpt_text}'")
    print(f"Token Count: {gpt_token_count}")

    # --- Test with an Open Source Model ---
    mistral_model = "mistralai/Mistral-7B-Instruct-v0.2"
    mistral_text = "Hello, this is a test for an open-source tokenizer."
    mistral_token_count = token_counter.count_text_tokens(mistral_text, model_name=mistral_model)
    print(f"\nModel: '{mistral_model}'")
    print(f"Text: '{mistral_text}'")
    print(f"Token Count: {mistral_token_count}")