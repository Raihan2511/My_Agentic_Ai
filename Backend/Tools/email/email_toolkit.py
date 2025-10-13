# from superagi.tools.base_tool import BaseToolkit, BaseTool, ToolConfiguration
# tools/email_toolkit.py
import os 
import sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
from typing import List
from Backend.tool_framework.base_tool import BaseTool
from Backend.tool_framework.base_toolkit import BaseToolkit
from Backend.tool_framework.tool_config import ToolConfiguration
# , ToolConfigKeyType
from abc import ABC
from typing import List
from Backend.Tools.email.read_email import ReadEmailTool
from Backend.Tools.email.send_email import SendEmailTool
# from Backend.Tools.email.send_email_attachment import SendEmailAttachmentTool
from Backend.types.key_type import ToolConfigKeyType


class EmailToolkit(BaseToolkit, ABC):
    name: str = "Email Toolkit"
    description: str = "Email Tool kit contains all tools related to sending email"

    def get_tools(self) -> List[BaseTool]:
        return [ReadEmailTool(), SendEmailTool()]

# , SendEmailAttachmentTool()

    def get_env_keys(self) -> List[ToolConfiguration]:
        return [
            ToolConfiguration(key="EMAIL_ADDRESS", key_type=ToolConfigKeyType.STRING, is_required= True, is_secret = False),
            ToolConfiguration(key="EMAIL_PASSWORD", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=True),
            ToolConfiguration(key="EMAIL_SIGNATURE", key_type=ToolConfigKeyType.STRING, is_required=False, is_secret=False),
            ToolConfiguration(key="EMAIL_DRAFT_MODE", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=False),
            ToolConfiguration(key="EMAIL_DRAFT_FOLDER", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=False),
            ToolConfiguration(key="EMAIL_SMTP_HOST", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=False),
            ToolConfiguration(key="EMAIL_SMTP_PORT", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=False),
            ToolConfiguration(key="EMAIL_IMAP_SERVER", key_type=ToolConfigKeyType.STRING, is_required=True, is_secret=False)
        ]