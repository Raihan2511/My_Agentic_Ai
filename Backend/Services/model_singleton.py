# Backend/Services/model_singleton.py
import os
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel
import dotenv

dotenv.load_dotenv()

class ModelSingleton:
    _instance = None
    
    def __init__(self):
        # --- Offering Model Attributes (770m) ---
        self.offering_model = None
        self.offering_tokenizer = None
        self.offering_base_id = os.getenv("BASE_MODEL_ID", "Salesforce/codet5p-770m")
        self.offering_adapter = os.getenv("OFFERING_MODEL_PATH")

        # --- Preference Model Attributes (220m) ---
        self.preference_model = None
        self.preference_tokenizer = None
        self.preference_base_id = os.getenv("BASE_MODEL_ID1", "Salesforce/codet5p-220m")
        self.preference_adapter = os.getenv("PREFERENCE_MODEL_PATH")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ModelSingleton()
        return cls._instance

    def _load_pipeline(self, base_id, adapter_path, model_name):
        """Helper to load a specific model + adapter."""
        print(f"⏳ [Singleton] Loading {model_name} (Base: {base_id})...")
        try:
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
            )
            
            base_model = AutoModelForSeq2SeqLM.from_pretrained(
                base_id,
                quantization_config=bnb_config,
                device_map="auto",
                trust_remote_code=True,
            )
            
            tokenizer = AutoTokenizer.from_pretrained(
                base_id,
                trust_remote_code=True,
                use_fast=False
            )
            
            print(f"   ... Applying Adapter: {adapter_path}")
            model = PeftModel.from_pretrained(base_model, adapter_path)
            model.eval()
            
            print(f"✅ [Singleton] {model_name} Ready.")
            return model, tokenizer
        except Exception as e:
            print(f"❌ [Singleton] Failed to load {model_name}: {e}")
            return None, None

    def load_models(self):
        """Loads BOTH models into memory on startup."""
        # 1. Load Offering Model
        if self.offering_model is None:
            self.offering_model, self.offering_tokenizer = self._load_pipeline(
                self.offering_base_id, self.offering_adapter, "Offering Model"
            )
        
        # 2. Load Preference Model
        if self.preference_model is None:
            self.preference_model, self.preference_tokenizer = self._load_pipeline(
                self.preference_base_id, self.preference_adapter, "Preference Model"
            )

# Create the global instance
global_model_manager = ModelSingleton.get_instance()