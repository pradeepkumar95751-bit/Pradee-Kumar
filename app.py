from flask import Flask, render_template, request, jsonify
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# Risky words list
SPAM_WORDS = [
    "rank", "google", "first page", "visibility", "yahoo",
    "quotation", "quote", "reports", "cost", "pricing",
    "seo", "traffic", "information", "info", "visible"
]

def clean_text(text: str) -> str:
    return " ".join(text.split())

def spam_score(text: str) -> int:
    score = 0
    text_lower = text.lower()
    for word in SPAM_WORDS:
        if word in text_lower:
            score += text_lower.count(word)
    return score

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

    # Spam protection check
    score = spam_score(subject + " " + body)
    if score > 5:
        return jsonify({"error": f"High spam score ({score}). Please reduce risky words."})

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
            status = "Delivered"
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
            "status": status,
            "spam_score": score
        })

    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True)
