from flask import Flask, render_template, request, Response, stream_with_context
import json
import re
import smtplib
import ssl
import time
import os
import html

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import formataddr, formatdate, make_msgid


app = Flask(__name__)

# Maximum uploaded PDF size: 10 MB
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$"
)


ALLOWED_FONTS = {
    "system": "Segoe UI, Arial, sans-serif",
    "arial": "Arial, Helvetica, sans-serif",
    "verdana": "Verdana, Geneva, sans-serif",
    "tahoma": "Tahoma, Geneva, sans-serif",
    "trebuchet": "Trebuchet MS, Arial, sans-serif",
    "georgia": "Georgia, serif",
    "times": "Times New Roman, Times, serif",
    "courier": "Courier New, monospace",
    "lucida": "Lucida Sans Unicode, Arial, sans-serif",
    "palatino": "Palatino Linotype, Book Antiqua, Palatino, serif",
    "garamond": "Garamond, Georgia, serif",
    "impact": "Impact, Haettenschweiler, sans-serif",
    "comic": "Comic Sans MS, cursive",
    "segoe": "Segoe UI, Arial, sans-serif",
    "calibri": "Calibri, Arial, sans-serif",
    "cambria": "Cambria, Georgia, serif",
    "consolas": "Consolas, monospace",
    "century": "Century Gothic, Arial, sans-serif",
    "bookman": "Bookman Old Style, serif",
    "franklin": "Franklin Gothic Medium, Arial, sans-serif",
}


SAMPLE_EMAILS = [
    "client01@example.com",
    "client02@example.com",
    "client03@example.com",
    "client04@example.com",
    "client05@example.com",
    "client06@example.com",
    "client07@example.com",
    "client08@example.com",
    "client09@example.com",
    "client10@example.com",
    "client11@example.com",
    "client12@example.com",
    "client13@example.com",
    "client14@example.com",
    "client15@example.com",
    "client16@example.com",
    "client17@example.com",
    "client18@example.com",
    "client19@example.com",
    "client20@example.com",
    "client21@example.com",
    "client22@example.com",
    "client23@example.com",
    "client24@example.com",
    "client25@example.com",
]


def is_valid_email(email):
    return EMAIL_PATTERN.fullmatch(email) is not None


def parse_recipients(raw_value):
    """
    Supports:
    email@example.com
    Name <email@example.com>
    comma separated
    semicolon separated
    spaces/new lines
    """

    raw_value = raw_value or ""

    # Convert semicolons to commas first.
    raw_value = raw_value.replace(";", ",")

    parts = []

    for chunk in raw_value.split(","):
        chunk = chunk.strip()

        if not chunk:
            continue

        # Support Name <email@example.com>
        match = re.match(
            r"^(.*?)\s*<\s*([^<>@\s]+@[^<>@\s]+)\s*>$",
            chunk
        )

        if match:
            name = match.group(1).strip()
            email = match.group(2).strip().lower()
            parts.append((name, email))
            continue

        # Otherwise allow multiple emails separated by whitespace.
        for value in re.split(r"\s+", chunk):
            email = value.strip().lower()

            if email:
                parts.append(("", email))

    recipients = []
    seen = set()

    for name, email in parts:
        if email not in seen:
            recipients.append({
                "name": name,
                "email": email
            })
            seen.add(email)

    return recipients


def stream_event(payload):
    return json.dumps(
        payload,
        ensure_ascii=False
    ) + "\n"


def personalize_text(text, recipient_name, recipient_email):
    """
    Supported:
    {name}
    {email}
    {0}
    """

    name = recipient_name.strip()

    if not name:
        # If no explicit name was supplied, use email username.
        name = recipient_email.split("@", 1)[0]

    return (
        text
        .replace("{name}", name)
        .replace("{email}", recipient_email)
        .replace("{0}", name)
    )


def text_to_html(text, font_family):
    """
    Convert plain message text into safe HTML.
    """

    safe_text = html.escape(text)
    safe_text = safe_text.replace("\n", "<br>\n")

    return f"""
    <div style="
        font-family:{font_family};
        font-size:15px;
        line-height:1.6;
        color:#182236;
        white-space:normal;
    ">
        {safe_text}
    </div>
    """


@app.route("/")
def index():
    return render_template(
        "index.html",
        fonts=ALLOWED_FONTS
    )


