# /home/sysadm/Music/My_Agentic_Ai/Backend/Tools/university/update_course_file.py
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

# --- Project Path Setup ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from Backend.tool_framework.base_tool import BaseTool
# --- IMPORT SINGLETON ---
from Backend.Services.model_singleton import global_model_manager

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

    def _get_update_file_path(self) -> str:
        return os.path.join(PROJECT_ROOT, self.UPDATE_FILE_NAME)

    def _execute(self, query_text: str) -> str:
        # --- CHANGED: GET MODEL FROM SINGLETON ---
        # 1. Load Model (From Singleton)
        if global_model_manager.offering_model is None:
            print("⚠️ Offering model not cached. Loading now...")
            global_model_manager.load_models()
        
        self.offering_model = global_model_manager.offering_model
        self.tokenizer = global_model_manager.offering_tokenizer
        
        if not self.offering_model: 
            return "Error: Model failed to load. Check console for details."
        # -----------------------------------------

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
                        
                        # Fix Title to match Subject_Number - REMOVED to prevent overwriting user title
                        # course_tag['title'] = f"{real_subject}_{xml_course_nbr}"

            # 3. Save
            update_file_path = self._get_update_file_path()
            timestamp = datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Z %Y")
            xml_header = f"""<?xml version="1.0" encoding="UTF-8"?>
<offerings campus="woebegon" year="2010" term="Fal" dateFormat="yyyy/M/d" timeFormat="HHmm" created="{timestamp}" includeExams="none" incremental="true">"""
            
            with open(update_file_path, "w", encoding="utf-8") as f:
                f.write(f"{xml_header}\n{str(offering_tag)}\n\n</offerings>")

            return "Success: Update file refreshed."
        except Exception as e: return f"Error saving file: {e}"