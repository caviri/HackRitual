# 12 — Email System

**Milestone:** MVP-1
**Priority:** Critical (required for authentication)
**Dependencies:** [01-project-setup-docker](01-project-setup-docker.md)
**Specs reference:** §7.6 (Email Sending), §4.3 (Networking)

---

## Overview

SMTP-based email sending for login code delivery and optional event notifications. Email must not block the request path — use either background threads or an internal queue (queue approach formalized in [14-task-queue-worker](14-task-queue-worker.md)).

---

## Tasks

### 12.1 SMTP Client Configuration

```python
# backend/app/services/email_service.py

from aiosmtplib import SMTP

class EmailService:
    def __init__(self, settings: Settings):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.username = settings.SMTP_USER
        self.password = settings.SMTP_PASS
        self.from_email = settings.SMTP_FROM

    async def send(self, to: str, subject: str, body_html: str, body_text: str):
        """Send an email via SMTP."""
        msg = MIMEMultipart("alternative")
        msg["From"] = self.from_email
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))

        async with SMTP(hostname=self.host, port=self.port, use_tls=True) as smtp:
            await smtp.login(self.username, self.password)
            await smtp.send_message(msg)
```

Use `aiosmtplib` for async SMTP — compatible with FastAPI's async model.

### 12.2 Email Templates

#### Login Code Email

**Subject:** `Your HackRitual login code`

**Body (HTML):**
```html
<div style="font-family: sans-serif; max-width: 480px; margin: 0 auto;">
  <h2>Your login code</h2>
  <p>Use this code to log in to <strong>{{event_title}}</strong>:</p>
  <div style="font-size: 32px; font-weight: bold; letter-spacing: 8px;
              text-align: center; padding: 16px; background: #f5f5f5;
              border-radius: 8px; margin: 16px 0;">
    {{code}}
  </div>
  <p>This code expires in 10 minutes.</p>
  <p style="color: #666; font-size: 12px;">
    If you didn't request this code, you can safely ignore this email.
  </p>
</div>
```

**Body (plain text):**
```
Your login code for {{event_title}}: {{code}}
This code expires in 10 minutes.
If you didn't request this, ignore this email.
```

#### Optional: Submission Received

**Subject:** `Submission received — {{event_title}}`

```
Your submission "{{title}}" has been received.
Status: {{status}}
```

#### Optional: Scoring Complete

**Subject:** `Score available — {{event_title}}`

```
Your submission "{{title}}" has been scored.
Score: {{score}}
View details: {{link}}
```

#### Optional: Event Phase Change

**Subject:** `{{event_title}} — {{phase_message}}`

```
The event has moved to {{new_state}}.
{{phase_description}}
```

### 12.3 Background Email Sending (MVP-1 Simple)

For MVP-1, use FastAPI's `BackgroundTasks`:

```python
@router.post("/auth/request-code")
async def request_code(
    data: RequestCodeInput,
    background_tasks: BackgroundTasks,
    email_service: EmailService = Depends(get_email_service),
):
    # ... generate code, store in DB ...
    background_tasks.add_task(
        email_service.send,
        to=data.email,
        subject="Your HackRitual login code",
        body_html=render_login_code_email(code, event_title),
        body_text=f"Your code: {code}",
    )
    return Response(status_code=204)
```

This is a simple in-process background task. For robust queueing with retries, see [14-task-queue-worker](14-task-queue-worker.md).

### 12.4 Email Metrics

Per specs §14.7, store only aggregate metrics:

- Count of emails sent (increment counter)
- Success/failure state
- Timestamp

Do NOT store:
- Email content
- SMTP response bodies
- Recipient addresses in logs

### 12.5 Email Validation

- Validate email format before attempting to send
- Use a simple regex or `email-validator` library
- Do not perform MX record lookups (adds latency, not reliable)

### 12.6 Development/Testing Mode

When `SMTP_HOST` is not configured or set to `console`:
- Print email content to stdout instead of sending
- Log the login code to make development/testing possible
- Clearly label as dev mode in logs

---

## Acceptance Criteria

- [ ] Login codes delivered via SMTP to the user's email
- [ ] Email sending does not block the HTTP response
- [ ] HTML and plain text alternatives included in emails
- [ ] Templates render correctly with event-specific data
- [ ] Dev mode outputs email to console when SMTP not configured
- [ ] Email metrics tracked (count, success/failure)
- [ ] No email content or recipient data logged in production

---

## Developer Notes

- `aiosmtplib` is the recommended async SMTP library for FastAPI
- For testing, use `MailHog` or `Mailpit` as a local SMTP server (add to docker-compose)
- Keep templates as simple strings — no need for a template engine in MVP-1
- Consider extracting templates to separate files if they grow complex
- SMTP connection timeouts should be short (10s) to avoid blocking workers
- If SMTP is flaky, the task queue (MVP-2) provides retry capability
