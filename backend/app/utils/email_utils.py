import smtplib
from email.message import EmailMessage
from pathlib import Path

from app.config import settings
from fastapi.templating import Jinja2Templates

_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def send_email(
    to_email: str, subject: str, plain_text: str, html_content: str | None = None
) -> None:
    message = EmailMessage()

    message["From"] = settings.mail_from
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(plain_text) # Some email clients do not render html, this is a fallback

    if html_content:
        message.add_alternative(html_content, subtype="html")  # or clients that do render html

    with smtplib.SMTP(settings.mail_host, settings.mail_port) as smtp:
        if settings.mail_use_tls:
            smtp.starttls()
        if settings.mail_username and settings.mail_password:
            smtp.login(
                settings.mail_username,
                settings.mail_password.get_secret_value()
            )
        smtp.send_message(message)

    
def send_password_reset_email(to_email: str, username: str, token: str) -> None:
    reset_url = f"{settings.frontend_url}/reset-password?token={token}"

    # we use this instead of TemplateResponse because TemplateResponse requires a request, this doesn't.
    template = templates.env.get_template("email/password_reset.html")
    html_content = template.render(reset_url=reset_url, username=username)

    plain_text = f"""Hi {username},
    
    You requested to reset your password. Click the link below to set a new password:
    
    {reset_url}
    
    If you didn't request this, you can safely ignore this email.
    
    Best Regards,
    The Fast API Blog Team
    """

    send_email(
        to_email=to_email,
        subject="Reset Your Password - Filobelo",
        plain_text=plain_text,
        html_content=html_content,
    )


def send_verification_email(to_email: str, username: str, token: str) -> None:
    verification_url = f"{settings.frontend_url}/verify-email?token={token}"

    template = templates.env.get_template("email/email_verification.html")
    html_content = template.render(verification_url=verification_url, username=username)

    plain_text = f"""Hi {username},

    Welcome to Filobelo! Please verify your email address to activate your account.

    {verification_url}

    This link will expire in 24 hours. If you didn't sign up for Filobelo, you can safely ignore this email.

    Best Regards,
    The Filobelo Team
    """

    send_email(
        to_email=to_email,
        subject="Verify your email - Filobelo",
        plain_text=plain_text,
        html_content=html_content,
    )