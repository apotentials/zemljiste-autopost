"""Šalje e-mail s gotovim tekstom za Google Business profil i LinkedIn (+ slika u privitku).
Besplatno preko Gmail SMTP-a s "App password". Ako SMTP nije postavljen, preskače se."""
from __future__ import annotations

import smtplib
from email.message import EmailMessage
from pathlib import Path

import config


def send_package(subject: str, texts: dict, url: str, attachment: Path | None) -> None:
    if not (config.SMTP_USER and config.SMTP_PASSWORD):
        print("  · SMTP nije postavljen – paket je samo u out/ mapi.")
        return

    body = f"""GOOGLE BUSINESS PROFIL – kopiraj u novu objavu (Dodaj ažuriranje)
Gumb: "Saznajte više" → {url}
Slika: u privitku
----------------------------------------------------------------
{texts['gbp']}


LINKEDIN
----------------------------------------------------------------
{texts['linkedin']}
"""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.SMTP_USER
    msg["To"] = config.NOTIFY_TO
    msg.set_content(body)
    if attachment and attachment.exists():
        msg.add_attachment(attachment.read_bytes(), maintype="image", subtype="jpeg", filename=attachment.name)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(config.SMTP_USER, config.SMTP_PASSWORD)
        s.send_message(msg)
    print(f"  · E-mail poslan na {config.NOTIFY_TO}")
