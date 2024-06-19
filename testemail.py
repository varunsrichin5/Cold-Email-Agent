import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Hardcoded API key
SENDGRID_API_KEY = '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'
FROM_EMAIL = 'dan@usemasssive.com'
TO_EMAIL = 'rohanghiya@gmail.com'

# Debug: Print the API key to confirm it's being read correctly
print(f"Using API Key: {SENDGRID_API_KEY}")

# Initialize SendGrid client with the hardcoded API key
sg = SendGridAPIClient(SENDGRID_API_KEY)

def send_email(to_email, subject, content):
    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=to_email,
        subject=subject,
        plain_text_content=content)

    try:
        response = sg.send(message)
        print(f"Email sent successfully to {to_email}. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error sending email to {to_email}: {str(e)}")

# Example usage
subject = "Test Email"
content = "This is a test email sent using SendGrid API."
send_email(TO_EMAIL, subject, content)
