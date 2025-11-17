import os
import sys
from typing import Type
from enum import Enum
from pydantic import BaseModel, Field

# --- Transformers Imports ---
# You must have 'transformers' and 'torch' installed:
# pip install transformers torch
try:
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    import torch
except ImportError:
    print("WARNING: 'transformers' or 'torch' not installed. NLPToXMLTool will not work.")
    print("Please run: pip install transformers torch")

# --- Project Path Setup ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# --- Framework Imports ---
from Backend.tool_framework.base_tool import BaseTool

# --- Input Schema ---
class TaskType(str, Enum):
    """Enumeration for the type of NLP to XML conversion."""
    OFFERING = "Offering"
    PREFERENCE = "Preference"

class NLPToXMLInput(BaseModel):
    """Input schema for the NLPToXMLTool."""
    text: str = Field(..., description="The natural language text to be converted to XML.")
    task_type: TaskType = Field(..., description="The type of conversion to perform: 'Offering' or 'Preference'.")

class NLPToXMLTool(BaseTool):
    """
    A tool that uses fine-tuned CodeT5p models to convert natural language 
    text into UniTime-compatible XML.
    """
    name: str = "Convert_NLP_to_XML"
    description: str = "Converts natural language text into a UniTime XML string for 'Offering' or 'Preference' tasks."
    args_schema: Type[BaseModel] = NLPToXMLInput

    # --- Caching models in memory ---
    # We cache models at the class level to avoid reloading them on every call
    _models = {}
    _tokenizers = {}

    def _load_model(self, model_path: str):
        """Loads and caches a model and tokenizer."""
        if model_path in self._models:
            return self._models[model_path], self._tokenizers[model_path]

        print(f"--- [NLP Tool] Loading model: {model_path} ---")
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            tokenizer = AutoTokenizer.from_pretrained(model_path)
            model = AutoModelForSeq2SeqLM.from_pretrained(model_path).to(device)
            
            self._models[model_path] = model
            self._tokenizers[model_path] = tokenizer
            print(f"--- [NLP Tool] Model loaded successfully to {device} ---")
            return model, tokenizer

        except Exception as e:
            print(f"--- [NLP Tool] CRITICAL: Failed to load model from {model_path} ---")
            print(f"Error: {e}")
            return None, None

    def _execute(self, text: str, task_type: TaskType) -> str:
        """
        Executes the NLP to XML conversion using the specified fine-tuned model.
        """
        print(f"--- [NLP Tool] Starting conversion for task: {task_type.value} ---")
        
        # --- 1. Get model paths from config ---
        offering_model_path = self.get_tool_config("OFFERING_MODEL_PATH")
        preference_model_path = self.get_tool_config("PREFERENCE_MODEL_PATH")

        if not offering_model_path or not preference_model_path:
            return "Error: Model paths (OFFERING_MODEL_PATH, PREFERENCE_MODEL_PATH) are not configured."

        # --- 2. Select and load the correct model ---
        model_path = ""
        if task_type == TaskType.OFFERING:
            model_path = offering_model_path
        elif task_type == TaskType.PREFERENCE:
            model_path = preference_model_path
        
        model, tokenizer = self._load_model(model_path)
        if model is None or tokenizer is None:
            return f"Error: Failed to load model for task '{task_type.value}' from path '{model_path}'."

        # --- 3. Prepare input for the model ---
        # We assume the fine-tuned model is trained to respond to the raw text.
        # You can add a prefix here if your model expects one (e.g., "convert to xml: ")
        input_text = text 
        device = "cuda" if torch.cuda.is_available() else "cpu"

        try:
            # --- 4. Run inference ---
            inputs = tokenizer(input_text, return_tensors="pt", padding=True, truncation=True).to(device)
            
            # Generate XML
            # You may need to adjust max_length, num_beams, etc. based on your model's training
            outputs = model.generate(
                **inputs, 
                max_length=512,  
                num_beams=4,
                early_stopping=True
            )
            
            # --- 5. Decode and return ---
            generated_xml = tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            print(f"--- [NLP Tool] Conversion successful. Output: {generated_xml} ---")
            return generated_xml

        except Exception as e:
            print(f"--- [NLP Tool] Error during model inference: {e} ---")
            return f"Error: Model inference failed. {str(e)}"