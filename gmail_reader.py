import imaplib
import email
from email.header import decode_header
from dotenv import load_dotenv
import os
import re

load_dotenv()


def decode_mime_words(s: str) -> str:
    if not s:
        return ""
    parts = decode_header(s)
    decoded = []

    for part, enc in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(enc or "utf-8", errors="ignore"))
        else:
            decoded.append(part)

    return "".join(decoded)


def clean_email_text(text: str) -> str:
    if not text:
        return ""

    # elimină quoted replies de tip "On Fri ... wrote:"
    text = re.split(r"\nOn .*wrote:", text)[0]

    # elimină liniile care încep cu >
    lines = text.splitlines()
    cleaned_lines = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith(">"):
            continue

        # elimină linii foarte inutile
        if stripped.lower().startswith("from:"):
            continue
        if stripped.lower().startswith("subject:"):
            continue
        if stripped.lower().startswith("to:"):
            continue
        if stripped.lower().startswith("sent:"):
            continue

        cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)

    # spații multiple
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


def extract_first_url(text: str) -> str:
    if not text:
        return ""

    match = re.search(r"(https?://[^\s]+|www\.[^\s]+)", text)
    if match:
        return match.group(0)

    return ""


def extract_text_from_message(msg) -> str:
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            if content_type == "text/plain" and "attachment" not in content_disposition:
                try:
                    body = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8",
                        errors="ignore"
                    )
                    break
                except Exception:
                    continue
    else:
        try:
            body = msg.get_payload(decode=True).decode(
                msg.get_content_charset() or "utf-8",
                errors="ignore"
            )
        except Exception:
            body = ""

    return clean_email_text(body)


def get_latest_unread_email():
    email_user = os.getenv("EMAIL_USER")
    email_pass = os.getenv("EMAIL_PASS")

    if not email_user or not email_pass:
        raise ValueError("EMAIL_USER sau EMAIL_PASS lipsesc din fișierul .env")

    mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    mail.login(email_user, email_pass)
    mail.select("inbox")

    status, messages = mail.search(None, "UNSEEN")
    if status != "OK":
        mail.logout()
        return None

    email_ids = messages[0].split()
    if not email_ids:
        mail.logout()
        return None

    latest_email_id = email_ids[-1]

    status, msg_data = mail.fetch(latest_email_id, "(RFC822)")
    if status != "OK":
        mail.logout()
        return None

    raw_email = msg_data[0][1]
    msg = email.message_from_bytes(raw_email)

    sender = decode_mime_words(msg.get("From", ""))
    subject = decode_mime_words(msg.get("Subject", ""))
    body = extract_text_from_message(msg)

    preview = body[:500] if body else ""
    url = extract_first_url(body)

    mail.logout()

    return {
        "sender": sender,
        "subject": subject,
        "message": preview,
        "url": url
    }