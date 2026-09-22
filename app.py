from flask import Flask, render_template, request, jsonify
import smtplib
import re
from email.mime.text import MIMEText

app = Flask(__name__)

def is_valid_email(email):
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return re.match(pattern, email)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/send", methods=["POST"])
def send():

    sender_name = request.form.get("sender_name", "")
    sender_id = request.form.get("sender_id", "")
    app_password = request.form.get("app_password", "")
    subject = request.form.get("subject", "")
    body = request.form.get("body", "")

    recipients_text = request.form.get("recipients", "")
    recipients_text = recipients_text.replace(",", "\n")

    recipients = [
        x.strip()
        for x in recipients_text.splitlines()
        if x.strip()
    ]

    total = len(recipients)
    sent = 0
    failed = 0

    results = []

    try:

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_id, app_password)

        for email in recipients:

            try:

                if not is_valid_email(email):
                    raise Exception("Invalid Email")

                msg = MIMEText(body)

                msg["From"] = f"{sender_name} <{sender_id}>"
                msg["To"] = email
                msg["Subject"] = subject

                server.sendmail(
                    sender_id,
                    email,
                    msg.as_string()
                )

                sent += 1

                status = "Sent"

            except Exception as e:

                failed += 1

                status = str(e)

            results.append({
                "recipient": email,
                "total": total,
                "sent": sent,
                "failed": failed,
                "remaining": total - sent - failed,
                "status": status
            })

        server.quit()

        return jsonify(results)

    except Exception as e:

        return jsonify([
            {
                "recipient": "Server",
                "total": total,
                "sent": 0,
                "failed": total,
                "remaining": total,
                "status": str(e)
            }
        ])

if __name__ == "__main__":
    app.run(debug=True)
