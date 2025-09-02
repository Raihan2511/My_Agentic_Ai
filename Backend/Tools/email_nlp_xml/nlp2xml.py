from textwrap import dedent
from Backend.Helper.hf_client import HFClient

TEMPLATES = {
    "meeting_v1": lambda body: f"""
        <meeting>
          <title>{HFClient.safe(body)[:60]}</title>
          <participants></participants>
          <datetime></datetime>
          <location></location>
          <notes>{HFClient.safe(body)}</notes>
        </meeting>
    """,
    "order_v1": lambda body: f"""
        <order>
          <items></items>
          <shipping_address></shipping_address>
          <notes>{HFClient.safe(body)}</notes>
        </order>
    """,
    "leave_v1": lambda body: f"""
        <leave_request>
          <employee></employee>
          <start_date></start_date>
          <end_date></end_date>
          <reason>{HFClient.safe(body)}</reason>
        </leave_request>
    """,
}

def nlp2xml(email_env, intent_label: str) -> str:
    client = HFClient()
    body = email_env.body
    if client.is_enabled:
        return client.nlp2xml(body, intent_label)
    fn = TEMPLATES.get(intent_label) or TEMPLATES["meeting_v1"]
    return dedent(fn(body)).strip()
