from flask import Flask, render_template, request, jsonify
import smtplib
import time
import re
from email.mime.text import MIMEText

app = Flask(__name__)

# =========================================================
# EMAIL VALIDATION
# =========================================================
def is_valid_email(email: str) -> bool:
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None

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
    subject = request.form.get("subject", "").strip()
    body = request.form.get("body", "").strip()
    recipients_text = request.form.get("recipients", "").replace(",", "\n")

    recipients = [r.strip() for r in recipients_text.splitlines() if r.strip()]
    valid = [r for r in recipients if is_valid_email(r)]
    invalid = [r for r in recipients if not is_valid_email(r)]

    total = len(recipients)
    sent_count = fail_count = 0
    results = []
    server = None

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_id, app_password)

        for recipient in valid:
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
                status = f"Failed: {e}"

            remaining = total - (sent_count + fail_count)
            results.append({"recipient": recipient, "total": total,
                            "sent": sent_count, "failed": fail_count,
                            "remaining": remaining, "status": status})
            time.sleep(2)  # normal delay

        for recipient in invalid:
            fail_count += 1
            remaining = total - (sent_count + fail_count)
            results.append({"recipient": recipient, "total": total,
                            "sent": sent_count, "failed": fail_count,
                            "remaining": remaining, "status": "Invalid email"})
    except Exception as e:
        return jsonify([{"recipient": "ALL", "total": total,
                         "sent": sent_count, "failed": fail_count,
                         "remaining": max(0, total - (sent_count + fail_count)),
                         "status": f"Connection error: {e}"}])
    finally:
        if server:
            try: server.quit()
            except: pass

    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True)
