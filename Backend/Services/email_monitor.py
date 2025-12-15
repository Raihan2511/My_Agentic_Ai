import asyncio
import os
import sys
import logging
import email
import random
from email.utils import parseaddr

# Setup Paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# --- IMPORTS FROM YOUR SYSTEM ---
from Backend.Helper.imap_email import ImapEmail
from Backend.Helper.read_email_helper import ReadEmail
from Backend.Tools.email.send_email import SendEmailTool
from kurt_multi_agent import app as agent_app

# Logging
logger = logging.getLogger("EmailMonitor")

# Polling interval (seconds)
CHECK_INTERVAL = 20

# Allowed senders (exact match)
ALLOWED_SENDERS = {
    "uraihan2511@gmail.com"
}


class EmailMonitorService:
    def __init__(self):
        self.imap_helper = ImapEmail()
        self.read_helper = ReadEmail()
        self.send_tool = SendEmailTool()

        self.is_running = False

        self.email_address = os.getenv("EMAIL_ADDRESS")
        self.email_password = os.getenv("EMAIL_PASSWORD")
        self.imap_server = os.getenv("EMAIL_IMAP_SERVER")

    # ------------------------------------------------------------------
    # ASYNC ENTRYPOINT (FastAPI lifespan safe)
    # ------------------------------------------------------------------
    async def start(self):
        self.is_running = True
        logger.info("📧 Email Monitor Started")

        while self.is_running:
            try:
                await asyncio.to_thread(self._check_for_new_tasks_sync)
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")

            # Add jitter to avoid IMAP rate limiting
            await asyncio.sleep(CHECK_INTERVAL + random.uniform(1, 5))

    # ------------------------------------------------------------------
    # SYNC THREAD (IMAP + blocking work)
    # ------------------------------------------------------------------
    def _check_for_new_tasks_sync(self):
        conn = None

        try:
            conn = self.imap_helper.imap_open(
                "INBOX",
                self.email_address,
                self.email_password,
                self.imap_server
            )
            conn.select("INBOX")

            status, messages_data = conn.search(None, "(UNSEEN)")
            if status != "OK" or not messages_data[0]:
                return

            for msg_id in messages_data[0].split():
                self._process_single_email(conn, msg_id)

        except Exception as e:
            logger.error(f"IMAP processing error: {e}")

        finally:
            if conn:
                try:
                    conn.logout()
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # SINGLE EMAIL HANDLER
    # ------------------------------------------------------------------
    def _process_single_email(self, conn, msg_id):
        try:
            res, msg_data = conn.fetch(msg_id, "(RFC822)")
            raw_msg = email.message_from_bytes(msg_data[0][1])

            # Secure sender parsing
            _, sender_email = parseaddr(raw_msg.get("From", ""))
            sender_email = sender_email.lower()

            if sender_email not in ALLOWED_SENDERS:
                logger.warning(f"⛔ Unauthorized sender: {sender_email}")
                return

            subject = raw_msg.get("Subject", "No Subject")

            body = self._extract_body(raw_msg)
            clean_body = self.read_helper.clean_email_body(body)

            # Remove quoted replies
            clean_body = clean_body.split("On ")[0].strip()

            logger.info(f"📩 Processing email from {sender_email}")

            # Run agent safely in this thread
            ai_result = self._run_agent_sync(clean_body)

            self._send_reply(sender_email, subject, ai_result)

        except Exception as e:
            logger.error(f"Failed processing email {msg_id}: {e}")

    # ------------------------------------------------------------------
    # EMAIL BODY EXTRACTION
    # ------------------------------------------------------------------
    def _extract_body(self, msg):
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                    payload = part.get_payload(decode=True)
                    if payload:
                        return payload.decode(errors="ignore")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                return payload.decode(errors="ignore")
        return ""

    # ------------------------------------------------------------------
    # SAFE AGENT EXECUTION (NO asyncio.run)
    # ------------------------------------------------------------------
    def _run_agent_sync(self, user_text: str) -> str:
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self._run_agent_async(user_text))
        finally:
            loop.close()

    async def _run_agent_async(self, user_text: str) -> str:
        inputs = {"messages": [("user", user_text)]}
        final_response = "Processed, but no output was generated."

        async for event in agent_app.astream(inputs):
            for output in event.values():
                if "messages" in output:
                    final_response = output["messages"][-1].content

        return final_response

    # ------------------------------------------------------------------
    # SEND EMAIL REPLY
    # ------------------------------------------------------------------
    def _send_reply(self, to_email: str, subject: str, body: str):
        reply_subject = f"Re: {subject}"
        reply_body = (
            "Hello,\n\n"
            "Your request has been processed.\n"
            "--------------------------------------\n"
            f"{body}\n"
            "--------------------------------------\n"
            "Best regards,\nUniversity AI Bot"
        )

        self.send_tool._execute(
            to=to_email,
            subject=reply_subject,
            body=reply_body
        )

        logger.info(f"✅ Reply sent to {to_email}")


# Singleton instance
email_monitor = EmailMonitorService()
