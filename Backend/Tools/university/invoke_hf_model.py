# import os
# import sys
# import torch
# from typing import Type, Any, Optional

# from pydantic import BaseModel, Field
# from langchain_google_genai import ChatGoogleGenerativeAI

# # --- Transformers/PEFT Imports ---
# from transformers import (
#     pipeline, 
#     AutoModelForSeq2SeqLM,
#     AutoTokenizer, 
#     BitsAndBytesConfig
# )
# from peft import PeftModel

# # --- Project Path Setup ---
# PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
# if PROJECT_ROOT not in sys.path:
#     sys.path.append(PROJECT_ROOT)

# from Backend.tool_framework.base_tool import BaseTool

# # --- Pydantic Input Schema ---
# class InvokeHFModelInput(BaseModel):
#     query_text: str = Field(..., description="The full, original email body or query text to be processed.")

# # --- Tool Class Definition ---
# class InvokeHFModelTool(BaseTool):
#     """
#     A "smart router" tool. It classifies a query, then loads the correct
#     QLoRA adapter onto a base model to generate the final XML.
#     """
#     name: str = "Invoke_University_AI_Model"
#     description: str = "Processes a query by routing it to the correct specialized AI model (e.g., course offering, instructor preference) and returns the result as an XML string."
    
#     # --- Pydantic v2 Fix ---
#     args_schema: Type[BaseModel] = InvokeHFModelInput

#     # --- Attributes for ALL models ---
#     classifier_llm: Optional[Any] = None
    
#     # Pipelines will be loaded lazily (on-demand)
#     offering_pipeline: Optional[Any] = None
#     preference_pipeline: Optional[Any] = None
    
#     # Store tokenizer to avoid reloading
#     tokenizer: Optional[Any] = None
    
#     # Store paths from config
#     base_model_id: Optional[str] = None
#     offering_adapter_path: Optional[str] = None
#     preference_adapter_path: Optional[str] = None


#     def __init__(self, **data):
#         """
#         Initializes the tool.
#         - Loads the classifier LLM immediately.
#         - Stores model paths for lazy loading fine-tuned models.
#         """
#         super().__init__(**data)
        
#         # 1. Load the Gemini classifier
#         self._initialize_classifier()
        
#         # 2. Store paths for on-demand QLoRA model loading
#         self.base_model_id = self.get_tool_config("BASE_MODEL_ID")
#         self.offering_adapter_path = self.get_tool_config("OFFERING_MODEL_PATH")
#         self.preference_adapter_path = self.get_tool_config("PREFERENCE_MODEL_PATH")
        
#         if not self.base_model_id:
#             print("Error: BASE_MODEL_ID is not configured. This is required to load QLoRA adapters.")
#         if not self.offering_adapter_path or not self.preference_adapter_path:
#             print("Error: Adapter paths (OFFERING_MODEL_PATH, PREFERENCE_MODEL_PATH) are not configured.")

#     def _initialize_classifier(self):
#         """Loads only the Gemini classifier LLM."""
#         if self.classifier_llm:
#             return
            
#         print("Initializing models...")
#         try:
#             google_api_key = self.get_tool_config("GOOGLE_API_KEY")
#             if not google_api_key:
#                 raise ValueError("GOOGLE_API_KEY not found in config.")
#             self.classifier_llm = ChatGoogleGenerativeAI(
#                 model="gemini-2.5-flash-lite", 
#                 google_api_key=google_api_key,
#                 temperature=0.0 # Deterministic classification
#             )
#             print("Classifier LLM (Gemini) initialized.")
#         except Exception as e:
#             print(f"Error: Failed to initialize Classifier LLM. Exception: {e}")

#     def _load_qlora_pipeline(self, adapter_path: str) -> Any:
#         """
#         Loads the 4-bit base model (codet5p), attaches the specified QLoRA adapter,
#         merges it, and returns a "text2text-generation" pipeline.
        
#         This function is based *exactly* on the loading code you provided.
#         """
#         try:
#             print(f"Loading QLoRA model. Base: '{self.base_model_id}', Adapter: '{adapter_path}'")

#             # Load the tokenizer (only once)
#             if not self.tokenizer:
#                 print("Loading tokenizer...")
#                 self.tokenizer = AutoTokenizer.from_pretrained(
#                     self.base_model_id,
#                     trust_remote_code=True,
#                     add_bos_token=True,
#                     add_eos_token=True,
#                     use_fast=False
#                 )
            
