import os
import sys
import torch
import re
import datetime 
from typing import Type, Any, Optional, ClassVar
from bs4 import BeautifulSoup

from pydantic import BaseModel, Field
# --- KRUTRIM IMPORT ---
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

class UpdateCourseInput(BaseModel):
    query_text: str = Field(..., description="The formatted prompt from Model_Prompt_Factory.")

class UpdateCourseFileTool(BaseTool):
    name: str = "Update_Course_File"
    description: str = "Executes the AI model to generate XML from a formatted prompt."
    args_schema: Type[BaseModel] = UpdateCourseInput
    
    UPDATE_FILE_NAME: ClassVar[str] = "unitime_update.xml"

    # --- Attributes ---
    classifier_llm: Optional[Any] = None
    offering_model: Optional[Any] = None
    tokenizer: Optional[Any] = None
    
    # --- HARDCODED PATHS FROM YOUR WORKING SCRIPT ---
    base_model_id: str = "Salesforce/codet5p-220m"
    offering_adapter_path: str = "/home/sysadm/Music/unitime/Offering-nlp-to-xml_update_v2/checkpoint-875"
    

    def __init__(self, **data):
        super().__init__(**data)
        self._initialize_classifier()

    def _initialize_classifier(self):
        if self.classifier_llm: return
        try:
            # Initialize Krutrim for text processing (Subject/Title fixing) if needed later
            krutrim_api_key = self.get_tool_config("KRUTRIM_API_KEY") or os.getenv("KRUTRIM_API_KEY")
            model_name = os.getenv("LLM_MODEL", "Qwen3-Next-80B-A3B-Instruct")

            if krutrim_api_key:
                self.classifier_llm = ChatOpenAI(
                    model=model_name,
                    api_key=krutrim_api_key,
                    base_url="https://cloud.olakrutrim.com/v1",
                    temperature=0.0
                )
        except Exception as e:
            print(f"Warning: Krutrim Classifier failed to init: {e}")

    def _load_qlora_pipeline(self) -> Any:
        """
        Loads the model EXACTLY like your working snippet.
        1. BitsAndBytes Config
        2. Load Base Model (Salesforce/codet5p-220m)
        3. Load Tokenizer
        4. Apply Adapter (PeftModel)
        """
        try:
            print(f"--- Loading Base Model: {self.base_model_id} ---")
            
            # 1. Quantization Config
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
            )

            # 2. Load Base Model
            base_model = AutoModelForSeq2SeqLM.from_pretrained(
                self.base_model_id,
                quantization_config=bnb_config,
                device_map="auto",
                trust_remote_code=True,
            )

            # 3. Load Tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.base_model_id,
                trust_remote_code=True,
                use_fast=False,
            )

            # 4. Load Adapter
            print(f"--- Loading Adapter: {self.offering_adapter_path} ---")
            model = PeftModel.from_pretrained(base_model, self.offering_adapter_path)
            model.eval()
            
            print("--- Model Loaded Successfully ---")
            return model

        except Exception as e:
            print(f"CRITICAL ERROR LOADING MODEL: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _get_update_file_path(self) -> str:
        return os.path.join(PROJECT_ROOT, self.UPDATE_FILE_NAME)

    def _execute(self, query_text: str) -> str:
        # Load model if not already loaded
        if not self.offering_model:
            self.offering_model = self._load_qlora_pipeline()
        
        if not self.offering_model: 
            return "Error: Model failed to load. Check console logs for 'CRITICAL ERROR'."

        print(f"--- Generating XML for: {query_text} ---")

        # 1. Generate
        try:
            inputs = self.tokenizer(query_text, return_tensors="pt").to(self.offering_model.device)
            with torch.no_grad():
                outputs = self.offering_model.generate(
                    input_ids=inputs["input_ids"], 
                    attention_mask=inputs["attention_mask"],
                    max_new_tokens=512, 
                    num_beams=4,
                    pad_token_id=self.tokenizer.pad_token_id, 
                    eos_token_id=self.tokenizer.eos_token_id
                )
            xml_output = self.tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
            print(f"Raw Output: {xml_output}")
        except Exception as e: 
            return f"Error inference: {e}"

        # 2. Extract & Correct
        try:
            soup = BeautifulSoup(xml_output, 'xml')
            offering_tag = soup.find('offering')
            if not offering_tag: return f"Error: Invalid XML generated. Output: {xml_output}"

            # --- SMART CORRECTION LOGIC (Matches your snippet) ---
            course_tag = offering_tag.find('course')
            if course_tag and course_tag.has_attr('courseNbr'):
                xml_course_nbr = course_tag['courseNbr']
                # Find real subject in user input (e.g. DLCS 101)
                pattern = re.compile(rf"([a-zA-Z]+)\s*{xml_course_nbr}", re.IGNORECASE)
                match = pattern.search(query_text)
                
                if match:
                    real_subject = match.group(1).upper()
                    generated_subject = course_tag.get('subject', '')
                    
                    if real_subject != generated_subject:
                        print(f"⚠️ Fixing Subject: {generated_subject} -> {real_subject}")
                        course_tag['subject'] = real_subject
                        
                        # Fix Title to match Subject_Number
                        course_tag['title'] = f"{real_subject}_{xml_course_nbr}"

            # 3. Save
            update_file_path = self._get_update_file_path()
            timestamp = datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Z %Y")
            xml_header = f"""<?xml version="1.0" encoding="UTF-8"?>
<offerings campus="woebegon" year="2010" term="Fal" dateFormat="yyyy/M/d" timeFormat="HHmm" created="{timestamp}" includeExams="none" incremental="true">"""
            
            with open(update_file_path, "w", encoding="utf-8") as f:
                f.write(f"{xml_header}\n{str(offering_tag)}\n\n</offerings>")

            return "Success: Update file refreshed."
        except Exception as e: return f"Error saving file: {e}"