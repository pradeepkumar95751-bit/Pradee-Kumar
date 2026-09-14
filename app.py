from flask import Flask, render_template, request, jsonify
import smtplib
import random
import time
import re
from email.mime.text import MIMEText

app = Flask(__name__)


# =========================================================
# WORD ROTATION
# =========================================================

ROTATE_WORDS = {
    "rank": [
        "rank",
        "ranking",
        "position"
    ],

    "first page of google": [
        "first page of Google",
        "top page of Google",
        "Google's first page"
    ],

    "visibility": [
        "visibility",
        "online presence",
        "search presence"
    ],

    "reports": [
        "reports",
        "details",
        "documents"
    ],

    "quote": [
        "quote",
        "pricing",
        "estimate"
    ],

    "information": [
        "information",
        "details",
        "material"
    ]
}


# =========================================================
# TEXT ROTATION FUNCTION
# =========================================================

def rotate_text(text: str) -> str:
    """
    Replaces selected words with normal-language variations.
    """

    for word, variants in ROTATE_WORDS.items():

        pattern = re.compile(
            re.escape(word),
            re.IGNORECASE
        )

        if pattern.search(text):
            selected = random.choice(variants)

            text = pattern.sub(
                selected,
                text,
                count=1
            )

    return text


# =========================================================
# EMAIL VALIDATION
# =========================================================

def is_valid_email(email):
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

    return re.match(pattern, email) is not None


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def index():
    return render_template("index.html")


# =========================================================
# SEND EMAIL
# =========================================================

@app.route("/send", methods=["POST"])
def send():

    sender_name = request.form.get(
        "sender_name",
        ""
    ).strip()

    sender_id = request.form.get(
        "sender_id",
        ""
    ).strip()

    app_password = request.form.get(
        "app_password",
        ""
    ).strip()

    subject = request.form.get(
        "subject",
        ""
    ).strip()

    body = request.form.get(
        "body",
        ""
    ).strip()

    recipients_text = request.form.get(
        "recipients",
        ""
    )


    # -----------------------------------------------------
    # Convert commas into new lines
    # -----------------------------------------------------

    recipients_text = recipients_text.replace(
        ",",
        "\n"
    )


    # -----------------------------------------------------
    # Create recipient list
    # -----------------------------------------------------

    recipients = [
        email.strip()
        for email in recipients_text.splitlines()
        if email.strip()
    ]


    # -----------------------------------------------------
    # Separate valid and invalid emails
    # -----------------------------------------------------

    valid_recipients = [
        email
        for email in recipients
        if is_valid_email(email)
    ]

    invalid_recipients = [
        email
        for email in recipients
        if not is_valid_email(email)
    ]


    # -----------------------------------------------------
    # Rotate normal wording
    # -----------------------------------------------------

    subject = rotate_text(subject)
    body = rotate_text(body)


    total = len(recipients)

    sent_count = 0
    fail_count = 0

    results = []

    server = None


    # =====================================================
    # SMTP CONNECTION
    # =====================================================

    try:

        smtp_host = "smtp.gmail.com"
        smtp_port = 587

        server = smtplib.SMTP(
            smtp_host,
            smtp_port
        )

        server.ehlo()

        server.starttls()

        server.ehlo()

        server.login(
            sender_id,
            app_password
        )


        # =================================================
        # SEND TO VALID RECIPIENTS
        # =================================================

        for recipient in valid_recipients:

            try:

                msg = MIMEText(
                    body,
                    "plain",
                    "utf-8"
                )

                msg["From"] = (
                    f"{sender_name} <{sender_id}>"
                )

                msg["To"] = recipient

                msg["Subject"] = subject


                # -----------------------------------------
                # Send email
                # -----------------------------------------

                server.sendmail(
                    sender_id,
                    recipient,
                    msg.as_string()
                )


                sent_count += 1

                status = "Sent"


            except Exception as e:

                fail_count += 1

                status = (
                    f"Failed: {str(e)}"
                )


            # ---------------------------------------------
            # Remaining emails
            # ---------------------------------------------

            remaining = total - (
                sent_count + fail_count
            )


            results.append({
                "recipient": recipient,
                "total": total,
                "sent": sent_count,
                "failed": fail_count,
                "remaining": remaining,
                "status": status
            })


            # ---------------------------------------------
            # Normal delay
            # ---------------------------------------------

            time.sleep(2)


        # =================================================
        # INVALID EMAIL RESULTS
        # =================================================

        for recipient in invalid_recipients:

            fail_count += 1

            remaining = total - (
                sent_count + fail_count
            )

            results.append({
                "recipient": recipient,
                "total": total,
                "sent": sent_count,
                "failed": fail_count,
                "remaining": remaining,
                "status": "Invalid email address"
            })


    # =====================================================
    # CONNECTION ERROR
    # =====================================================

    except Exception as e:

        remaining = total - (
            sent_count + fail_count
        )

        return jsonify([
            {
                "recipient": "ALL",
                "total": total,
                "sent": sent_count,
                "failed": fail_count,
                "remaining": max(
                    0,
                    remaining
                ),
                "status": (
                    f"Connection error: {str(e)}"
                )
            }
        ])


    # =====================================================
    # CLOSE SMTP CONNECTION
    # =====================================================

    finally:

        if server:

            try:
                server.quit()

            except Exception:
                pass


    # =====================================================
    # RETURN RESULTS
    # =====================================================

    return jsonify(results)


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