@app.route("/sample-emails", methods=["GET"])
def sample_emails():
    return Response(
        json.dumps({
            "emails": SAMPLE_EMAILS
        }),
        content_type="application/json"
    )


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
    )

    font_key = request.form.get(
        "font_key",
        "system"
    ).strip().lower()

    recipients = parse_recipients(
        request.form.get("recipients", "")
    )

    pdf_file = request.files.get("pdf_file")

    def generate():

        total = len(recipients)
        sent = 0
        failed = 0
        server = None

        # -----------------------------
        # VALIDATION
        # -----------------------------

        if not is_valid_email(sender_email):
            yield stream_event({
                "type": "fatal",
                "message": "Valid Gmail address enter karein."
            })
            return

        if not app_password:
            yield stream_event({
                "type": "fatal",
                "message": "Gmail App Password required hai."
            })
            return

        if not subject:
            yield stream_event({
                "type": "fatal",
                "message": "Email Subject required hai."
            })
            return

        if not body.strip():
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

        if font_key not in ALLOWED_FONTS:
            font_key = "system"

        font_family = ALLOWED_FONTS[font_key]

        # -----------------------------
        # PDF VALIDATION
        # -----------------------------

        pdf_data = None
        pdf_filename = None

        if pdf_file and pdf_file.filename:

            filename = os.path.basename(
                pdf_file.filename
            )

            if not filename.lower().endswith(".pdf"):
                yield stream_event({
                    "type": "fatal",
                    "message": "Sirf PDF file attach kar sakte hain."
                })
                return

            pdf_data = pdf_file.read()
            pdf_filename = filename

            if not pdf_data:
                yield stream_event({
                    "type": "fatal",
                    "message": "PDF file empty hai."
                })
                return

            if len(pdf_data) > 10 * 1024 * 1024:
                yield stream_event({
                    "type": "fatal",
                    "message": "PDF maximum 10 MB ho sakti hai."
                })
                return

        # -----------------------------
        # START
        # -----------------------------

        yield stream_event({
            "type": "start",
            "total": total,
            "sent": 0,
            "failed": 0,
            "remaining": total,
            "pdf_attached": bool(pdf_data),
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
                "pdf_attached": bool(pdf_data),
                "message": "Connected. Emails send ho rahe hain..."
            })

            # -----------------------------
            # SEND EMAILS
            # -----------------------------

            for recipient in recipients:

                recipient_name = recipient["name"]
                recipient_email = recipient["email"]

                if not is_valid_email(recipient_email):

                    failed += 1

                    yield stream_event({
                        "type": "progress",
                        "recipient": recipient_email,
                        "success": False,
                        "total": total,
                        "sent": sent,
                        "failed": failed,
                        "remaining": total - sent - failed,
                        "message": "Invalid email address"
                    })

                    continue

                try:

                    personalized_body = personalize_text(
                        body,
                        recipient_name,
                        recipient_email
                    )

                    personalized_subject = personalize_text(
                        subject,
                        recipient_name,
                        recipient_email
                    )

                    # Multipart email
                    message = MIMEMultipart("mixed")

                    message["From"] = formataddr((
                        sender_name,
                        sender_email
                    ))

                    message["To"] = recipient_email

                    message["Subject"] = personalized_subject

                    message["Date"] = formatdate(
                        localtime=True
                    )

                    message["Message-ID"] = make_msgid()

                    message["Reply-To"] = sender_email

                    # HTML body
                    html_body = text_to_html(
                        personalized_body,
                        font_family
                    )

                    alternative = MIMEMultipart(
                        "alternative"
                    )

                    # Plain-text version
                    alternative.attach(
                        MIMEText(
                            personalized_body,
                            "plain",
                            "utf-8"
                        )
                    )

                    # HTML version
                    alternative.attach(
                        MIMEText(
                            html_body,
                            "html",
                            "utf-8"
                        )
                    )

                    message.attach(alternative)

                    # -----------------------------
                    # PDF ATTACHMENT
                    # -----------------------------

                    if pdf_data:

                        attachment = MIMEApplication(
                            pdf_data,
                            _subtype="pdf"
                        )

                        attachment.add_header(
                            "Content-Disposition",
                            "attachment",
                            filename=pdf_filename
                        )

                        message.attach(
                            attachment
                        )

                    server.sendmail(
                        sender_email,
                        [recipient_email],
                        message.as_string()
                    )

                    sent += 1

                    success = True
                    status_message = "Sent"

                except Exception as error:

                    failed += 1

                    success = False

                    status_message = (
                        f"Failed: {error}"
                    )

                yield stream_event({
                    "type": "progress",
                    "recipient": recipient_email,
                    "success": success,
                    "total": total,
                    "sent": sent,
                    "failed": failed,
                    "remaining": total - sent - failed,
                    "message": status_message
                })

                # Small pause between messages.
                time.sleep(1)

            # -----------------------------
            # COMPLETE
            # -----------------------------

            yield stream_event({
                "type": "complete",
                "total": total,
                "sent": sent,
                "failed": failed,
                "remaining": 0,
                "pdf_attached": bool(pdf_data),
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
                    "Gmail address aur "
                    "16-character App Password "
                    "check karein."
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
        content_type=(
            "application/x-ndjson; charset=utf-8"
        ),
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


@app.errorhandler(413)
def file_too_large(error):
    return Response(
        json.dumps({
            "error": "File maximum 10 MB ho sakti hai."
        }),
        status=413,
        content_type="application/json"
    )


if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
        threaded=True
    )
