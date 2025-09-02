from langchain_core.tools import tool
# from .router import route_intent
# from .nlp2xml import nlp2xml
# from .validate import validate_xml

# @tool("route_intent", return_direct=True)
# def lc_route_intent(email: dict) -> str:
#     return route_intent(type("E", (), email))

# @tool("nlp2xml", return_direct=True)
# def lc_nlp2xml(email: dict, intent_label: str) -> str:
#     return nlp2xml(type("E", (), email), intent_label)

# @tool("validate_xml", return_direct=True)
# def lc_validate_xml(xml: str, intent_label: str) -> str:
#     return validate_xml(xml, intent_label)

# def tools():
#     return [lc_route_intent, lc_nlp2xml, lc_validate_xml]


# File: Backend/Tools/email_nlp_xml/lc_tools.py

from langchain_core.tools import tool
from .router import route_intent
from .nlp2xml import nlp2xml
from .validate import validate_xml

@tool("route_intent", return_direct=True)
def lc_route_intent(email: dict) -> str:
    """
    Determines the primary intent of an email. Use this as the first step
    to understand what the email is about, for example, 'order_inquiry' 
    or 'customer_complaint'. The input is the email dictionary.
    """
    return route_intent(type("E", (), email))

@tool("nlp2xml", return_direct=True)
def lc_nlp2xml(email: dict, intent_label: str) -> str:
    """
    Converts the natural language of an email into a structured XML format 
    based on its intent. Use this tool *after* the intent has been identified 
    by the 'route_intent' tool.
    """
    return nlp2xml(type("E", (), email), intent_label)

@tool("validate_xml", return_direct=True)
def lc_validate_xml(xml: str, intent_label: str) -> str:
    """
    Validates a given XML string against the appropriate schema for its intent label.
    Use this as the final step to ensure the generated XML is correct and well-formed
    before finishing the task.
    """
    return validate_xml(xml, intent_label)

def tools():
    return [lc_route_intent, lc_nlp2xml, lc_validate_xml]