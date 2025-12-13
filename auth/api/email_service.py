from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import send_mail

from .utils import activation_link, password_reset_link

logger = logging.getLogger(__name__)

EMAIL_TEMPLATE_HTML = """\
<!doctype html>
<html>
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta charset="utf-8" />
    <title>{title}</title>
  </head>
  <body style="margin:0;padding:0;background:#0b0b0b;color:#ffffff;font-family:Arial,sans-serif;">
    <div style="max-width:560px;margin:0 auto;padding:24px;">
      <h2 style="color:#e50914;margin:0 0 16px 0;">{title}</h2>
      <p style="margin:0 0 24px 0;line-height:1.6;">{message}</p>
      <a href="{link}" style="display:inline-block;background:#e50914;color:#ffffff;padding:12px 18px;border-radius:6px;text-decoration:none;">
        {button_text}
      </a>
      <p style="margin:24px 0 0 0;font-size:12px;opacity:0.85;word-break:break-all;">
        {link}
      </p>
    </div>
  </body>
</html>
"""


def render_email_html(title: str, message: str, button_text: str, link: str) -> str:
    """Render responsive HTML email."""
    return EMAIL_TEMPLATE_HTML.format(
        title=title,
        message=message,
        button_text=button_text,
        link=link,
    )


def send_email(to_email: str, subject: str, text_body: str, html_body: str) -> None:
    """Send email using Django settings."""
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com")
    send_mail(
        subject,
        text_body,
        from_email,
        [to_email],
        html_message=html_body,
        fail_silently=False,
    )


def dev_link(label: str, link: str) -> None:
    """Print/log a copy-paste safe link for local development."""
    if not getattr(settings, "DEBUG", False):
        return
    logger.warning("[%s LINK] %s", label, link)
    print(f"[{label} LINK] {link}", flush=True)


def send_activation_email(to_email: str, uidb64: str, token: str) -> None:
    """Send activation email."""
    link = activation_link(uidb64, token)
    dev_link("ACTIVATION", link)
    html = render_email_html(
        "Activate your Videoflix account",
        "Please activate your account to sign in.",
        "Activate",
        link,
    )
    send_email(to_email, "Activate your Videoflix account", f"Activate your account:\n{link}", html)


def send_password_reset_email(to_email: str, uidb64: str, token: str) -> None:
    """Send password reset email."""
    link = password_reset_link(uidb64, token)
    dev_link("RESET", link)
    html = render_email_html(
        "Reset your Videoflix password",
        "Set a new password for your account.",
        "Reset password",
        link,
    )
    send_email(to_email, "Reset your Videoflix password", f"Reset your password:\n{link}", html)
