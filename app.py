import smtplib

# Basic setup
sender_email = "your_email@gmail.com"
receiver_email = "client@example.com"
password = "your_16_digit_app_password"

# Server details
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls() # Connection secure karne ke liye

try:
    server.login(sender_email, password)
    message = "Subject: Test Mail\n\nHello, this is a test email."
    server.sendmail(sender_email, receiver_email, message)
    print("Email successfully sent!")
except Exception as e:
    print(f"Error: {e}")
finally:
    server.quit()