#             # Configure 4-bit quantization
#             bnb_config = BitsAndBytesConfig(
#                 load_in_4bit=True,
#                 bnb_4bit_quant_type="nf4",
#                 bnb_4bit_compute_dtype=torch.float16,
#             )
            
#             # Load the base model in 4-bit
#             print("Loading 4-bit base model...")
#             base_model = AutoModelForSeq2SeqLM.from_pretrained(
#                 self.base_model_id,
#                 quantization_config=bnb_config,
#                 device_map="auto",
#                 trust_remote_code=True,
#                 torch_dtype=torch.float16 # Added for consistency
#             )
#             print(f"Base model loaded.")

#             # Load the PEFT model (apply adapter)
#             print(f"Loading adapter from: {adapter_path}")
#             model = PeftModel.from_pretrained(base_model, adapter_path)
#             print(f"Adapter loaded.")
            
#             # Merge the adapter into the base model for faster inference
#             print("Merging adapter...")
#             model = model.merge_and_unload()
#             model.eval() # Set to evaluation mode
#             print("Adapter merged and unloaded.")

#             # Create the pipeline
#             model_pipeline = pipeline(
#                 "text2text-generation", # Correct pipeline for T5 models
#                 model=model,
#                 tokenizer=self.tokenizer,
#                 device_map="auto",
#                 torch_dtype=torch.float16
#             )
#             print("✅ Model pipeline is ready!")
#             return model_pipeline
        
#         except Exception as e:
#             print(f"Error: Failed to load QLoRA model. Exception: {e}")
#             print("Please ensure 'peft', 'bitsandbytes', and 'accelerate' are installed.")
#             return None

#     def _classify_intent(self, query: str) -> str:
#         """Uses the LLM to classify the query text."""
#         if not self.classifier_llm:
#             return "Error: Classifier model is not loaded."

#         prompt = f"""
#         Classify the following university-related query into one of the following exact categories:
#         - Course_Offering (for adding new classes, student registrations, etc.)
#         - Instructor_Preference (for teacher preferences, room features, time constraints)
#         - Other (for anything else)
        
#         Respond with *only* the category name and nothing else.
        
#         Query: "{query}"
#         """
#         try:
#             response = self.classifier_llm.invoke(prompt)
#             intent = response.content.strip()
            
#             if intent in ["Course_Offering", "Instructor_Preference", "Other"]:
#                 return intent
#             else:
#                 return "Other" # Default to 'Other' if classification fails
#         except Exception as e:
#             return f"Error: Classification failed: {e}"

#     def _execute(self, query_text: str) -> str:
#         """
#         Main execution logic:
#         1. Classify intent.
#         2. Lazily load the correct QLoRA model.
#         3. Run the model to get XML.
#         4. Return the XML.
#         """
#         if not self.classifier_llm:
#             return "Error: Classifier AI model is not loaded."
#         if not self.base_model_id or not self.offering_adapter_path or not self.preference_adapter_path:
#              return "Error: Model paths are not configured. Cannot load QLoRA models."

#         # --- Step 1: Classify the Intent ---
#         print(f"Classifying query: '{query_text[:100]}...'")
#         intent = self._classify_intent(query_text)
#         print(f"Query classified as: {intent}")

#         # --- Step 2: Route & Lazy-Load the Correct Model ---
#         pipeline_to_use = None
#         if intent == "Course_Offering":
#             # Load the model "lazily" (only when needed)
#             if not self.offering_pipeline:
#                 self.offering_pipeline = self._load_qlora_pipeline(self.offering_adapter_path)
#             pipeline_to_use = self.offering_pipeline
            
#         elif intent == "Instructor_Preference":
#             # Load the model "lazily"
#             if not self.preference_pipeline:
#                 self.preference_pipeline = self._load_qlora_pipeline(self.preference_adapter_path)
#             pipeline_to_use = self.preference_pipeline

#         elif "Error" in intent:
#             return intent # Return the classification error
#         else:
#             return "Error: Query classified as 'Other'. No specialized model available for this request."

#         if not pipeline_to_use:
#              return f"Error: Failed to load the model for intent '{intent}'."

