from flask import Flask, render_template, request, jsonify
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

# Spam word replacements dictionary
SPAM_REPLACEMENTS = {
    "rank": "position",
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
    sender_id = request.form["sender_id"]   # Gmail address
    app_password = request.form["app_password"]  # Gmail App Password
    subject = clean_text(request.form["subject"])
    body = clean_text(request.form["body"])
    recipients = request.form["recipients"].replace(",", "\n").splitlines()
    recipients = [r.strip() for r in recipients if r.strip()]

    total = len(recipients)
    sent_count = fail_count = 0
    results = []

    smtp_host = "smtp.gmail.com"
    smtp_port = 587

    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(sender_id, app_password)

        for recipient in recipients:
            try:
                msg = MIMEText(body, "plain")
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
            results.append({
                "recipient": recipient,
                "total": total,
                "sent": sent_count,
                "failed": fail_count,
                "remaining": remaining,
                "status": status
            })
    except Exception as e:
        return jsonify([{"recipient":"ALL","total":total,"sent":sent_count,"failed":fail_count,"remaining":total,"status":f"Connection error: {e}"}])
    finally:
        try:
            server.quit()
        except:
            pass

    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True)
