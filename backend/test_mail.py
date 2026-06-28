"""Run from the backend/ directory: python test_mail.py"""
import smtplib
from email.message import EmailMessage
from app.config import settings

print(f"Host     : {settings.mail_host}")
print(f"Port     : {settings.mail_port}")
print(f"Username : {settings.mail_username}")
print(f"From     : {settings.mail_from}")
print(f"TLS      : {settings.mail_use_tls}")
print()

msg = EmailMessage()
msg["From"]    = settings.mail_from
msg["To"]      = "mikelange64@gmail.com"
msg["Subject"] = "WorkspaceApp — SMTP test"
msg.set_content("If you see this, SMTP is working.")

try:
    print(f"Connecting to {settings.mail_host}:{settings.mail_port}...")
    with smtplib.SMTP(settings.mail_host, settings.mail_port, timeout=10) as smtp:
        smtp.set_debuglevel(1)          # prints every SMTP command/response
        if settings.mail_use_tls:
            print("Starting TLS...")
            smtp.starttls()
        print("Logging in...")
        smtp.login(settings.mail_username, settings.mail_password.get_secret_value())
        print("Sending...")
        smtp.send_message(msg)
    print("\n✓ Email sent — check your Mailtrap inbox.")
except Exception as e:
    print(f"\n✗ Failed: {type(e).__name__}: {e}")