#         # --- Step 3: Run the Specialized Model ---
#         try:
#             print(f"Generating XML with {intent} model...")
#             outputs = pipeline_to_use(
#                 query_text,
#                 max_new_tokens=512, # You can adjust this
#                 num_return_sequences=1
#             )
            
#             # --- CORRECTED XML EXTRACTION ---
#             # For "text2text-generation", the output is clean
#             # and does NOT include the prompt.
#             generated_text = outputs[0]['generated_text']
#             response_text = generated_text.strip()
            
#             return response_text

#         except Exception as e:
#             return f"Error: An exception occurred during model inference: {e}"
















import os
import sys
import torch
from typing import Type, Any, Optional

from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI

# --- Transformers/PEFT Imports ---
from transformers import (
    AutoModelForSeq2SeqLM,
    AutoTokenizer, 
    BitsAndBytesConfig
)
from peft import PeftModel

# --- Project Path Setup ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from Backend.tool_framework.base_tool import BaseTool

# --- Pydantic Input Schema ---
class InvokeHFModelInput(BaseModel):
    query_text: str = Field(..., description="The full, original email body or query text to be processed.")

# --- Tool Class Definition ---
class InvokeHFModelTool(BaseTool):
    name: str = "Invoke_University_AI_Model"
    description: str = "Processes a query by routing it to the correct specialized AI model (e.g., course offering, instructor preference) and returns the result as an XML string."
    args_schema: Type[BaseModel] = InvokeHFModelInput

    # --- Attributes for ALL models ---
    classifier_llm: Optional[Any] = None
    
    offering_model: Optional[Any] = None
    preference_model: Optional[Any] = None
    
    tokenizer: Optional[Any] = None
    base_model_id: Optional[str] = None
    offering_adapter_path: Optional[str] = None
    preference_adapter_path: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        self._initialize_classifier()
        self.base_model_id = self.get_tool_config("BASE_MODEL_ID")
        self.offering_adapter_path = self.get_tool_config("OFFERING_MODEL_PATH")
        self.preference_adapter_path = self.get_tool_config("PREFERENCE_MODEL_PATH")
        
        if not self.base_model_id:
            print("Error: BASE_MODEL_ID is not configured.")
        if not self.offering_adapter_path or not self.preference_adapter_path:
            print("Error: Adapter paths are not configured.")

    def _initialize_classifier(self):
        if self.classifier_llm:
            return
        print("Initializing models...")
        try:
            google_api_key = self.get_tool_config("GOOGLE_API_KEY")
            if not google_api_key:
                raise ValueError("GOOGLE_API_KEY not found in config.")
            self.classifier_llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash-lite", 
                google_api_key=google_api_key,
                temperature=0.0
            )
            print("Classifier LLM (Gemini) initialized.")
        except Exception as e:
            print(f"Error: Failed to initialize Classifier LLM. Exception: {e}")

    def _load_qlora_pipeline(self, adapter_path: str) -> Any:
        try:
            print(f"Loading QLoRA model. Base: '{self.base_model_id}', Adapter: '{adapter_path}'")

            if not self.tokenizer:
                print("Loading tokenizer...")
                self.tokenizer = AutoTokenizer.from_pretrained(
                    self.base_model_id,
                    trust_remote_code=True,
                    add_bos_token=True,
                    add_eos_token=True,
                    use_fast=False
                )
            
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
            )
            
            print("Loading 4-bit base model...")
            base_model = AutoModelForSeq2SeqLM.from_pretrained(
                self.base_model_id,
                quantization_config=bnb_config,
                device_map="auto",
                trust_remote_code=True,
                torch_dtype=torch.float16
            )
            print(f"Base model loaded.")

            print(f"Loading adapter from: {adapter_path}")
            model = PeftModel.from_pretrained(base_model, adapter_path)
            print(f"Adapter loaded.")
            
            # -----------------------------------------------------------------
            # --- THIS IS THE FIX. THE "merge_and_unload" LINE IS REMOVED. ---
            # --- THIS NOW MATCHES YOUR test.py SCRIPT. ---
            # -----------------------------------------------------------------
            
            model.eval() # Set to evaluation mode (just like test.py)

            print("✅ Model is ready!")
            return model
        
        except Exception as e:
            print(f"Error: Failed to load QLoRA model. Exception: {e}")
            return None

    def _classify_intent(self, query: str) -> str:
        # (This function is correct, no changes)
        if not self.classifier_llm:
            return "Error: Classifier model is not loaded."
        prompt = f"""
        Classify the following university-related query into one of the following exact categories:
        - Course_Offering (for adding new classes, student registrations, etc.)
        - Instructor_Preference (for teacher preferences, room features, time constraints)
        - Other (for anything else)
        
        Respond with *only* the category name and nothing else.
        
        Query: "{query}"
        """
        try:
            response = self.classifier_llm.invoke(prompt)
            intent = response.content.strip()
            if intent in ["Course_Offering", "Instructor_Preference", "Other"]:
                return intent
            else:
                return "Other"
        except Exception as e:
            return f"Error: Classification failed: {e}"

    def _sanitize_prompt_for_model(self, email_body: str, intent: str) -> str:
        # (This function is correct, no changes)
        print(f"Sanitizing prompt for intent: {intent}...")
        if intent == "Course_Offering":
            system_prompt = """
            You are an expert data extractor. Convert the following email body into a clean, single-line instructional prompt.
            The prompt MUST start with "COURSE OFFERING REQUEST" followed by the extracted details.
            Example: "COURSE OFFERING REQUEST Add a new class: [Course Name]. Place it in [Room] on [Schedule]. It's a [Type] with a limit of [Capacity]."
            Extract all relevant details from the email. Ignore all greetings, sign-offs, and conversational filler.
            """
        elif intent == "Instructor_Preference":
             system_prompt = """
            You are an expert data extractor. Convert the following email body into a clean, single-line instructional prompt.
            The prompt MUST start with "INSTRUCTOR PREFERENCE REQUEST" followed by the extracted details.
            Example: "INSTRUCTOR PREFERENCE REQUEST Instructor [Name] has a [Preference Level] preference for the [Feature] room feature."
            Extract all relevant details from the email. Ignore all greetings, sign-offs, and conversational filler.
            """
        else:
            return email_body 

        try:
            full_prompt = f"{system_prompt}\n\nEMAIL BODY:\n\"{email_body}\"\n\nCLEAN PROMPT:"
            response = self.classifier_llm.invoke(full_prompt)
            clean_prompt = response.content.strip().strip('"') 
            print(f"Sanitized prompt: {clean_prompt}")
            return clean_prompt
        except Exception as e:
            print(f"Error sanitizing prompt: {e}")
            return email_body

    def _execute(self, query_text: str) -> str:
        # (This function is correct, no changes)
        if not self.classifier_llm:
            return "Error: Classifier AI model is not loaded."
        if not self.base_model_id or not self.offering_adapter_path or not self.preference_adapter_path:
             return "Error: Model paths are not configured."

        # --- Step 1: Classify the Intent ---
        print(f"Classifying query: '{query_text[:100]}...'")
        intent = self._classify_intent(query_text)
        print(f"Query classified as: {intent}")

        # --- Step 2: Route & Lazy-Load the Correct Model ---
        model_to_use = None
        if intent == "Course_Offering":
            if not self.offering_model:
                self.offering_model = self._load_qlora_pipeline(self.offering_adapter_path)
            model_to_use = self.offering_model
            
        elif intent == "Instructor_Preference":
            if not self.preference_model:
                self.preference_model = self._load_qlora_pipeline(self.preference_adapter_path)
            model_to_use = self.preference_model

        elif "Error" in intent:
            return intent
        else:
            return "Error: Query classified as 'Other'. No specialized model available for this request."

        if not model_to_use:
             return f"Error: Failed to load the model for intent '{intent}'."

        # --- Step 3: Sanitize the Prompt ---
        sanitized_prompt = self._sanitize_prompt_for_model(query_text, intent)

        # --- Step 4: Run the Specialized Model (Manually, like your test.py) ---
        try:
            print(f"Generating XML with {intent} model (manual generation)...")
            
            # 1. Tokenize (like test.py)
            inputs = self.tokenizer(sanitized_prompt, return_tensors="pt").to(model_to_use.device)

            # 2. Generate (like test.py)
            with torch.no_grad():
                outputs = model_to_use.generate(
                    **inputs,
                    max_new_tokens=512,
                    num_beams=4,
                    early_stopping=False,
                    pad_token_id=self.tokenizer.pad_token_id 
                )

            # 3. Decode (like test.py)
            xml_output = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return xml_output.strip()

        except Exception as e:
            return f"Error: An exception occurred during model inference: {e}"