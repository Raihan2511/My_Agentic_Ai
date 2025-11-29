import os
import sys
import torch
import re
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
    base_model_id: Optional[str] = None
    offering_adapter_path: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        self._initialize_classifier()
        self.base_model_id = self.get_tool_config("BASE_MODEL_ID")
        # POINT TO YOUR NEW V2 CHECKPOINT HERE
        self.offering_adapter_path = "/home/sysadm/Music/unitime_nlp/data_generator/Offering-nlp-to-xml_update_v2/checkpoint-875"

    def _initialize_classifier(self):
        # (Same as before, mainly for logging/fallback)
        if self.classifier_llm: return
        try:
            google_api_key = self.get_tool_config("GOOGLE_API_KEY")
            self.classifier_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", google_api_key=google_api_key, temperature=0.0)
        except Exception: pass

    def _load_qlora_pipeline(self, adapter_path: str) -> Any:
        try:
            if not self.tokenizer:
                self.tokenizer = AutoTokenizer.from_pretrained(self.base_model_id, trust_remote_code=True, use_fast=False)
            
            bnb_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16)
            base_model = AutoModelForSeq2SeqLM.from_pretrained(self.base_model_id, quantization_config=bnb_config, device_map="auto", trust_remote_code=True)
            model = PeftModel.from_pretrained(base_model, adapter_path)
            model.eval() 
            return model
        except Exception as e:
            return None

    def _get_update_file_path(self) -> str:
        return os.path.join(PROJECT_ROOT, self.UPDATE_FILE_NAME)

    def _execute(self, query_text: str) -> str:
        if not self.base_model_id: return "Error: Config missing."

        if not self.offering_model:
            self.offering_model = self._load_qlora_pipeline(self.offering_adapter_path)
        
        if not self.offering_model: return "Error: Model failed to load."

        # 1. Generate
        try:
            inputs = self.tokenizer(query_text, return_tensors="pt").to(self.offering_model.device)
            with torch.no_grad():
                outputs = self.offering_model.generate(
                    input_ids=inputs["input_ids"], attention_mask=inputs["attention_mask"],
                    max_new_tokens=512, num_beams=4,
                    pad_token_id=self.tokenizer.pad_token_id, eos_token_id=self.tokenizer.eos_token_id
                )
            xml_output = self.tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
        except Exception as e: return f"Error inference: {e}"

        # 2. Extract & Correct
        try:
            soup = BeautifulSoup(xml_output, 'xml')
            offering_tag = soup.find('offering')
            if not offering_tag: return f"Error: Invalid XML. {xml_output}"

            # --- SMART CORRECTION LOGIC ---
            course_tag = offering_tag.find('course')
            if course_tag and course_tag.has_attr('courseNbr'):
                xml_course_nbr = course_tag['courseNbr']
                # Find real subject in user input (e.g. DLCS)
                pattern = re.compile(rf"([a-zA-Z]+)\s*{xml_course_nbr}", re.IGNORECASE)
                match = pattern.search(query_text)
                
                if match:
                    real_subject = match.group(1).upper()
                    generated_subject = course_tag.get('subject', '')
                    
                    if real_subject != generated_subject:
                        print(f"⚠️ Fixing Subject: {generated_subject} -> {real_subject}")
                        course_tag['subject'] = real_subject
                        
                        # SMART TITLE CHECK:
                        # Only reset title if it looks generic (DLC_101). 
                        # If it is custom (Advanced AI), KEEP IT.
                        current_title = course_tag.get('title', '')
                        generic_pattern = f"{generated_subject}_{xml_course_nbr}"
                        
                        if current_title == generic_pattern or current_title == "":
                            course_tag['title'] = f"{real_subject}_{xml_course_nbr}"
                        else:
                            print(f"ℹ️ Preserving custom title: {current_title}")

            # 3. Save
            update_file_path = self._get_update_file_path()
            timestamp = datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Z %Y")
            xml_header = f"""<?xml version="1.0" encoding="UTF-8"?>
<offerings campus="woebegon" year="2010" term="Fal" dateFormat="yyyy/M/d" timeFormat="HHmm" created="{timestamp}" includeExams="none" incremental="true">"""
            
            with open(update_file_path, "w", encoding="utf-8") as f:
                f.write(f"{xml_header}\n{str(offering_tag)}\n\n</offerings>")

            return "Success: Update file refreshed."
        except Exception as e: return f"Error saving file: {e}"