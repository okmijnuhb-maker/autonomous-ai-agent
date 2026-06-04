# tools/email_tool.py

import json
import logging
import re
import smtplib
import os
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Optional, List, Dict
from dotenv import load_dotenv

log = logging.getLogger(__name__)

load_dotenv(Path("C:/educational files/advanced_agent/.env"))

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SENT_LOG_PATH = "C:/educational files/advanced_agent/memory/sent_emails.json"


def validate_email(email: str) -> bool:
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w{2,}$"
    valid = bool(re.match(pattern, email.strip()))
    log.info(f"Email validation: {email} — {'valid' if valid else 'invalid'}")
    return valid


def build_draft(
    to: List[str],
    subject: str,
    body: str,
    cc: Optional[List[str]] = None,
    attachments: Optional[List[str]] = None
) -> Dict:
    invalid = [e for e in to if not validate_email(e)]
    if invalid:
        raise ValueError(f"Invalid recipient emails: {invalid}")
    draft = {
        "to": to,
        "cc": cc or [],
        "subject": subject,
        "body": body,
        "attachments": attachments or [],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    log.info(f"Draft built — to: {to} | subject: {subject}")
    return draft


def build_mime(draft: Dict) -> MIMEMultipart:
    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = ", ".join(draft["to"])
    msg["Subject"] = draft["subject"]
    if draft["cc"]:
        msg["Cc"] = ", ".join(draft["cc"])
    msg.attach(MIMEText(draft["body"], "plain"))
    for filepath in draft["attachments"]:
        path = Path(filepath)
        if not path.exists():
            log.warning(f"Attachment not found: {filepath}")
            continue
        with open(path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={path.name}")
        msg.attach(part)
        log.info(f"Attachment added: {path.name}")
    return msg


def connect_smtp() -> smtplib.SMTP:
    if not SMTP_USER or not SMTP_PASS:
        raise EnvironmentError("SMTP_USER or SMTP_PASS not set in .env")
    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
    server.ehlo()
    server.starttls()
    server.login(SMTP_USER, SMTP_PASS)
    log.info(f"SMTP connected — {SMTP_HOST}:{SMTP_PORT}")
    return server


class SentLogManager:
    def __init__(self, path: str = SENT_LOG_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.log_data: List[Dict] = self._load()
        log.info(f"Sent log loaded — {len(self.log_data)} past emails")

    def _load(self) -> List[Dict]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def save(self, draft: Dict, status: str) -> None:
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "to": draft["to"],
            "cc": draft["cc"],
            "subject": draft["subject"],
            "body_preview": draft["body"][:100],
            "attachments": draft["attachments"],
            "status": status
        }
        self.log_data.append(entry)
        self.path.write_text(json.dumps(self.log_data, indent=2), encoding="utf-8")
        log.info(f"Sent log updated — total: {len(self.log_data)}")

    def get_all(self) -> List[Dict]:
        return self.log_data.copy()

    def get_last(self) -> Optional[Dict]:
        return self.log_data[-1] if self.log_data else None

    def clear(self) -> None:
        self.log_data.clear()
        self.path.write_text("[]", encoding="utf-8")
        log.info("Sent log cleared")

    def summary(self) -> str:
        return f"Total emails sent: {len(self.log_data)}"


sent_log = SentLogManager()


def send_email(
    to: List[str],
    subject: str,
    body: str,
    cc: Optional[List[str]] = None,
    attachments: Optional[List[str]] = None
) -> str:
    try:
        draft = build_draft(to, subject, body, cc, attachments)
        msg = build_mime(draft)
        all_recipients = draft["to"] + draft["cc"]
        server = connect_smtp()
        server.sendmail(SMTP_USER, all_recipients, msg.as_string())
        server.quit()
        sent_log.save(draft, "sent")
        log.info(f"Email sent successfully to: {to}")
        return f"Email sent successfully to: {', '.join(to)}"
    except Exception as e:
        log.error(f"Email send failed: {e}")
        if "draft" in dir():
            sent_log.save(draft, f"failed: {e}")
        return f"Email send failed: {e}"