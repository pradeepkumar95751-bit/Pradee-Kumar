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
    r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$"
)


BATCH_SIZE = 5
BATCH_DELAY = 2


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
    ).replace(" ", "")

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

        # -------------------------
        # VALIDATION
        # -------------------------

        if not is_valid_email(sender_email):

            yield stream_event({
                "type": "fatal",
                "message": "Valid Gmail address enter karein."
            })

            return

        if not app_password:

            yield stream_event({
                "type": "fatal",
                "message": "16-digit Google App Password required hai."
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

        # -------------------------
        # START
        # -------------------------

        yield stream_event({
            "type": "start",
            "total": total,
            "sent": 0,
            "failed": 0,
            "remaining": total,
            "batch_size": BATCH_SIZE,
            "message": f"{BATCH_SIZE} emails ke batches mein sending start ho rahi hai..."
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
                "message": "Gmail connected. Sending emails..."
            })

            # -------------------------
            # 5 EMAIL BATCHES
            # -------------------------

            for batch_start in range(
                0,
                total,
                BATCH_SIZE
            ):

                batch = recipients[
                    batch_start:
                    batch_start + BATCH_SIZE
                ]

                batch_number = (
                    batch_start // BATCH_SIZE
                ) + 1

                total_batches = (
                    total + BATCH_SIZE - 1
                ) // BATCH_SIZE

                yield stream_event({
                    "type": "batch",
                    "batch": batch_number,
                    "total_batches": total_batches,
                    "batch_size": len(batch),
                    "message": (
                        f"Batch {batch_number}/{total_batches} "
                        f"send ho raha hai..."
                    )
                })

                # -------------------------
                # SEND CURRENT BATCH
                # -------------------------

                for recipient in batch:

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

                        message["From"] = formataddr((
                            sender_name,
                            sender_email
                        )) if sender_name else sender_email

                        message["To"] = recipient

                        message["Subject"] = subject

                        message["Date"] = formatdate(
                            localtime=True
                        )

                        message["Message-ID"] = make_msgid()

                        message["Reply-To"] = sender_email

                        server.sendmail(
                            sender_email,
                            [recipient],
                            message.as_string()
                        )

                        sent += 1

                        success = True

                        status_message = "Sent successfully"

                    except Exception as error:

                        failed += 1

                        success = False

                        status_message = (
                            f"Failed: {error}"
                        )

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

                    # Small delay between individual messages
                    time.sleep(0.5)

                # -------------------------
                # BATCH DELAY
                # -------------------------

                if (
                    batch_start + BATCH_SIZE
                    < total
                ):

                    yield stream_event({
                        "type": "waiting",
                        "total": total,
                        "sent": sent,
                        "failed": failed,
                        "remaining": total - sent - failed,
                        "message": (
                            f"Batch {batch_number} complete. "
                            f"Next batch ke liye wait..."
                        )
                    })

                    time.sleep(BATCH_DELAY)

            # -------------------------
            # COMPLETE
            # -------------------------

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
                    "Gmail login failed. "
                    "Gmail address aur 16-digit "
                    "App Password check karein."
                )
            })

        except smtplib.SMTPException as error:

            yield stream_event({
                "type": "fatal",
                "total": total,
                "sent": sent,
                "failed": failed,
                "remaining": total - sent - failed,
                "message": f"SMTP error: {error}"
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
