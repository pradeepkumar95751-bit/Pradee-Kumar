from flask import Flask, render_template, request, jsonify
import smtplib
import random
import time
from email.mime.text import MIMEText

app = Flask(__name__)

# Multi-rotation dictionary (multiple variants for each risky word)
ROTATE_WORDS = {
    "rank": ["ra\u200bnk", "ran\u200bk", "ra\u200bn\u200bk"],
    "first page of google": ["first page of Goo\u200bgle", "first page of Googl\u200be", "first page of Go\u200bogle"],
    "visibility": ["visi\u200bbility", "visibil\u200bity", "vis\u200bib\u200blity"],
    "reports": ["repo\u200brts", "rep\u200borts", "re\u200bpor\u200bts"],
    "quote": ["quo\u200bte", "qu\u200bote", "q\u200buo\u200bte"],
    "information": ["infor\u200bmation", "inform\u200bation", "info\u200brma\u200btion"]
}

def rotate_text(text: str) -> str:
    text_lower = text.lower()
    for bad, variants in ROTATE_WORDS.items():
        if bad in text_lower:
            chosen = random.choice(variants)
            text = text.replace(bad, chosen)
            text = text.replace(bad.capitalize(), chosen.capitalize())
    return text

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/send", methods=["POST"])
def send():
    sender_name = request.form["sender_name"]
    sender_id = request.form["sender_id"]
    app_password = request.form["app_password"]
    subject = rotate_text(request.form["subject"])
    body = rotate_text(request.form["body"])
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

            # Normal sending speed (2 sec delay between mails)
            time.sleep(2)

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
