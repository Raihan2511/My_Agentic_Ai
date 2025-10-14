# # generate_xml_tool.py

# from superagi.tools.base_tool import BaseTool
# from pydantic import BaseModel, Field
# from typing import Type
# import requests
# import os

# from superagi.helper.unitime import UnitimeXMLHelper

# class GenerateXMLInput(BaseModel):
#     prompt: str = Field(..., description="User scheduling request in natural language")
#     ground_truth_xml: str = Field(..., description="Reference XML for ID correction")

# class GenerateXMLTool(BaseTool):
#     name = "GenerateXMLTool"
#     description = "Generate UniTime-compatible XML from natural language prompt using HF model"
#     args_schema: Type[BaseModel] = GenerateXMLInput

#     def _run(self, prompt: str, ground_truth_xml: str) -> str:
#         hf_token = os.environ.get("HF_API_TOKEN")
#         hf_endpoint = os.environ.get("HF_MODEL_ENDPOINT")

#         if not hf_token or not hf_endpoint:
#             raise ValueError("HF_API_TOKEN and HF_MODEL_ENDPOINT must be set in environment")

#         headers = {
#             "Authorization": f"Bearer {hf_token}",
#             "Content-Type": "application/json"
#         }

#         payload = {"inputs": prompt}
#         response = requests.post(hf_endpoint, headers=headers, json=payload)

#         if response.status_code != 200:
#             raise RuntimeError(f"HF API call failed: {response.text}")

#         raw_xml = response.json()[0]['generated_text']

#         # Fix malformed XML
#         fixed_xml = UnitimeXMLHelper.fix_xml(raw_xml)

#         # Replace IDs
#         id_map = UnitimeXMLHelper.extract_id_map(ground_truth_xml)
#         final_xml = UnitimeXMLHelper.replace_ids(fixed_xml, id_map)

#         return final_xml

# generate_xml_tool.py
import os
import sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from Backend.tool_framework.base_tool import BaseTool
from pydantic import BaseModel, Field
from typing import Type
import requests
from Backend.Helper.unitime import UnitimeXMLHelper

class GenerateXMLInput(BaseModel):
    prompt: str = Field(..., description="User scheduling request in natural language")
    ground_truth_xml: str = Field(..., description="Reference XML for ID correction")

class GenerateXMLTool(BaseTool):
    name = "GenerateXMLTool"
    description = "Generate UniTime-compatible XML from natural language prompt using HF model"
    args_schema: Type[BaseModel] = GenerateXMLInput

    def _execute(self, prompt: str, ground_truth_xml: str) -> str:
        hf_token = self.get_tool_config("HF_API_TOKEN")
        hf_endpoint = self.get_tool_config("HF_MODEL_ENDPOINT")

        if not hf_token or not hf_endpoint:
            raise ValueError("HF_API_TOKEN and HF_MODEL_ENDPOINT must be configured")

        headers = {
            "Authorization": f"Bearer {hf_token}",
            "Content-Type": "application/json"
        }

        payload = {"inputs": prompt}
        response = requests.post(hf_endpoint, headers=headers, json=payload)

        if response.status_code != 200:
            raise RuntimeError(f"HF API call failed: {response.text}")

        raw_xml = response.json()[0]['generated_text']
        
        # Fix malformed XML
        fixed_xml = UnitimeXMLHelper.fix_xml(raw_xml)
        
        # Replace IDs
        id_map = UnitimeXMLHelper.extract_id_map(ground_truth_xml)
        final_xml = UnitimeXMLHelper.replace_ids(fixed_xml, id_map)
        
        return final_xml
