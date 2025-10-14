# unitime_workflow_tool.py
import os
import sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from Backend.tool_framework.base_tool import BaseTool

from pydantic import BaseModel, Field
from typing import Type
import json

from Backend.Tools.unitime_scheduling.generate_xml_tool import GenerateXMLTool
from Backend.Tools.unitime_scheduling.validate_xml_tool import ValidateXMLTool
from Backend.Tools.unitime_scheduling.import_xml_tool import ImportXMLTool

class UnitimeWorkflowInput(BaseModel):
    prompt: str = Field(..., description="Natural language scheduling request")
    ground_truth_xml: str = Field(..., description="Reference XML for validation and ID mapping")
    auto_import: bool = Field(default=False, description="Auto-import if validation passes")

class UnitimeWorkflowTool(BaseTool):
    name = "UnitimeWorkflowTool"
    description = "Complete UniTime scheduling workflow: Generate XML → Validate → Import (if valid)"
    args_schema: Type[BaseModel] = UnitimeWorkflowInput

    def _execute(self, prompt: str, ground_truth_xml: str, auto_import: bool = False) -> str:
        results = {
            "step": "",
            "status": "",
            "details": {},
            "xml_generated": "",
            "final_result": ""
        }
        
        try:
            # STEP 1: Generate XML
            results["step"] = "1_generate"
            generator = GenerateXMLTool()
            # Pass required config to sub-tools
            generator.toolkit_config = self.toolkit_config
            
            xml_output = generator._execute(prompt, ground_truth_xml)
            results["xml_generated"] = xml_output
            results["details"]["generation"] = "✅ XML generated successfully"
            
            # STEP 2: Validate XML
            results["step"] = "2_validate"
            validator = ValidateXMLTool()
            validator.toolkit_config = self.toolkit_config
            
            validation_result = validator._execute(xml_output, ground_truth_xml)
            validation_dict = eval(validation_result)  # Convert string back to dict
            results["details"]["validation"] = validation_dict
            
            # Check if validation passed
            is_valid = validation_dict.get('is_valid', False)
            semantic_accuracy = validation_dict.get('semantic_accuracy', 0)
            
            if not is_valid:
                results["status"] = "❌ FAILED"
                results["final_result"] = f"Validation failed - XML is malformed"
                return json.dumps(results, indent=2)
            
            if semantic_accuracy < 0.8:  # Threshold for semantic accuracy
                results["status"] = "⚠️ WARNING"
                results["final_result"] = f"XML valid but low semantic accuracy: {semantic_accuracy}"
                if not auto_import:
                    return json.dumps(results, indent=2)
            
            # STEP 3: Import XML (if auto_import is True)
            if auto_import:
                results["step"] = "3_import"
                importer = ImportXMLTool()
                importer.toolkit_config = self.toolkit_config
                
                import_result = importer._execute(xml_output)
                results["details"]["import"] = import_result
                
                if "✅" in import_result:
                    results["status"] = "✅ SUCCESS"
                    results["final_result"] = "Complete workflow successful - XML imported to UniTime"
                else:
                    results["status"] = "❌ IMPORT_FAILED"
                    results["final_result"] = f"Validation passed but import failed: {import_result}"
            else:
                results["status"] = "✅ READY_FOR_IMPORT"
                results["final_result"] = "XML generated and validated successfully. Ready for manual import."
            
            return json.dumps(results, indent=2)
            
        except Exception as e:
            results["status"] = "❌ ERROR"
            results["final_result"] = f"Error in {results['step']}: {str(e)}"
            return json.dumps(results, indent=2)