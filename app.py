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

    smtp_host = "smtp.gmail.com"
    smtp_port = 587
    smtp_user = sender_id   # Gmail address
    smtp_pass = app_password  # 16-digit App Password

    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)

        for recipient in recipients:
            try:
                msg = MIMEText(body, "plain")
                msg["From"] = f"{sender_name} <{smtp_user}>"
                msg["To"] = recipient
                msg["Subject"] = subject

                server.sendmail(smtp_user, recipient, msg.as_string())
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
