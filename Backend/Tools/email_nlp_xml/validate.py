from Backend.Helper.dtds import DTDRegistry
from Backend.Helper.xml_utils import XMLValidator

def validate_xml(xml: str, intent_label: str) -> str:
    dtd = DTDRegistry().get(intent_label)
    return XMLValidator(dtd).validate_and_repair(xml)
