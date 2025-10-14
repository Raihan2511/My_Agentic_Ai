# # validtae_xml_tool.py

# from superagi.tools.base_tool import BaseTool
# from pydantic import BaseModel, Field
# from typing import Type

# from superagi.helper.unitime import UnitimeXMLHelper

# class ValidateXMLInput(BaseModel):
#     prediction_xml: str = Field(..., description="Generated XML to validate")
#     ground_truth_xml: str = Field(..., description="Reference XML for validation")

# class ValidateXMLTool(BaseTool):
#     name = "ValidateXMLTool"
#     description = "Validate XML for correctness and semantic match"
#     args_schema: Type[BaseModel] = ValidateXMLInput

#     def _run(self, prediction_xml: str, ground_truth_xml: str) -> str:
#         results = {}

#         results['is_valid'] = UnitimeXMLHelper.is_valid_xml(prediction_xml)
#         results['exact_match'] = UnitimeXMLHelper.calculate_exact_match(prediction_xml, ground_truth_xml)
#         results['bleu_score'] = UnitimeXMLHelper.calculate_bleu_score(prediction_xml, ground_truth_xml)
#         results['semantic_accuracy'] = UnitimeXMLHelper.calculate_semantic_accuracy(prediction_xml, ground_truth_xml)

#         return str(results)


# validate_xml_tool.py

import os
import sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from Backend.tool_framework.base_tool import BaseTool

from pydantic import BaseModel, Field
from typing import Type
from Backend.Helper.unitime import UnitimeXMLHelper

class ValidateXMLInput(BaseModel):
    prediction_xml: str = Field(..., description="Generated XML to validate")
    ground_truth_xml: str = Field(..., description="Reference XML for validation")

class ValidateXMLTool(BaseTool):
    name = "ValidateXMLTool"
    description = "Validate XML for correctness and semantic match"
    args_schema: Type[BaseModel] = ValidateXMLInput

    def _execute(self, prediction_xml: str, ground_truth_xml: str) -> str:
        results = {}
        
        results['is_valid'] = UnitimeXMLHelper.is_valid_xml(prediction_xml)
        results['exact_match'] = UnitimeXMLHelper.calculate_exact_match(prediction_xml, ground_truth_xml)
        results['bleu_score'] = UnitimeXMLHelper.calculate_bleu_score(prediction_xml, ground_truth_xml)
        results['semantic_accuracy'] = UnitimeXMLHelper.calculate_semantic_accuracy(prediction_xml, ground_truth_xml)
        
        return str(results)