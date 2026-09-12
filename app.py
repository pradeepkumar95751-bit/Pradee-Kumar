from flask import Flask, render_template, request, jsonify
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# Spam word replacements dictionary
SPAM_REPLACEMENTS = {
    "rank": "rank",
    "first page of google": "top search results",
    "visibility": "online presence",
    "reports": "analysis",
    "quote": "proposal",
    "information": "insights",
    "seo": "search optimization",
    "traffic": "visitors",
    "pricing": "costing",
    "yahoo": "portal"
}

# Multiple SMTP servers (each with unique IP)
SMTP_SERVERS = [
    {"host": "smtp1.example.com", "port": 587, "user": "user1@example.com", "password": "pass1"},
    {"host": "smtp2.example.com", "port": 587, "user": "user2@example.com", "password": "pass2"},
    {"host": "smtp3.example.com", "port": 587, "user": "user3@example.com", "password": "pass3"},
]

def clean_text(text):
    text_lower = text.lower()
    for bad, good in SPAM_REPLACEMENTS.items():
        if bad in text_lower:
            text = text.replace(bad, good)
            text = text.replace(bad.capitalize(), good.capitalize())
    return text

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/send", methods=["POST"])
def send():
    sender_name = request.form["sender_name"]
    subject = clean_text(request.form["subject"])
    body = clean_text(request.form["body"])
    recipients = request.form["recipients"].replace(",", "\n").splitlines()
    recipients = [r.strip() for r in recipients if r.strip()]

    total = len(recipients)
    sent_count = fail_count = 0
    results = []

    for i, recipient in enumerate(recipients):
        smtp_config = SMTP_SERVERS[i % len(SMTP_SERVERS)]  # rotate servers
        try:
            msg = MIMEMultipart()
            msg["From"] = f"{sender_name} <{smtp_config['user']}>"
            msg["To"] = recipient
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            server = smtplib.SMTP(smtp_config["host"], smtp_config["port"])
            server.starttls()
            server.login(smtp_config["user"], smtp_config["password"])
            server.sendmail(smtp_config["user"], recipient, msg.as_string())
            server.quit()
            sent_count += 1
            status = f"Sent via {smtp_config['host']}"
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

    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True)
