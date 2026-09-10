from flask import Flask, render_template, request, jsonify
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# simple spam word replacement dictionary
SPAM_WORDS = {
    "free": "complimentary",
    "offer": "proposal",
    "win": "achieve",
    "money": "funds",
    "urgent": "important",
    "guarantee": "assurance"
}

def clean_text(text):
    for bad, good in SPAM_WORDS.items():
        text = text.replace(bad, good)
    return text

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/send", methods=["POST"])
def send():
    sender_name = request.form["sender_name"]
    gmail_user = request.form["gmail_user"]
    app_password = request.form["app_password"]
    subject = clean_text(request.form["subject"])
    body = clean_text(request.form["body"])
    recipients = request.form["recipients"].replace(",", "\n").splitlines()
    recipients = [r.strip() for r in recipients if r.strip()]

    total = len(recipients)
    sent_count = fail_count = 0

    for recipient in recipients:
        try:
            msg = MIMEMultipart()
            msg["From"] = f"{sender_name} <{gmail_user}>"
            msg["To"] = recipient
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(gmail_user, app_password)
            server.sendmail(gmail_user, recipient, msg.as_string())
            server.quit()
            sent_count += 1
        except Exception as e:
            fail_count += 1

    remaining = total - (sent_count + fail_count)
    return jsonify({
        "total": total,
        "sent": sent_count,
        "failed": fail_count,
        "remaining": remaining,
        "status": "Completed sending"
    })

if __name__ == "__main__":
    app.run(debug=True)
