from . import EmailEnvelope

def fetch_latest_dummy() -> EmailEnvelope:
    return EmailEnvelope(
        sender="alice@example.com",
        subject="PTO",
        body="I'd like vacation from Sept 10–12."
    )
