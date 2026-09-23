from flask import Flask, render_template, request, Response
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
    r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$"
)


def is_valid_email(email):
    return EMAIL_PATTERN.fullmatch(email) is not None


def parse_recipients(raw_value):
    """
    Accept:
    email1@example.com
    email2@example.com

    Also accepts comma/semicolon separated emails.
    """

    if not raw_value:
        return []

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
    return json.dumps(
        payload,
        ensure_ascii=False
    ) + "\n"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/send-stream", methods=["POST"])
def send_stream():

    sender_name = request.form.get(
        "sender_name",
        ""
    ).strip()

    sender_email = request.form.get(
        "sender_email",
        ""
    ).strip().lower()

    app_password = request.form.get(
        "app_password",
        ""
    ).replace(" ", "").strip()

    subject = request.form.get(
        "subject",
        ""
    ).strip()

    body = request.form.get(
        "body",
        ""
    ).strip()

    recipients = parse_recipients(
        request.form.get(
            "recipients",
            ""
        )
    )

    def generate():

        total = len(recipients)
        sent = 0
        failed = 0
        server = None

        # -----------------------------------------
        # VALIDATION
        # -----------------------------------------

        if not is_valid_email(sender_email):
            yield stream_event({
                "type": "fatal",
                "message": "Please enter a valid Gmail address."
            })
            return

        if not app_password:
            yield stream_event({
                "type": "fatal",
                "message": "Please enter your Gmail App Password."
            })
            return

        if len(app_password) != 16:
            yield stream_event({
                "type": "fatal",
                "message": (
                    "Gmail App Password should contain "
                    "16 characters."
                )
            })
            return

        if not subject:
            yield stream_event({
                "type": "fatal",
                "message": "Email Subject is required."
            })
            return

        if not body:
            yield stream_event({
                "type": "fatal",
                "message": "Message Body is required."
            })
            return

        if total == 0:
            yield stream_event({
                "type": "fatal",
                "message": "Please add at least one recipient."
            })
            return

        # -----------------------------------------
        # START
        # -----------------------------------------

        yield stream_event({
            "type": "start",
            "total": total,
            "sent": 0,
            "failed": 0,
            "remaining": total,
            "message": "Connecting to Gmail..."
        })

        try:

            tls_context = ssl.create_default_context()

            server = smtplib.SMTP(
                "smtp.gmail.com",
                587,
                timeout=30
            )

            server.ehlo()

            server.starttls(
                context=tls_context
            )

            server.ehlo()

            server.login(
                sender_email,
                app_password
            )

            yield stream_event({
                "type": "connected",
                "total": total,
                "sent": sent,
                "failed": failed,
                "remaining": total,
                "message": "Connected to Gmail. Ready to send."
            })

            # -----------------------------------------
            # SEND EMAILS
            # -----------------------------------------

            for recipient in recipients:

                # Invalid recipient
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

                    message = MIMEText(
                        body,
                        "plain",
                        "utf-8"
                    )

                    # Sender name is optional
                    if sender_name:
                        message["From"] = formataddr(
                            (
                                sender_name,
                                sender_email
                            )
                        )
                    else:
                        message["From"] = sender_email

                    message["To"] = recipient
                    message["Subject"] = subject
                    message["Date"] = formatdate(
                        localtime=True
                    )

                    # Use sender's domain for Message-ID
                    sender_domain = sender_email.split("@")[-1]

                    message["Message-ID"] = make_msgid(
                        domain=sender_domain
                    )

                    message["Reply-To"] = sender_email

                    server.sendmail(
                        sender_email,
                        [recipient],
                        message.as_string()
                    )

                    sent += 1

                    yield stream_event({
                        "type": "progress",
                        "recipient": recipient,
                        "success": True,
                        "total": total,
                        "sent": sent,
                        "failed": failed,
                        "remaining": total - sent - failed,
                        "message": "Sent successfully"
                    })

                except smtplib.SMTPRecipientsRefused as error:

                    failed += 1

                    yield stream_event({
                        "type": "progress",
                        "recipient": recipient,
                        "success": False,
                        "total": total,
                        "sent": sent,
                        "failed": failed,
                        "remaining": total - sent - failed,
                        "message": "Recipient rejected by Gmail"
                    })

                except smtplib.SMTPException as error:

                    failed += 1

                    yield stream_event({
                        "type": "progress",
                        "recipient": recipient,
                        "success": False,
                        "total": total,
                        "sent": sent,
                        "failed": failed,
                        "remaining": total - sent - failed,
                        "message": str(error)
                    })

                except Exception as error:

                    failed += 1

                    yield stream_event({
                        "type": "progress",
                        "recipient": recipient,
                        "success": False,
                        "total": total,
                        "sent": sent,
                        "failed": failed,
                        "remaining": total - sent - failed,
                        "message": str(error)
                    })

                # Small pause between messages
                time.sleep(1)

            # -----------------------------------------
            # COMPLETE
            # -----------------------------------------

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
                    "Gmail authentication failed. "
                    "Check your Gmail address and "
                    "16-character App Password."
                )
            })

        except smtplib.SMTPConnectError:

            yield stream_event({
                "type": "fatal",
                "total": total,
                "sent": sent,
                "failed": failed,
                "remaining": total - sent - failed,
                "message": (
                    "Could not connect to Gmail SMTP server."
                )
            })

        except ssl.SSLError as error:

            yield stream_event({
                "type": "fatal",
                "total": total,
                "sent": sent,
                "failed": failed,
                "remaining": total - sent - failed,
                "message": f"SSL/TLS error: {error}"
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
        generate(),
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
