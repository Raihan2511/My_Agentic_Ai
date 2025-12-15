# /home/sysadm/Music/My_Agentic_Ai/Backend/Tools/university/add_preference_to_batch.py
import os
import sys
import torch
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

class AddPreferenceInput(BaseModel):
    query_text: str = Field(..., description="The full, original text requesting the preference update.")

class AddPreferenceToBatchTool(BaseTool):
    name: str = "Add_Preference_to_Batch"
    description: str = "Processes a request to add Instructor Preferences (Time, Room, Distribution) and appends XML to the batch file."
    args_schema: Type[BaseModel] = AddPreferenceInput
    
    BATCH_FILE_NAME: ClassVar[str] = "unitime_batch.xml"

    # --- Attributes ---
    classifier_llm: Optional[Any] = None
    pref_model: Optional[Any] = None
    tokenizer: Optional[Any] = None

    def __init__(self, **data):
        super().__init__(**data)
        self._initialize_classifier()

    def _initialize_classifier(self):
        if self.classifier_llm: return
        try:
            # --- KRUTRIM CONFIGURATION ---
            krutrim_api_key = self.get_tool_config("KRUTRIM_API_KEY") or os.getenv("KRUTRIM_API_KEY")
            model_name = os.getenv("LLM_MODEL", "Qwen3-Next-80B-A3B-Instruct")

            if not krutrim_api_key:
                print("Warning: KRUTRIM_API_KEY missing. Classifier will not work.")
                return

            self.classifier_llm = ChatOpenAI(
                model=model_name,
                api_key=krutrim_api_key,
                base_url="https://cloud.olakrutrim.com/v1",
                temperature=0.0
            )
        except Exception as e:
            print(f"Error: Failed to initialize Classifier LLM. Exception: {e}")

    def _sanitize_prompt_for_model(self, text: str) -> str:
        # 1. Use LLM to extract the core intent (clean up email headers, signatures, etc.)
        system_prompt = """
        You are a Data Formatter for University Instructor Preferences. 
        Extract the core preference request and format it exactly like these examples:
        
        Examples:
        - "Instructor Doe needs a Projector" -> "For instructor Doe, make the room preference Required for Projector."
        - "Prof Smith cannot teach on Mondays" -> "For instructor Smith, make the time slot M prohibited."
        - "JOE DOE needs time slot T 1630-1830 required" -> "For instructor JOE DOE, make the time slot T 1630-1830 required."
        
        Input Text:
        """
        try:
            full_prompt = f"{system_prompt}\n\"{text}\"\n\nOUTPUT:"
            response = self.classifier_llm.invoke(full_prompt)
            clean_text = response.content.strip().strip('"')
            return clean_text
        except Exception as e:
            print(f"Error sanitizing prompt: {e}")
            return text

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
        if not self.classifier_llm: return "Error: Classifier (Krutrim) not loaded."

        # 1. Load Preference Model (From Singleton)
        if global_model_manager.preference_model is None:
            print("⚠️ Preference model not cached. Loading now...")
            global_model_manager.load_models()
        
        self.pref_model = global_model_manager.preference_model
        self.tokenizer = global_model_manager.preference_tokenizer
        
        if not self.pref_model: 
            return "Error: Preference Model failed to load from Singleton."

        # 2. Sanitize & Format
        clean_text = self._sanitize_prompt_for_model(query_text)
        
        # --- CRITICAL FIX: MATCH TRAINING DATA FORMAT ---
        # Training used: f"Prompt: {prompt}\nXML:"
        formatted_input = f"Prompt: {clean_text}\nXML:"
        
        print(f"Preference Model Input: {formatted_input}")

        # 3. Generate
        try:
            inputs = self.tokenizer(formatted_input, return_tensors="pt").to(self.pref_model.device)
            with torch.no_grad():
                outputs = self.pref_model.generate(
                    input_ids=inputs["input_ids"], 
                    attention_mask=inputs["attention_mask"],
                    max_new_tokens=512, 
                    num_beams=4,
                    pad_token_id=self.tokenizer.pad_token_id, 
                    eos_token_id=self.tokenizer.eos_token_id,
                )
            xml_output = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # --- CRITICAL FIX: REMOVE ARTIFACTS ---
            # Training notebook showed explicit removal of <pad>
            xml_output = xml_output.replace("<pad>", "").strip()
            
        except Exception as e:
            return f"Error during inference: {e}"

        # 4. Insert into File
        try:
            # Logic: Extract the relevant tag. Usually <instructorCoursePref>, <roomPref>, etc.
            # We'll assume the model outputs a valid XML block.
            ai_xml = BeautifulSoup(xml_output, 'xml')
            
            # Find the first meaningful child tag
            pref_tag = ai_xml.find(True) 
            
            if not pref_tag: return f"Error: Invalid XML. Output: {xml_output}"

            pref_block = str(pref_tag)
            
            self._ensure_batch_file_exists()
            batch_file_path = self._get_batch_file_path()

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