import os
from dotenv import load_dotenv
from Backend.Services import EmailEnvelope
from Backend.Tools.email_nlp_xml.lc_tools import tools as email_tools

# Gemini client (with graceful fallback)
try:
    import google.generativeai as genai
except Exception:
    genai = None

def _mock_run(email_env):
    # Deterministic fallback: route -> nlp2xml -> validate
    ts = email_tools()
    label = ts[0].invoke({"sender": email_env.sender, "subject": email_env.subject, "body": email_env.body})
    xml   = ts[1].invoke({"sender": email_env.sender, "subject": email_env.subject, "body": email_env.body}, label)
    final = ts[2].invoke(xml, label)
    return final

def run_once(email_env: EmailEnvelope) -> str:
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or genai is None:
        return _mock_run(email_env)

    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")

    # Convert LangChain tools to Gemini tool schema
    ts = email_tools()
    tool_defs = [t.to_dict() for t in ts]  # LC Tools expose JSON-schema Gemini can use
    model = genai.GenerativeModel(model_name)
    chat = model.start_chat(tools=tool_defs)

    system = (
        "You orchestrate tools to produce valid XML under the chosen DTD.\n"
        "Always call tools in order: route_intent → nlp2xml → validate_xml."
    )
    user = f"Email\nSender: {email_env.sender}\nSubject: {email_env.subject}\nBody:\n{email_env.body}"

    resp = chat.send_message([{"role": "user", "parts": [system]}, {"role": "user", "parts": [user]}])
    # If Gemini didn't actually tool-call, take text as final; else, you may need to inspect tool outputs.
    return getattr(resp, "text", None) or _mock_run(email_env)
