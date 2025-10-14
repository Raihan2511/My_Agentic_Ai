import os
import sys
import torch
from pydantic import BaseModel, Field
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer

# --- Project Path Setup ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from Backend.tool_framework.base_tool import BaseTool

# --- Pydantic Input Schema (No changes here) ---
class InvokeHFModelInput(BaseModel):
    student_name: str = Field(..., description="The full name of the student.")
    course_id: str = Field(..., description="The course ID for the registration or query.")
    query_text: str = Field(..., description="The original request or question from the student's email.")

# --- Tool Class Definition (Modified for Direct Model Loading) ---
class InvokeHFModelTool(BaseTool):
    """
    A tool that loads a fine-tuned model directly into memory from a local path
    and uses it to process student and course data.
    """
    name: str = "Invoke_University_AI_Model"
    description: str = "Use this tool to process student data with the specialized university AI model."
    args_schema = InvokeHFModelInput

    # --- NEW: Attributes to hold the loaded model ---
    generator_pipeline = None
    model_path: str = None

    def __init__(self, **data):
        super().__init__(**data)
        # Load the model only once when the tool is initialized.
        self._initialize_model()

    def _initialize_model(self):
        """Loads the model and tokenizer into memory. This is called only once."""
        if self.generator_pipeline:
            # Model is already loaded
            return

        self.model_path = self.get_tool_config("LOCAL_MODEL_PATH")
        if not self.model_path:
            print("Error: LOCAL_MODEL_PATH is not configured. The model will not be loaded.")
            return

        try:
            print(f"Initializing model from local path: {self.model_path}...")
            
            # Check for GPU availability
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"Using device: {device}")

            # Use the transformers pipeline for easy text generation
            # This handles tokenization, model inference, and decoding for you.
            self.generator_pipeline = pipeline(
                "text-generation",
                model=self.model_path,
                torch_dtype=torch.float16, # Use float16 for better performance on GPUs
                device=device,
            )
            print("Model loaded successfully.")

        except Exception as e:
            print(f"Error: Failed to load model from {self.model_path}. Exception: {e}")
            self.generator_pipeline = None


    def _execute(self, student_name: str, course_id: str, query_text: str) -> str:
        # Check if the model failed to load during initialization
        if not self.generator_pipeline:
            return "Error: The AI model is not loaded. Please check the configuration and logs."

        # Format the prompt exactly as your model expects.
        # For instruction-tuned models, you might need a specific format.
        # This is a generic example.
        prompt = f"Process enrollment for student '{student_name}' in course '{course_id}'. Original query: '{query_text}'"
        
        try:
            print(f"Generating response for prompt: '{prompt[:100]}...'")
            outputs = self.generator_pipeline(
                prompt,
                max_new_tokens=512,
                num_return_sequences=1,
                eos_token_id=self.generator_pipeline.tokenizer.eos_token_id,
            )

            # The pipeline output includes the original prompt. We need to extract only the new text.
            generated_text = outputs[0]['generated_text']
            response_text = generated_text[len(prompt):].strip()
            
            return response_text

        except Exception as e:
            return f"Error: An exception occurred during model inference: {e}"