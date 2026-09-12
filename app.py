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
    "reports": "reports",
    "quote": "quote",
    "information": "insights",
    "seo": "search optimization",
    "traffic": "visitors",
    "pricing": "costing",
    "yahoo": "portal"
}

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
    gmail_user = request.form["gmail_user"]
    app_password = request.form["app_password"]
    subject = clean_text(request.form["subject"])
    body = clean_text(request.form["body"])
    recipients = request.form["recipients"].replace(",", "\n").splitlines()
    recipients = [r.strip() for r in recipients if r.strip()]

    total = len(recipients)
    sent_count = fail_count = 0
    results = []

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

    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True)
