# Backend/Tools/university/add_to_batch_file.py

import os
import sys
import torch
import re
import datetime 
from typing import Type, Any, Optional, ClassVar
from bs4 import BeautifulSoup # <-- 1. IMPORT BEAUTIFULSOUP

from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
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
class AddToBatchInput(BaseModel):
    query_text: str = Field(..., description="The full, original email body or query text to be processed.")

# --- Tool Class Definition ---
class AddToBatchFileTool(BaseTool):
    name: str = "Add_Offering_to_Batch_File"
    description: str = "Processes an email and inserts the resulting <offering> XML into the main batch file."
    args_schema: Type[BaseModel] = AddToBatchInput
    
    BATCH_FILE_NAME: ClassVar[str] = "unitime_batch.xml"

    # (All your model attributes and __init__ / _load_qlora_pipeline / etc. methods are correct)
    # (Copy all of them here)
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
            
            model.eval() # Set to evaluation mode

            print("✅ Model is ready!")
            return model
        
        except Exception as e:
            print(f"Error: Failed to load QLoRA model. Exception: {e}")
            return None

    def _classify_intent(self, query: str) -> str:
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
        # (This function is identical to your old tool)
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

    def _get_batch_file_path(self) -> str:
        """Helper to get the full path to the batch file."""
        return os.path.join(PROJECT_ROOT, self.BATCH_FILE_NAME)

    def _ensure_batch_file_exists(self) -> str:
        """
        Checks if the batch file exists. If not, creates it with the
        header and footer so it's a valid, empty batch.
        """
        batch_file_path = self._get_batch_file_path()
        if not os.path.exists(batch_file_path):
            print(f"--- {self.BATCH_FILE_NAME} not found. Creating new base file. ---")
            timestamp = datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Z %Y")
            
            xml_header = f"""<?xml version="1.0" encoding="UTF-8"?>
<offerings campus="woebegon" year="2010" term="Fal" dateFormat="yyyy/M/d" timeFormat="HHmm" created="{timestamp}" includeExams="none">"""
            
            xml_footer = """
</offerings>"""

            try:
                with open(batch_file_path, "w", encoding="utf-8") as f:
                    f.write(f"{xml_header}\n{xml_footer}")
                return "Success: Created new batch file."
            except Exception as e:
                return f"Error: Failed to create new batch file: {e}"
        return "Success: Batch file already exists."


    def _execute(self, query_text: str) -> str:
        # (This function is identical up to Step 4)
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

        # --- Step 4: Run the Specialized Model ---
        xml_output = ""
        try:
            print(f"Generating XML with {intent} model (manual generation)...")
            
            inputs = self.tokenizer(sanitized_prompt, return_tensors="pt").to(model_to_use.device)

            with torch.no_grad():
                outputs = model_to_use.generate(
                    **inputs,
                    max_new_tokens=512,
                    num_beams=4,
                    early_stopping=False,
                    pad_token_id=self.tokenizer.pad_token_id 
                )

            xml_output = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            xml_output = xml_output.strip()

        except Exception as e:
            return f"Error: An exception occurred during model inference: {e}"

        # --- STEP 5: NEW LOGIC (CORRECTED WITH BEAUTIFULSOUP) ---
        try:
            print("Parsing AI output to find <offering> block...")
            
            # **THE FIX IS HERE:**
            # We use BeautifulSoup to parse the AI's XML output
            ai_xml = BeautifulSoup(xml_output, 'xml')
            
            # Find the <offering> tag
            offering_tag = ai_xml.find('offering')
            
            if not offering_tag:
                # This error means your AI model did not produce a valid <offering>
                return f"Error: AI model generated invalid XML. Could not find <offering> tag. Output: {xml_output}"

            # Convert just the <offering> tag and its contents back to a string
            offering_block = str(offering_tag)
            
            # 1. Ensure the base file exists
            init_status = self._ensure_batch_file_exists()
            if "Error" in init_status:
                return init_status
            
            batch_file_path = self._get_batch_file_path()

            # 2. Read the current batch file
            with open(batch_file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 3. Find the *last* closing </offerings> tag
            insert_pos = content.rfind("</offerings>")
            
            if insert_pos == -1:
                return f"Error: Batch file '{batch_file_path}' is corrupt or missing </offerings> tag."

            # 4. Insert the new *offering_block*
            new_content = (
                content[:insert_pos] 
                + offering_block 
                + "\n"
                + content[insert_pos:]
            )

            # 5. Write the entire new content back to the file
            with open(batch_file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            print(f"Successfully inserted new offering into {batch_file_path}")
            return "Success: The request has been processed and added to the batch file."

        except Exception as e:
            return f"Error saving to batch file: {e}"


















# import os
# import sys
# import torch
# import re
# import datetime 
# from typing import Type, Any, Optional, ClassVar
# from bs4 import BeautifulSoup 

# from pydantic import BaseModel, Field
# from langchain_google_genai import ChatGoogleGenerativeAI
# from transformers import (
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
# class AddToBatchInput(BaseModel):
#     query_text: str = Field(..., description="The full, original email body or query text to be processed.")

# # --- Tool Class Definition ---
# class AddToBatchFileTool(BaseTool):
#     name: str = "Add_Offering_to_Batch_File"
#     description: str = "Processes an email/query, generates XML, and inserts or **modifies/replaces** the offering within the single **unitime_batch.xml** file."
#     args_schema: Type[BaseModel] = AddToBatchInput
    
#     # CONSOLIDATED to use a single batch file for all operations
#     BATCH_FILE_NAME: ClassVar[str] = "unitime_batch.xml" 

#     # --- Attributes for ALL models ---
#     classifier_llm: Optional[Any] = None
#     offering_model: Optional[Any] = None
#     preference_model: Optional[Any] = None
#     tokenizer: Optional[Any] = None
#     base_model_id: Optional[str] = None
#     offering_adapter_path: Optional[str] = None
#     preference_adapter_path: Optional[str] = None

#     def __init__(self, **data):
#         super().__init__(**data)
#         self._initialize_classifier()
#         self.base_model_id = self.get_tool_config("BASE_MODEL_ID")
#         self.offering_adapter_path = self.get_tool_config("OFFERING_MODEL_PATH")
#         self.preference_adapter_path = self.get_tool_config("PREFERENCE_MODEL_PATH")
        
#         if not self.base_model_id:
#             print("Error: BASE_MODEL_ID is not configured.")
#         if not self.offering_adapter_path or not self.preference_adapter_path:
#             print("Error: Adapter paths are not configured.")

#     def _initialize_classifier(self):
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
#                 temperature=0.0
#             )
#             print("Classifier LLM (Gemini) initialized.")
#         except Exception as e:
#             print(f"Error: Failed to initialize Classifier LLM. Exception: {e}")

#     def _load_qlora_pipeline(self, adapter_path: str) -> Any:
#         try:
#             print(f"Loading QLoRA model. Base: '{self.base_model_id}', Adapter: '{adapter_path}'")
#             if not self.tokenizer:
#                 print("Loading tokenizer...")
#                 self.tokenizer = AutoTokenizer.from_pretrained(
#                     self.base_model_id,
#                     trust_remote_code=True,
#                     add_bos_token=True,
#                     add_eos_token=True,
#                     use_fast=False
#                 )
#             bnb_config = BitsAndBytesConfig(
#                 load_in_4bit=True,
#                 bnb_4bit_quant_type="nf4",
#                 bnb_4bit_compute_dtype=torch.float16,
#             )
#             print("Loading 4-bit base model...")
#             base_model = AutoModelForSeq2SeqLM.from_pretrained(
#                 self.base_model_id,
#                 quantization_config=bnb_config,
#                 device_map="auto",
#                 trust_remote_code=True,
#                 torch_dtype=torch.float16
#             )
#             print(f"Base model loaded.")
#             print(f"Loading adapter from: {adapter_path}")
#             model = PeftModel.from_pretrained(base_model, adapter_path)
#             print(f"Adapter loaded.")
#             model.eval()
#             print("✅ Model is ready!")
#             return model
#         except Exception as e:
#             print(f"Error: Failed to load QLoRA model. Exception: {e}")
#             return None

#     def _classify_intent(self, query: str) -> str:
#         if not self.classifier_llm:
#             return "Error: Classifier model is not loaded."
#         prompt = f"""
#         Classify the following university-related query into one of the following exact categories:
#         - Course_Offering (for adding new classes, for updating existing classes, student registrations, etc.)
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
#                 return "Other"
#         except Exception as e:
#             return f"Error: Classification failed: {e}"

#     def _classify_action(self, query: str) -> str:
#         """Determines if a Course_Offering query is an INSERT (new course) or UPDATE (existing course)."""
#         if not self.classifier_llm:
#             return "Error: Classifier model is not loaded."
        
#         prompt = f"""
#         Analyze the following university request. Classify the desired action as either 'INSERT' (for creating a new course/offering) or 'UPDATE' (for modifying an existing course/offering).
        
#         Respond with *only* the classification ('INSERT' or 'UPDATE') and nothing else.
        
#         Query: "{query}"
#         """
#         try:
#             response = self.classifier_llm.invoke(prompt)
#             action = response.content.strip().upper()
#             if action in ["INSERT", "UPDATE"]:
#                 return action
#             else:
#                 return "INSERT" 
#         except Exception as e:
#             print(f"Error: Action classification failed: {e}")
#             return "INSERT"

#     def _sanitize_prompt_for_model(self, email_body: str, intent: str) -> str:
#         print(f"Sanitizing prompt for intent: {intent}...")
#         if intent == "Course_Offering":
#             system_prompt = """
#             You are an expert data extractor. Convert the following email body into a clean, single-line instructional prompt.
#             The prompt MUST start with "COURSE OFFERING REQUEST" followed by the extracted details.
#             Example: "COURSE OFFERING REQUEST Add a new class: [Course Name]. Place it in [Room] on [Schedule]. It's a [Type] with a limit of [Capacity]."
#             Extract all relevant details from the email. Ignore all greetings, sign-offs, and conversational filler.
#             """
#         elif intent == "Instructor_Preference":
#                system_prompt = """
#             You are an expert data extractor. Convert the following email body into a clean, single-line instructional prompt.
#             The prompt MUST start with "INSTRUCTOR PREFERENCE REQUEST" followed by the extracted details.
#             Example: "INSTRUCTOR PREFERENCE REQUEST Instructor [Name] has a [Preference Level] preference for the [Feature] room feature."
#             Extract all relevant details from the email. Ignore all greetings, sign-offs, and conversational filler.
#             """
#         else:
#             return email_body 

#         try:
#             full_prompt = f"{system_prompt}\n\nEMAIL BODY:\n\"{email_body}\"\n\nCLEAN PROMPT:"
#             response = self.classifier_llm.invoke(full_prompt)
#             clean_prompt = response.content.strip().strip('"') 
#             print(f"Sanitized prompt: {clean_prompt}")
#             return clean_prompt
#         except Exception as e:
#             print(f"Error sanitizing prompt: {e}")
#             return email_body
    
#     def _get_batch_file_path(self) -> str:
#         """Helper to get the full path to the single batch file."""
#         return os.path.join(PROJECT_ROOT, self.BATCH_FILE_NAME)

#     def _ensure_batch_file_exists(self) -> str:
#         """
#         Checks if the batch file exists. If not, creates it with the
#         header and footer so it's a valid, empty batch.
#         """
#         batch_file_path = self._get_batch_file_path()
#         if not os.path.exists(batch_file_path):
#             print(f"--- {self.BATCH_FILE_NAME} not found. Creating new base file. ---")
#             timestamp = datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Z %Y")
            
#             xml_header = f"""<?xml version="1.0" encoding="UTF-8"?>
# <offerings campus="woebegon" year="2010" term="Fal" dateFormat="yyyy/M/d" timeFormat="HHmm" created="{timestamp}" includeExams="none">"""
            
#             xml_footer = """
# </offerings>"""

#             try:
#                 with open(batch_file_path, "w", encoding="utf-8") as f:
#                     f.write(f"{xml_header}\n{xml_footer}")
#                 return "Success: Created new batch file."
#             except Exception as e:
#                 return f"Error: Failed to create new batch file: {e}"
#         return "Success: Batch file already exists."


#     def _execute(self, query_text: str) -> str:
#         if not self.classifier_llm:
#             return "Error: Classifier AI model is not loaded."
#         if not self.base_model_id or not self.offering_adapter_path or not self.preference_adapter_path:
#             return "Error: Model paths are not configured."

#         # --- Step 1: Classify the Intent and Action ---
#         print(f"Classifying query: '{query_text[:100]}...'")
#         intent = self._classify_intent(query_text)
#         print(f"Query classified as: {intent}")

#         action = ""
#         model_to_use = None
        
#         if intent == "Course_Offering":
#             action = self._classify_action(query_text)
#             print(f"Course Offering Action classified as: {action}")
#             if not self.offering_model:
#                 self.offering_model = self._load_qlora_pipeline(self.offering_adapter_path)
#             model_to_use = self.offering_model
            
#         elif intent == "Instructor_Preference":
#             action = "INSERT" # Preferences are treated as new insertions/modifications, appending to the batch file
#             if not self.preference_model:
#                 self.preference_model = self._load_qlora_pipeline(self.preference_adapter_path)
#             model_to_use = self.preference_model

#         elif "Error" in intent:
#             return intent
#         else:
#             return "Error: Query classified as 'Other'. No specialized model available for this request."

#         if not model_to_use:
#             return f"Error: Failed to load the model for intent '{intent}'."

#         # --- Step 2: Sanitize the Prompt & Run the Specialized Model ---
#         sanitized_prompt = self._sanitize_prompt_for_model(query_text, intent)
#         xml_output = ""
#         try:
#             print(f"Generating XML with {intent} model (manual generation)...")
#             inputs = self.tokenizer(sanitized_prompt, return_tensors="pt").to(model_to_use.device)
#             with torch.no_grad():
#                 outputs = model_to_use.generate(
#                     **inputs,
#                     max_new_tokens=512,
#                     num_beams=4,
#                     early_stopping=False,
#                     pad_token_id=self.tokenizer.pad_token_id 
#                 )
#             xml_output = self.tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
#         except Exception as e:
#             return f"Error: An exception occurred during model inference: {e}"

#         # --- Step 3: Parse the Generated XML Block ---
#         try:
#             print(f"Parsing AI output to find XML block for action: {action}...")
#             ai_xml = BeautifulSoup(xml_output, 'xml')
            
#             target_tag = None
#             unique_key = None
            
#             if intent == "Course_Offering":
#                 target_tag = ai_xml.find('offering')
#                 if not target_tag:
#                     return f"Error: AI model generated invalid XML. Could not find <offering> tag. Output: {xml_output}"
                
#                 # Use Subject and Course Number as the unique identifier
#                 unique_key = (target_tag.get('subject', 'UNKNOWN'), target_tag.get('courseNbr', 'UNKNOWN'))
#                 if unique_key == ('UNKNOWN', 'UNKNOWN'):
#                     return f"Error: Generated XML missing required 'subject' and 'courseNbr' attributes for modification. Output: {xml_output}"
                
#             elif intent == "Instructor_Preference":
#                 # Assuming preference model generates a preference block
#                 target_tag = ai_xml.find('preference') or ai_xml.find('instructor')
#                 if not target_tag:
#                     return f"Error: AI model generated invalid XML. Could not find preference tag. Output: {xml_output}"
#                 action = "INSERT" # Always treat preferences as appends for simplicity
            
#             else:
#                 return "Error: Unknown intent after model generation."

#             xml_block = str(target_tag)
            
#             # 1. Ensure the base file exists
#             init_status = self._ensure_batch_file_exists()
#             if "Error" in init_status:
#                 return init_status
            
#             batch_file_path = self._get_batch_file_path()

#             # 2. Read the current batch file content
#             with open(batch_file_path, "r", encoding="utf-8") as f:
#                 content = f.read()
            
#             # --- Step 4: INSERT or REPLACE Logic ---
#             if action == "INSERT":
#                 # APPEND to the end of the file (before </offerings>)
#                 insert_pos = content.rfind("</offerings>")
#                 if insert_pos == -1:
#                     return f"Error: Batch file '{batch_file_path}' is corrupt or missing </offerings> tag."
                
#                 new_content = (
#                     content[:insert_pos] 
#                     + "\n"
#                     + xml_block 
#                     + "\n"
#                     + content[insert_pos:]
#                 )
#                 status_msg = f"Success: New entry added (INSERT) to {self.BATCH_FILE_NAME}."
            
#             elif action == "UPDATE":
#                 # FIND and REPLACE the existing block using BeautifulSoup
                
#                 existing_xml = BeautifulSoup(content, 'xml')
                
#                 # Find the existing offering using BOTH subject and courseNbr
#                 old_offering = existing_xml.find('offering', attrs={
#                     'subject': unique_key[0], 
#                     'courseNbr': unique_key[1]
#                 })

#                 if old_offering:
#                     # Replace the old offering tag with the new one generated by the model
#                     old_offering.replace_with(target_tag)
                    
#                     # Get the string representation of the modified BeautifulSoup object
#                     new_content = str(existing_xml)
#                     status_msg = f"Success: Offering {unique_key[0]} {unique_key[1]} was modified/replaced (UPDATE) in {self.BATCH_FILE_NAME}."
#                 else:
#                     # If not found, treat it as a new insert (append)
#                     print("Warning: Existing offering not found for update. Appending as new INSERT.")
                    
#                     insert_pos = content.rfind("</offerings>")
#                     new_content = (
#                         content[:insert_pos] 
#                         + "\n"
#                         + xml_block 
#                         + "\n"
#                         + content[insert_pos:]
#                     )
#                     status_msg = f"Success: Offering {unique_key[0]} {unique_key[1]} not found, added as new entry (INSERT) to {self.BATCH_FILE_NAME}."
                    

#             # 5. Write the entire new content back to the file
#             with open(batch_file_path, "w", encoding="utf-8") as f:
#                 f.write(new_content)

#             print(status_msg)
#             return status_msg

#         except Exception as e:
#             return f"Error saving to batch file: {e}"