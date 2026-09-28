"""Account emails over SMTP (settings `SMTP_*` in backend/.env)."""
import logging
import smtplib
from email.message import EmailMessage
from html import escape

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_STYLE = """
body{margin:0;background:#f4f5f7;font-family:Arial,sans-serif;color:#1f2937}
.wrap{max-width:560px;margin:32px auto;background:#fff;border-radius:12px;border:1px solid #e5e7eb}
.head{padding:24px 32px;border-bottom:1px solid #e5e7eb;font-size:18px;font-weight:700}
.body{padding:24px 32px;font-size:15px;line-height:1.6}
.info{background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:12px 16px;margin:16px 0}
.info p{margin:4px 0}
.btn{display:inline-block;margin:8px 0 16px;padding:12px 24px;background:#4f46e5;color:#fff!important;
     text-decoration:none;border-radius:8px;font-weight:600}
.foot{padding:16px 32px;border-top:1px solid #e5e7eb;font-size:12px;color:#6b7280}
"""


def _page(body: str) -> str:
    return (
        f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{_STYLE}</style></head><body>'
        f'<div class="wrap"><div class="head">SkillSprint AI</div><div class="body">{body}</div>'
        '<div class="foot">This is an automated email from SkillSprint AI. Please do not reply.</div></div></body></html>'
    )


def _send(to_email: str, subject: str, html: str, text: str) -> bool:
    """Returns False when the email was not sent; the caller's action still succeeds (HR can copy the link)."""
    settings = get_settings()
    if not (settings.smtp_host and settings.smtp_user and settings.smtp_password):
        logger.warning("SMTP is not configured; email to %s not sent: %s", to_email, subject)
        return False

    msg = EmailMessage()
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_user}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
    except (smtplib.SMTPException, OSError):
        logger.exception("Sending email to %s failed", to_email)
        return False
    return True


def send_account_credentials(
    to_email: str, name: str, password: str, login_url: str, position_name: str, department_name: str
) -> bool:
    """Login details for an account an Admin created from a CV.

    The password is generated for this email only: it is not stored in plain text and not shown to the Admin when the
    email is sent. The employee is asked to change it after the first login.
    """
    html = _page(
        f"<p>Hello <strong>{escape(name)}</strong>,</p>"
        f"<p>Your SkillSprint AI account has been created for your onboarding path.</p>"
        f'<div class="info"><p><strong>Login Email:</strong> {escape(to_email)}</p>'
        f"<p><strong>Temporary Password:</strong> <code>{escape(password)}</code></p>"
        f"<p><strong>Position:</strong> {escape(position_name)}</p>"
        f"<p><strong>Department:</strong> {escape(department_name)}</p></div>"
        f"<p>After signing in, please change your password in the account menu (top-right corner).</p>"
        f'<a class="btn" href="{escape(login_url)}">Sign In</a>'
    )
    text = (
        f"Hello {name},\n"
        f"Your SkillSprint AI account has been created.\n"
        f"Login Email: {to_email}\n"
        f"Temporary Password: {password}\n"
        f"Position: {position_name}. Department: {department_name}.\n"
        f"Sign in: {login_url}\n"
        f"After signing in, please change your password in the account menu."
    )
    return _send(to_email, "Your SkillSprint AI Login Credentials", html, text)

