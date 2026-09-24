import os
import smtplib
from email.message import EmailMessage
from twilio.rest import Client
from dotenv import load_dotenv
import re

load_dotenv()

class NotificationManager:
    def __init__(self):
        self.twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_from = os.getenv("TWILIO_FROM_NUMBER")
        self.admin_phone = os.getenv("ADMIN_MOBILE_NUMBER", "+918690023283")
        
        self.smtp_server = os.getenv("SMTP_SERVER")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_user = os.getenv("SMTP_USERNAME")
        self.smtp_pass = os.getenv("SMTP_PASSWORD")
        
        # Initialize Twilio client if configured
        if self.twilio_sid and self.twilio_token:
            self.twilio_client = Client(self.twilio_sid, self.twilio_token)
        else:
            self.twilio_client = None
            print("Warning: Twilio credentials not found. SMS notifications disabled.")

    def extract_contacts_from_cv(self, cv_text):
        """Extracts the first found email and phone number from the CV."""
        email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
        phone_pattern = r'\+?[\d\s-]{10,15}' # basic matching
        
        email_match = re.search(email_pattern, cv_text)
        phone_match = re.search(phone_pattern, cv_text)
        
        return {
            "email": email_match.group(0) if email_match else None,
            "phone": phone_match.group(0) if phone_match else None
        }

    def send_sms(self, to_number, body):
        """Sends an SMS using Twilio."""
        if not self.twilio_client:
            print(f"[MOCK SMS] To {to_number}: {body}")
            return False
            
        try:
            message = self.twilio_client.messages.create(
                body=body,
                from_=self.twilio_from,
                to=to_number
            )
            print(f"SMS sent to {to_number}. SID: {message.sid}")
            return True
        except Exception as e:
            print(f"Failed to send SMS to {to_number}: {e}")
            return False

    def send_email(self, to_email, subject, body):
        """Sends an email using SMTP."""
        if not all([self.smtp_server, self.smtp_user, self.smtp_pass]):
            print(f"[MOCK EMAIL] To {to_email}\nSubject: {subject}\nBody: {body}")
            return False
            
        try:
            msg = EmailMessage()
            msg.set_content(body)
            msg['Subject'] = subject
            msg['From'] = self.smtp_user
            msg['To'] = to_email

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            print(f"Email sent to {to_email}")
            return True
        except Exception as e:
            print(f"Failed to send email to {to_email}: {e}")
            return False

    def alert_high_match(self, job, user_phone, user_email):
        """Sends notifications to user and admin about a high match job."""
        message = f"🚨 HIGH MATCH JOB FOUND 🚨\nRole: {job.get('Position')}\nCompany: {job.get('Company')}\nURL: {job.get('URL')}"
        
        # Notify User
        if user_phone:
            self.send_sms(user_phone, message)
        if user_email:
            self.send_email(user_email, "New High Match Job Found!", message)
            
        # Notify Admin
        if self.admin_phone:
            self.send_sms(self.admin_phone, f"[ADMIN COPY] {message}")
