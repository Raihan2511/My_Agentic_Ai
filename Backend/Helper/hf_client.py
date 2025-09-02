import os
from typing import Optional
from huggingface_hub import InferenceClient

class HFClient:
    def __init__(self):
        self.model_id = os.getenv("HF_MODEL_ID")
        self.token = os.getenv("HF_TOKEN")
        self.is_enabled = bool(self.model_id and self.token)
        self._client: Optional[InferenceClient] = None
        if self.is_enabled:
            self._client = InferenceClient(model=self.model_id, token=self.token)

    @staticmethod
    def safe(s: str) -> str:
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def nlp2xml(self, body: str, intent_label: str) -> str:
        if not self._client:
            raise RuntimeError("HFClient not configured")
        prompt = (
            "You convert email text to XML that conforms to the DTD labeled: "
            f"{intent_label}. Only output XML.\nEmail:\n{body}"
        )
        return self._client.text_generation(prompt, max_new_tokens=512)
