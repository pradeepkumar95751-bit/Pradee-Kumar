from flask import Flask, render_template, request, Response, stream_with_context
import json
import re
import smtplib
import ssl
import time

from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid


app = Flask(__name__)


EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9-9-]{0,61}[A-Za-z0-9]?"
    r"(?:\.?:[A-Za-z0-9-]{0,61}[A-Za-z0-9]?)+$"
)


def is_valid_email(email):
    return EMAIL_PATTERN.fullmatch(email) is not None


def parse_recipients(raw_value):
    normalised = re.sub(r"[,;\s]+", "\n", raw_value)

    recipients = []
    seen = set()

    for line in normalised.splitlines():
        email = line.strip().lower()

        if email and email not in seen:
            recipients.append(email)
            seen.add(email)

    return recipients


def stream_event(payload):
    return json.dumps(payload, ensure_ascii=False) + "\n"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/send-stream", methods=["POST"])
def send_stream():
    sender_name = request.form.get("sender_name", "").strip()
    sender_email = request.form.get("sender_email", "").strip().lower()
    app_password = request.form.get("app_password", "").replace(" ", "")
    subject = request.form.get("subject", "").strip()
    body = request.form.get("body", "").strip()
    recipients = parse_recipients(request.form.get("recipients", ""))

    def generate():
        total = len(recipients)
        sent = 0
        failed = 0
        server = None

        if not sender_name:
            yield stream_event({
                "type": "fatal",
                "message": "Sender Name required hai."
            })
            return

        if not is_valid_email(sender_email):
            yield stream_event({
                "type": "fatal",
                "message": "Valid sender email enter karein."
            })
            return

        if not app_password:
            yield stream_event({
                "type": "fatal",
                "message": "Google App Password required hai."
            })
            return

        if not subject:
            yield stream_event({
                "type": "fatal",
                "message": "Email Subject required hai."
            })
            return

        if not body:
            yield stream_event({
                "type": "fatal",
                "message": "Message Body required hai."
            })
            return

        if total == 0:
            yield stream_event({
                "type": "fatal",
                "message": "Kam se kam ek recipient enter karein."
            })
            return

        yield stream_event({
            "type": "start",
            "total": total,
            "sent": 0,
            "failed": 0,
            "remaining": total,
            "message": "Gmail server se connect ho raha hai..."
        })

        try:
            tls_context = ssl.create_default_context()

            server = smtplib.SMTP(
                host="smtp.gmail.com",
                port=587,
                timeout=30
            )

            server.ehlo()
            server.starttls(context=tls_context)
            server.ehlo()
            server.login(sender_email, app_password)

            yield stream_event({
                "type": "connected",
                "total": total,
                "sent": sent,
                "failed": failed,
                "remaining": total,
                "message": "Connected. Emails send ho rahe hain..."
            })

            for recipient in recipients:
                if not is_valid_email(recipient):
                    failed += 1

                    yield stream_event({
                        "type": "progress",
                        "recipient": recipient,
                        "success": False,
                        "total": total,
                        "sent": sent,
                        "failed": failed,
                        "remaining": total - sent - failed,
                        "message": "Invalid email address"
                    })
                    continue

                try:
                    recipient_domain = recipient.rsplit("@", 1)[-1]

                    message = MIMEText(
                        body,
                        "plain",
                        "utf-8"
                    )

                    message["From"] = formataddr((
                        sender_name,
                        sender_email
                    ))
                    message["To"] = recipient
                    message["Subject"] = subject
                    message["Date"] = formatdate(localtime=True)
                    message["Message-ID"] = make_msgid(
                        domain=recipient_domain
                    )
                    message["Reply-To"] = sender_email

                    server.sendmail(
                        sender_email,
                        [recipient],
                        message.as_string()
                    )

                    sent += 1
                    success = True
                    status_message = "Sent"

                except Exception as error:
                    failed += 1
                    success = False
                    status_message = f"Failed: {error}"

                yield stream_event({
                    "type": "progress",
                    "recipient": recipient,
                    "success": success,
                    "total": total,
                    "sent": sent,
                    "failed": failed,
                    "remaining": total - sent - failed,
                    "message": status_message
                })

                # A small delay avoids sending everything instantly.
                time.sleep(1)

            yield stream_event({
                "type": "complete",
                "total": total,
                "sent": sent,
                "failed": failed,
                "remaining": 0,
                "message": "Sending completed"
            })

        except smtplib.SMTPAuthenticationError:
            yield stream_event({
                "type": "fatal",
                "total": total,
                "sent": sent,
                "failed": failed,
                "remaining": total - sent - failed,
                "message": (
                    "Gmail login failed. Gmail address aur "
                    "16-character App Password check karein."
                )
            })

        except Exception as error:
            yield stream_event({
                "type": "fatal",
                "total": total,
                "sent": sent,
                "failed": failed,
                "remaining": total - sent - failed,
                "message": f"Connection error: {error}"
            })

        finally:
            if server is not None:
                try:
                    server.quit()
                except Exception:
                    try:
                        server.close()
                    except Exception:
                        pass

    return Response(
        stream_with_context(generate()),
        content_type="application/x-ndjson; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
        threaded=True
    )
