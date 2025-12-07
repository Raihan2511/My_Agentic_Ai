import os
import sys
import torch
import re 
import datetime 
from typing import Type, Any, Optional, ClassVar
from bs4 import BeautifulSoup 

from pydantic import BaseModel, Field
# --- CHANGED: Use OpenAI client for Krutrim ---
from langchain_openai import ChatOpenAI
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

    # --- Attributes for ALL models ---
    classifier_llm: Optional[Any] = None
    offering_model: Optional[Any] = None
    tokenizer: Optional[Any] = None
    base_model_id: Optional[str] = None
    offering_adapter_path: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        self._initialize_classifier()
        self.base_model_id = self.get_tool_config("BASE_MODEL_ID")
        
        # --- FIX 1: Point to the new V2 Checkpoint (Custom Titles) ---
        self.offering_adapter_path = "/home/sysadm/Music/unitime_nlp/data_generator/Offering-nlp-to-xml_update_v2/checkpoint-875"

    def _initialize_classifier(self):
        if self.classifier_llm: return
        try:
            # --- UPDATED FOR KRUTRIM ---
            # Try to get key from tool config, otherwise fallback to os.getenv
            krutrim_api_key = self.get_tool_config("KRUTRIM_API_KEY") or os.getenv("KRUTRIM_API_KEY")
            
            # Get the model name from .env, default to the one you requested
            model_name = os.getenv("LLM_MODEL", "Qwen3-Next-80B-A3B-Instruct")

            if not krutrim_api_key:
                print("Error: KRUTRIM_API_KEY is missing in configuration.")
                return

            self.classifier_llm = ChatOpenAI(
                model=model_name,
                api_key=krutrim_api_key,
                base_url="https://cloud.olakrutrim.com/v1",
                temperature=0.0
            )
            # ---------------------------
        except Exception as e:
            print(f"Error: Failed to initialize Classifier LLM. Exception: {e}")

    def _load_qlora_pipeline(self, adapter_path: str) -> Any:
        try:
            if not self.tokenizer:
                self.tokenizer = AutoTokenizer.from_pretrained(
                    self.base_model_id,
                    trust_remote_code=True,
                    use_fast=False
                )
            
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
            model = PeftModel.from_pretrained(base_model, adapter_path)
            model.eval()
            return model
        except Exception as e:
            return None

    def _classify_intent(self, query: str) -> str:
        # Default to Course_Offering for this tool as it's specifically for adding offerings
        return "Course_Offering"

    def _sanitize_prompt_for_model(self, email_body: str, intent: str) -> str:
        print(f"Sanitizing prompt for intent: {intent}...")
        
        # --- FIX 2: Updated Prompt to match V2 Training Data (Includes Title) ---
        system_prompt = """
        You are a Data Formatter. Your job is to extract details from a course request email and format them into a SINGLE strict sentence.
        
        REQUIRED OUTPUT FORMAT:
        "Add a new course offering: {Subject} {Number} titled '{Title}' as a {Type} in {Building} room {Room} on {Days} {Start}-{End} with limit {Capacity}."
        
        RULES:
        - If the Title is missing, infer a generic one like '{Subject} Basics'.
        - If Building is 'ENG', use 'Engineering'. If 'EDU', use 'Education Center'.
        - Time must be HHmm format (e.g. 1330).
        - Ignore greetings and signatures.
        
        Input Email:
        """

        try:
            full_prompt = f"{system_prompt}\n\"{email_body}\"\n\nOUTPUT:"
            response = self.classifier_llm.invoke(full_prompt)
            clean_prompt = response.content.strip().strip('"') 
            print(f"Sanitized prompt: {clean_prompt}")
            return clean_prompt
        except Exception as e:
            print(f"Error sanitizing prompt: {e}")
            return email_body

    def _get_batch_file_path(self) -> str:
        return os.path.join(PROJECT_ROOT, self.BATCH_FILE_NAME)

    def _ensure_batch_file_exists(self) -> str:
        batch_file_path = self._get_batch_file_path()
        if not os.path.exists(batch_file_path):
            timestamp = datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Z %Y")
            xml_header = f"""<?xml version="1.0" encoding="UTF-8"?>
<offerings campus="woebegon" year="2010" term="Fal" dateFormat="yyyy/M/d" timeFormat="HHmm" created="{timestamp}" includeExams="none">"""
            xml_footer = """
</offerings>"""
            try:
                with open(batch_file_path, "w", encoding="utf-8") as f:
                    f.write(f"{xml_header}\n{xml_footer}")
            except Exception as e:
                return f"Error: Failed to create new batch file: {e}"
        return "Success"

    def _execute(self, query_text: str) -> str:
        if not self.classifier_llm: return "Error: Classifier not loaded."
        if not self.base_model_id: return "Error: Model config missing."

        # 1. Load Model
        if not self.offering_model:
            self.offering_model = self._load_qlora_pipeline(self.offering_adapter_path)
        if not self.offering_model: return "Error: Model failed to load."

        # 2. Sanitize (to V2 Format)
        sanitized_prompt = self._sanitize_prompt_for_model(query_text, "Course_Offering")

        # 3. Generate
        try:
            inputs = self.tokenizer(sanitized_prompt, return_tensors="pt").to(self.offering_model.device)
            with torch.no_grad():
                outputs = self.offering_model.generate(
                    input_ids=inputs["input_ids"], attention_mask=inputs["attention_mask"],
                    max_new_tokens=512, num_beams=4,
                    pad_token_id=self.tokenizer.pad_token_id, eos_token_id=self.tokenizer.eos_token_id,
                )
            xml_output = self.tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
        except Exception as e:
            return f"Error during inference: {e}"

        # 4. Insert into File
        try:
            ai_xml = BeautifulSoup(xml_output, 'xml')
            offering_tag = ai_xml.find('offering')
            if not offering_tag: return f"Error: Invalid XML. Output: {xml_output}"

            # --- FIX 3: Safe Correction Logic (Does NOT overwrite Title) ---
            course_tag = offering_tag.find('course')
            if course_tag and course_tag.has_attr('courseNbr'):
                pattern = re.compile(rf"([a-zA-Z]+)\s*{course_tag['courseNbr']}", re.IGNORECASE)
                match = pattern.search(sanitized_prompt)
                if match:
                    real_subject = match.group(1).upper()
                    if real_subject != course_tag.get('subject', ''):
                        print(f"Applying fix: {course_tag.get('subject')} -> {real_subject}")
                        course_tag['subject'] = real_subject
                        # CRITICAL: Do NOT reset the title here. We trust the V2 model's generated title.

            offering_block = str(offering_tag)
            
            self._ensure_batch_file_exists()
            batch_file_path = self._get_batch_file_path()

            with open(batch_file_path, "r", encoding="utf-8") as f:
                content = f.read()

            insert_pos = content.rfind("</offerings>")
            if insert_pos == -1: return "Error: Batch file corrupt."

            new_content = content[:insert_pos] + offering_block + "\n" + content[insert_pos:]

            with open(batch_file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return "Success: Added to batch file."

        except Exception as e:
            return f"Error saving to batch file: {e}"