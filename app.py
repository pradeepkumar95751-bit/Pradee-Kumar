from flask import Flask, render_template, request, jsonify
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/send", methods=["POST"])
def send():
    sender_name = request.form["sender_name"]
    sender_id = request.form["sender_id"]
    app_password = request.form["app_password"]
    subject = request.form["subject"]
    body = request.form["body"]
    recipients = request.form["recipients"].replace(",", "\n").splitlines()
    recipients = [r.strip() for r in recipients if r.strip()]

    total = len(recipients)
    sent_count = fail_count = 0
    results = []

    smtp_config = {
        "host": "smtp.gmail.com",
        "port": 587,
        "user": "youruser@example.com",
        "password": "yourpassword"
    }

    try:
        # Ek hi connection open karo
        server = smtplib.SMTP(smtp_config["host"], smtp_config["port"])
        server.starttls()
        server.login(smtp_config["user"], smtp_config["password"])

        for recipient in recipients:
            try:
                msg = MIMEText(body, "plain")
                msg["From"] = f"{sender_name} ({sender_id}) <{smtp_config['user']}>"
                msg["To"] = recipient
                msg["Subject"] = subject

                server.sendmail(smtp_config["user"], recipient, msg.as_string())
                sent_count += 1
                status = "Sent"
            except Exception as e:
                fail_count += 1
                status = f"Failed: {e}"

            remaining = total - (sent_count + fail_count)
            results.append({
                "recipient": recipient,
                "total": total,
                "sent": sent_count,
                "failed": fail_count,
                "remaining": remaining,
                "status": status
            })
    finally:
        try:
            server.quit()
        except:
            pass

    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True)
