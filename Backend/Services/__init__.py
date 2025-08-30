from pydantic import BaseModel

class EmailEnvelope(BaseModel):
    sender: str
    subject: str
    body: str
