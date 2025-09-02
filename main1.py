import sys
import os

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_ROOT)
import typer
from rich import print
from dotenv import load_dotenv
from Backend.Services import EmailEnvelope
from Backend.Agents.email_agents.llm_runner import run_once

app = typer.Typer()

@app.command()
def main(text: str, sender: str = "user@example.com", subject: str = "CLI"):
    load_dotenv()
    env = EmailEnvelope(sender=sender, subject=subject, body=text)
    xml = run_once(env)
    print("\n[bold]Final XML[/bold]:\n")
    print(xml)

if __name__ == "__main__":
    app()
