# # import_xml_tool.py

# from superagi.tools.base_tool import BaseTool
# from pydantic import BaseModel, Field
# from typing import Type
# import requests
# import os

# class ImportXMLInput(BaseModel):
#     xml_payload: str = Field(..., description="Validated UniTime XML to import")

# class ImportXMLTool(BaseTool):
#     name = "ImportXMLTool"
#     description = "Send validated XML to UniTime server for import"
#     args_schema: Type[BaseModel] = ImportXMLInput

#     def _run(self, xml_payload: str) -> str:
#         unitime_url = os.environ.get("UNITIME_IMPORT_URL")

#         if not unitime_url:
#             raise ValueError("UNITIME_IMPORT_URL must be set in environment")

#         response = requests.post(unitime_url, data=xml_payload, headers={"Content-Type": "application/xml"})

#         if response.status_code != 200:
#             return f"❌ Import failed: {response.status_code} - {response.text}"
#         return "✅ XML imported successfully"


# import_xml_tool.py
import os
import sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from Backend.tool_framework.base_tool import BaseTool

from pydantic import BaseModel, Field
from typing import Type
import requests

class ImportXMLInput(BaseModel):
    xml_payload: str = Field(..., description="Validated UniTime XML to import")

class ImportXMLTool(BaseTool):
    name = "ImportXMLTool"
    description = "Send validated XML to UniTime server for import"
    args_schema: Type[BaseModel] = ImportXMLInput

    def _execute(self, xml_payload: str) -> str:
        unitime_url = self.get_tool_config("UNITIME_IMPORT_URL")
        
        if not unitime_url:
            raise ValueError("UNITIME_IMPORT_URL must be configured")
        
        response = requests.post(
            unitime_url, 
            data=xml_payload, 
            headers={"Content-Type": "application/xml"}
        )
        
        if response.status_code != 200:
            return f"❌ Import failed: {response.status_code} - {response.text}"
        return "✅ XML imported successfully"
