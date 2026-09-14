from flask import Flask, render_template, request, jsonify
import smtplib
import random
import time
import re
from email.mime.text import MIMEText

app = Flask(__name__)

# =========================================================
# MULTI ROTATION WORDS
# =========================================================
ROTATE_WORDS = {
    "rank": ["ra\u200bnk", "ran\u200bk", "ra\u200bn\u200bk"],
    "first page of google": ["first page of Goo\u200bgle", "first page of Googl\u200be", "first page of Go\u200bogle"],
    "visibility": ["visi\u200bbility", "visibil\u200bity", "vis\u200bib\u200blity"],
    "reports": ["repo\u200brts", "rep\u200borts", "re\u200bpor\u200bts"],
    "quote": ["quo\u200bte", "qu\u200bote", "q\u200buo\u200bte"],
    "information": ["infor\u200bmation", "inform\u200bation", "info\u200brma\u200btion"]
}

# =========================================================
# ROTATION FUNCTION
# =========================================================
def rotate_text(text: str) -> str:
    for word, variants in ROTATE_WORDS.items():
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        if pattern.search(text):
            selected = random.choice(variants)
            text = pattern.sub(selected, text)
    return text

# =========================================================
# EMAIL VALIDATION
# =========================================================
def is_valid_email(email: str) -> bool:
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
    sender_name = request.form.get("sender_name", "").strip()
    sender_id = request.form.get("sender_id", "").strip()
    app_password = request.form.get("app_password", "").strip()
    subject = rotate_text(request.form.get("subject", "").strip())
    body = rotate_text(request.form.get("body", "").strip())
    recipients_text = request.form.get("recipients", "").replace(",", "\n")

    recipients = [email.strip() for email in recipients_text.splitlines() if email.strip()]
    valid_recipients = [email for email in recipients if is_valid_email(email)]
    invalid_recipients = [email for email in recipients if not is_valid_email(email)]

    total = len(recipients)
    sent_count = fail_count = 0
    results = []
    server = None

    try:
        smtp_host = "smtp.gmail.com"
        smtp_port = 587
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(sender_id, app_password)

        # Send to valid recipients
        for recipient in valid_recipients:
            try:
                msg = MIMEText(body, "plain", "utf-8")
                msg["From"] = f"{sender_name} <{sender_id}>"
                msg["To"] = recipient
                msg["Subject"] = subject

                server.sendmail(sender_id, recipient, msg.as_string())
                sent_count += 1
                status = "Sent"
            except Exception as e:
                fail_count += 1
                status = f"Failed: {str(e)}"

            remaining = total - (sent_count + fail_count)
            results.append({
                "recipient": recipient,
                "total": total,
                "sent": sent_count,
                "failed": fail_count,
                "remaining": remaining,
                "status": status
            })

            # Normal delay
            time.sleep(2)

        # Handle invalid emails
        for recipient in invalid_recipients:
            fail_count += 1
            remaining = total - (sent_count + fail_count)
            results.append({
                "recipient": recipient,
                "total": total,
                "sent": sent_count,
                "failed": fail_count,
                "remaining": remaining,
                "status": "Invalid email address"
            })

    except Exception as e:
        remaining = total - (sent_count + fail_count)
        return jsonify([{
            "recipient": "ALL",
            "total": total,
            "sent": sent_count,
            "failed": fail_count,
            "remaining": max(0, remaining),
            "status": f"Connection error: {str(e)}"
        }])
    finally:
        if server:
            try:
                server.quit()
            except Exception:
                pass

    return jsonify(results)

# =========================================================
# RUN APP
# =========================================================
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
