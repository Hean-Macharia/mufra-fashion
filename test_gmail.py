import smtplib
from email.message import EmailMessage

# Your credentials
EMAIL_ADDRESS = "winnersb27@gmail.com"
EMAIL_PASSWORD = "lyhmtrlffzjkquej"  # Without spaces

# Test email
msg = EmailMessage()
msg['Subject'] = "Test Email from Python"
msg['From'] = EMAIL_ADDRESS
msg['To'] = "winnersb27@gmail.com"
msg.set_content("This is a test email using App Password")

try:
    with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
        smtp.starttls()
        print("TLS started...")
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        print("Login successful...")
        smtp.send_message(msg)
        print("Email sent successfully!")
except Exception as e:
    print(f"Error: {e}")