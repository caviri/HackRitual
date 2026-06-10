"""
Email service — SMTP dispatch with a console fallback for local dev.

Covers the auth-critical subset of Step 12. Full email system (submission
notifications, event phase changes, metrics) is expanded there.

Dev/console mode is active when SMTP_HOST is "console" or "localhost" with
no real port — in that case the email body is printed to stdout so development
and testing are possible without an SMTP server.
"""

from __future__ import annotations

import hashlib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.services import email_metrics

logger = logging.getLogger(__name__)

_CONSOLE_HOSTS = {"console", "localhost", "127.0.0.1"}


def _is_console_mode(host: str) -> bool:
    return host.strip().lower() in _CONSOLE_HOSTS


def _recipient_tag(to: str) -> str:
    """A short hash standing in for the address — never log the address itself."""
    return hashlib.sha256(to.encode("utf-8")).hexdigest()[:12]


async def send_email(to: str, subject: str, body_html: str, body_text: str) -> bool:
    """
    Dispatch an email, recording an aggregate metric. Returns success.

    In console/dev mode nothing is sent — a concise line is logged (no body, no
    address) and the attempt is counted as a success. Used by notifications; the
    login-code path keeps its own dev print for developer convenience.
    """
    from app.config import settings

    if _is_console_mode(settings.smtp_host):
        logger.info(
            "[DEV] email (not sent via SMTP)",
            extra={"recipient_tag": _recipient_tag(to), "subject": subject},
        )
        email_metrics.record(True)
        return True

    try:
        await _send_smtp(to=to, subject=subject, body_html=body_html, body_text=body_text)
        email_metrics.record(True)
        return True
    except Exception:
        email_metrics.record(False)
        return False


def _login_code_html(code: str, event_title: str) -> str:
    """Magic-link email — HackRitual-styled.

    Inline CSS only (mail clients strip <style>). Six glyph slots mimic the
    on-site signin so the code reads like a sigil rather than a number.
    """
    digits = "".join(
        f'<td style="width:42px;height:54px;background:#0a0c07;'
        f'border:1px solid #1a2410;text-align:center;'
        f'font-family:Menlo,Monaco,Consolas,monospace;'
        f'font-size:28px;font-weight:500;color:#7c9858;letter-spacing:0;">{ch}</td>'
        for ch in code
    )
    return f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#050603;">
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"
         style="background:#050603;padding:48px 16px;">
    <tr><td align="center">
      <table role="presentation" cellpadding="0" cellspacing="0" border="0"
             style="max-width:520px;width:100%;background:#0a0c07;border:1px solid #1a2410;">
        <tr><td style="padding:32px 32px 0 32px;">
          <div style="font-family:Menlo,Monaco,Consolas,monospace;font-size:12px;
                      letter-spacing:0.18em;text-transform:uppercase;color:#545848;margin-bottom:24px;">
            <span style="color:#7c9858;">◆</span>&nbsp;&nbsp;HackRitual&nbsp;&nbsp;·&nbsp;&nbsp;the spellbook
          </div>
          <h1 style="font-family:Georgia,'Times New Roman',serif;font-style:italic;
                     font-weight:400;font-size:38px;line-height:1.05;color:#f1f1e8;
                     margin:0 0 12px 0;">
            Speak the six glyphs.
          </h1>
          <p style="font-family:Menlo,Monaco,Consolas,monospace;font-size:14px;
                    line-height:1.6;color:#8a8f78;margin:0 0 28px 0;">
            Your code for entering <span style="color:#f1f1e8;">{event_title}</span>.
            It holds for ten minutes.
          </p>
        </td></tr>
        <tr><td style="padding:0 32px 32px 32px;">
          <table role="presentation" cellpadding="0" cellspacing="6" border="0" align="center">
            <tr>{digits}</tr>
          </table>
        </td></tr>
        <tr><td style="padding:0 32px 32px 32px;border-top:1px solid #1a2410;">
          <p style="font-family:Georgia,'Times New Roman',serif;font-style:italic;
                    font-size:16px;color:#8a8f78;margin:20px 0 0 0;line-height:1.55;">
            The ritual is fragile. If you did not call upon it, ignore this
            letter — the code will fade in ten minutes' time.
          </p>
          <p style="font-family:Menlo,Monaco,Consolas,monospace;font-size:11px;
                    letter-spacing:0.16em;text-transform:uppercase;color:#545848;
                    margin:20px 0 0 0;">
            ▒ each gate keeps its own register
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _login_code_text(code: str, event_title: str) -> str:
    """Plain-text fallback for mail clients that don't render HTML."""
    spaced = " ".join(code)
    return (
        f"HackRitual · the spellbook\n\n"
        f"Speak the six glyphs.\n\n"
        f"Your code for entering {event_title}:\n\n"
        f"    {spaced}\n\n"
        f"It holds for ten minutes.\n"
        f"If you did not call upon it, ignore this letter — the code will\n"
        f"fade in ten minutes' time.\n"
    )


async def send_login_code(to: str, code: str, event_title: str) -> None:
    """
    Dispatch the magic login code to the given address.

    In console mode the message is printed to stdout rather than sent
    via SMTP — safe for development and test environments.
    """
    from app.config import settings

    subject = f"◆ {code} — your HackRitual sigil"
    body_html = _login_code_html(code, event_title)
    body_text = _login_code_text(code, event_title)

    if _is_console_mode(settings.smtp_host):
        # Dev convenience: the code is printed so local login is possible.
        logger.info(
            "[DEV] Login code email (not sent via SMTP)",
            extra={"to": to, "subject": subject, "code": code},
        )
        print(f"\n--- DEV EMAIL ---\nTo: {to}\nSubject: {subject}\n\n{body_text}\n---\n")
        email_metrics.record(True)
        return

    try:
        await _send_smtp(
            to=to,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
        )
        email_metrics.record(True)
    except Exception:
        email_metrics.record(False)
        raise


async def _send_smtp(to: str, subject: str, body_html: str, body_text: str) -> None:
    """Low-level SMTP send via aiosmtplib."""
    import aiosmtplib
    from app.config import settings

    msg = MIMEMultipart("alternative")
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    use_tls = settings.smtp_port == 465
    start_tls = settings.smtp_port == 587

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_pass,
            use_tls=use_tls,
            start_tls=start_tls,
            timeout=10,
        )
        logger.info("Email sent", extra={"recipient_tag": _recipient_tag(to)})
    except Exception as exc:
        logger.error(
            "Failed to send email",
            extra={"recipient_tag": _recipient_tag(to), "error": str(exc)},
        )
        raise
