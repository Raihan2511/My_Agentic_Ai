import os
import sys
import torch
import datetime 
from typing import Type, Any, Optional, ClassVar
from bs4 import BeautifulSoup 

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

class AddPreferenceInput(BaseModel):
    query_text: str = Field(..., description="The full, original text requesting the preference update.")

class AddPreferenceToBatchTool(BaseTool):
    name: str = "Add_Preference_to_Batch"
    description: str = "Processes a request to add Instructor Preferences (Time, Room, Distribution) and appends XML to the batch file."
    args_schema: Type[BaseModel] = AddPreferenceInput
    
    BATCH_FILE_NAME: ClassVar[str] = "unitime_batch.xml"

    # --- Attributes ---
    classifier_llm: Optional[Any] = None
    preference_model: Optional[Any] = None
    tokenizer: Optional[Any] = None
    base_model_id: Optional[str] = None
    preference_adapter_path: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        self._initialize_classifier()
        self.base_model_id = self.get_tool_config("BASE_MODEL_ID")
        # Uses the specific PREFERENCE path from your .env
        self.preference_adapter_path = self.get_tool_config("PREFERENCE_MODEL_PATH")

    def _initialize_classifier(self):
        if self.classifier_llm: return
        try:
            google_api_key = self.get_tool_config("GOOGLE_API_KEY")
            self.classifier_llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash-lite", 
                google_api_key=google_api_key,
                temperature=0.0
            )
        except Exception as e:
            print(f"Error: Failed to initialize Classifier LLM. Exception: {e}")

    def _load_qlora_pipeline(self) -> Any:
        try:
            if not self.tokenizer:
                self.tokenizer = AutoTokenizer.from_pretrained(self.base_model_id, trust_remote_code=True, use_fast=False)
            
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
            )
            
            base_model = AutoModelForSeq2SeqLM.from_pretrained(
                self.base_model_id,
                quantization_config=bnb_config,
                device_map="auto",
                trust_remote_code=True,
            )
            print(f"Loading Preference Adapter: {self.preference_adapter_path}")
            model = PeftModel.from_pretrained(base_model, self.preference_adapter_path)
            model.eval()
            return model
        except Exception as e:
            print(f"Error loading Preference Model: {e}")
            return None

    def _sanitize_prompt_for_model(self, text: str) -> str:
        # Specific prompt for Preferences to standardize input for the model
        system_prompt = """
        You are a Data Formatter for University Instructor Preferences. 
        Convert the user request into a standard prompt like:
        "INSTRUCTOR PREFERENCE REQUEST: Instructor [Name] [Action: Add/Update] [Type: Room/Time/Distribution] Preference [Level: Required/Strongly Preferred] for [Details]."
        
        Examples:
        - "Instructor Doe needs a Projector" -> "INSTRUCTOR PREFERENCE REQUEST: Instructor Doe Add Room Preference Required for Projector."
        - "Prof Smith cannot teach on Mondays" -> "INSTRUCTOR PREFERENCE REQUEST: Instructor Smith Add Time Preference Prohibited for Monday."
        
        Input Text:
        """
        try:
            return self.classifier_llm.invoke(f"{system_prompt}\n\"{text}\"\n\nOUTPUT:").content.strip().strip('"')
        except:
            return text

    def _ensure_batch_file_exists(self) -> str:
        batch_file_path = os.path.join(PROJECT_ROOT, self.BATCH_FILE_NAME)
        if not os.path.exists(batch_file_path):
            timestamp = datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Z %Y")
            xml_header = f"""<?xml version="1.0" encoding="UTF-8"?>
<offerings campus="woebegon" year="2010" term="Fal" dateFormat="yyyy/M/d" timeFormat="HHmm" created="{timestamp}" includeExams="none">"""
            xml_footer = """
</offerings>"""
            with open(batch_file_path, "w", encoding="utf-8") as f:
                f.write(f"{xml_header}\n{xml_footer}")
        return "Success"

    def _execute(self, query_text: str) -> str:
        if not self.classifier_llm or not self.base_model_id: return "Error: Config missing."

        # 1. Load Model
        if not self.preference_model:
            self.preference_model = self._load_qlora_pipeline()
        if not self.preference_model: return "Error: Preference Model failed to load."

        # 2. Sanitize
        sanitized_prompt = self._sanitize_prompt_for_model(query_text)
        print(f"Preference Prompt: {sanitized_prompt}")

        # 3. Generate
        try:
            inputs = self.tokenizer(sanitized_prompt, return_tensors="pt").to(self.preference_model.device)
            with torch.no_grad():
                outputs = self.preference_model.generate(
                    input_ids=inputs["input_ids"], attention_mask=inputs["attention_mask"],
                    max_new_tokens=512, num_beams=4,
                    pad_token_id=self.tokenizer.pad_token_id, eos_token_id=self.tokenizer.eos_token_id,
                )
            xml_output = self.tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
        except Exception as e:
            return f"Error during inference: {e}"

        # 4. Insert into File
        try:
            # Logic: Extract the relevant tag. Usually <instructorCoursePref>, <roomPref>, etc.
            # We'll assume the model outputs a valid XML block.
            ai_xml = BeautifulSoup(xml_output, 'xml')
            
            # Find the first meaningful child tag (not strictly <offering> since this is preference)
            # Adjust this based on what your Preference Model outputs!
            # Common tags: <instructorCoursePref>, <preference>, <update>
            pref_tag = ai_xml.find(True) 
            
            if not pref_tag: return f"Error: Invalid XML. Output: {xml_output}"

            pref_block = str(pref_tag)
            
            self._ensure_batch_file_exists()
            batch_file_path = os.path.join(PROJECT_ROOT, self.BATCH_FILE_NAME)

            with open(batch_file_path, "r", encoding="utf-8") as f:
                content = f.read()

            insert_pos = content.rfind("</offerings>")
            if insert_pos == -1: return "Error: Batch file corrupt."

            new_content = content[:insert_pos] + pref_block + "\n" + content[insert_pos:]

            with open(batch_file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return "Success: Preference added to batch file."

        except Exception as e:
            return f"Error saving to batch file: {e}"