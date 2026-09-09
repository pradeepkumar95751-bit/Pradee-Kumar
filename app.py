from flask import Flask, render_template, request
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    total = sent_count = fail_count = remaining = 0
    status = "Ready to send"

    if request.method == "POST":
        sender_name = request.form["sender_name"]
        gmail_user = request.form["gmail_user"]
        app_password = request.form["app_password"]
        subject = request.form["subject"]
        body = request.form["body"]
        recipients = request.form["recipients"].replace(",", "\n").splitlines()

        recipients = [r.strip() for r in recipients if r.strip()]
        total = len(recipients)

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
                print(f"Failed: {recipient} → {e}")
                fail_count += 1

        remaining = total - (sent_count + fail_count)
        status = "Completed sending"

    return render_template("index.html",
                           total=total,
                           sent=sent_count,
                           failed=fail_count,
                           remaining=remaining,
                           status=status)

if __name__ == "__main__":
    app.run(debug=True)
