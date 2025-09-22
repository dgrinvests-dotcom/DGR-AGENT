import os
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

class GmailIntegration:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.imap_server = "imap.gmail.com"
        self.imap_port = 993
        
        # Get credentials from environment
        self.email_address = os.getenv("GMAIL_ADDRESS")
        self.app_password = os.getenv("GMAIL_APP_PASSWORD")  # Use App Password, not regular password
        
        if not all([self.email_address, self.app_password]):
            raise ValueError("Missing Gmail credentials. Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD environment variables")
        
        self.logger = logging.getLogger(__name__)
    
    async def send_email(self, 
                        to_email: str, 
                        subject: str, 
                        body: str, 
                        is_html: bool = False) -> bool:
        """Send email via Gmail SMTP"""
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email_address
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add body
            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # Connect to Gmail SMTP
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()  # Enable TLS encryption
            server.login(self.email_address, self.app_password)
            
            # Send email
            text = msg.as_string()
            server.sendmail(self.email_address, to_email, text)
            server.quit()
            
            self.logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending email to {to_email}: {e}")
            return False
    
    async def send_property_follow_up(self, 
                                    to_email: str, 
                                    lead_name: str, 
                                    property_address: str,
                                    meet_link: str = None) -> bool:
        """Send follow-up email about property inquiry"""
        
        subject = f"Following up on your property at {property_address}"
        
        body = f"""
Hi {lead_name},

Thank you for your interest in selling your property at {property_address}.

I wanted to follow up on our conversation and provide you with some additional information:

• I buy houses for cash and can close quickly (typically 7-14 days)
• No repairs needed - I buy properties in any condition
• No real estate commissions or fees
• Free, no-obligation consultation

"""
        
        if meet_link:
            body += f"""
I've scheduled our call. Here's your Google Meet link:
{meet_link}

"""
        
        body += f"""
If you have any questions or would like to discuss your options, please don't hesitate to reach out.

Best regards,
[Your Name]
[Your Company]
[Your Phone Number]

P.S. If you're not interested in selling at this time, simply reply "REMOVE" and I'll take you off my contact list.
        """.strip()
        
        return await self.send_email(to_email, subject, body)
    
    async def send_appointment_confirmation(self, 
                                         to_email: str, 
                                         lead_name: str,
                                         meeting_time: str,
                                         meet_link: str) -> bool:
        """Send appointment confirmation email"""
        
        subject = "Appointment Confirmed - Real Estate Consultation"
        
        body = f"""
Hi {lead_name},

Your appointment has been confirmed!

Meeting Details:
• Date & Time: {meeting_time}
• Duration: 30 minutes
• Google Meet Link: {meet_link}

What to expect:
• Quick property evaluation
• Discussion of your selling timeline
• Cash offer presentation (if applicable)
• Answer any questions you have

Please save this email for your records. If you need to reschedule, just reply to this email.

Looking forward to speaking with you!

Best regards,
[Your Name]
[Your Company]
[Your Phone Number]
        """.strip()
        
        return await self.send_email(to_email, subject, body)
    
    async def send_no_show_follow_up(self, 
                                   to_email: str, 
                                   lead_name: str) -> bool:
        """Send follow-up email for missed appointments"""
        
        subject = "We missed you - Let's reschedule"
        
        body = f"""
Hi {lead_name},

I noticed we missed our scheduled call today. No worries - I understand things come up!

I'm still very interested in discussing your property and making you a cash offer.

Would you like to reschedule? Just reply with a few times that work better for you, and I'll send you a new meeting link.

Available times:
• Monday - Friday: 9 AM - 5 PM EST
• Response within 24 hours guaranteed

Best regards,
[Your Name]
[Your Company]
[Your Phone Number]
        """.strip()
        
        return await self.send_email(to_email, subject, body)
    
    async def get_recent_emails(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent emails from Gmail inbox"""
        
        try:
            # Connect to Gmail IMAP
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.app_password)
            mail.select('inbox')
            
            # Search for recent emails
            status, messages = mail.search(None, 'ALL')
            
            if status != 'OK':
                return []
            
            # Get message IDs
            message_ids = messages[0].split()
            recent_emails = []
            
            # Get the most recent emails (up to limit)
            for msg_id in message_ids[-limit:]:
                try:
                    # Fetch email
                    status, msg_data = mail.fetch(msg_id, '(RFC822)')
                    
                    if status != 'OK':
                        continue
                    
                    # Parse email
                    raw_email = msg_data[0][1]
                    email_message = email.message_from_bytes(raw_email)
                    
                    # Extract email details
                    subject = email_message.get('Subject', '')
                    from_addr = email_message.get('From', '')
                    date = email_message.get('Date', '')
                    
                    # Get email body
                    body = ""
                    if email_message.is_multipart():
                        for part in email_message.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode('utf-8')
                                break
                    else:
                        body = email_message.get_payload(decode=True).decode('utf-8')
                    
                    recent_emails.append({
                        'id': msg_id.decode(),
                        'subject': subject,
                        'from': from_addr,
                        'date': date,
                        'body': body[:500]  # First 500 characters
                    })
                    
                except Exception as e:
                    self.logger.error(f"Error parsing email {msg_id}: {e}")
                    continue
            
            mail.close()
            mail.logout()
            
            return recent_emails
            
        except Exception as e:
            self.logger.error(f"Error fetching emails: {e}")
            return []
    
    async def send_bulk_follow_up(self, 
                                leads: List[Dict[str, Any]], 
                                template_type: str = "general") -> Dict[str, int]:
        """Send bulk follow-up emails to multiple leads"""
        
        results = {"sent": 0, "failed": 0}
        
        for lead in leads:
            try:
                email_addr = lead.get('email')
                name = lead.get('first_name', 'there')
                address = lead.get('property_address', 'your property')
                
                if not email_addr:
                    results["failed"] += 1
                    continue
                
                if template_type == "general":
                    success = await self.send_property_follow_up(email_addr, name, address)
                elif template_type == "no_show":
                    success = await self.send_no_show_follow_up(email_addr, name)
                else:
                    success = await self.send_property_follow_up(email_addr, name, address)
                
                if success:
                    results["sent"] += 1
                else:
                    results["failed"] += 1
                    
                # Small delay to avoid rate limiting
                import asyncio
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error sending bulk email to {lead}: {e}")
                results["failed"] += 1
        
        return results
    
    def validate_email_address(self, email_addr: str) -> bool:
        """Basic email validation"""
        import re
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email_addr) is not None
    
    async def send_welcome_email(self, to_email: str, lead_name: str) -> bool:
        """Send welcome email to new leads"""
        
        subject = "Thank you for your interest in selling your property"
        
        body = f"""
Hi {lead_name},

Thank you for reaching out about selling your property!

I'm [Your Name], and I specialize in helping homeowners sell their properties quickly for cash. Here's what makes working with me different:

✓ Cash offers within 24 hours
✓ Close in as little as 7 days
✓ No repairs or cleaning needed
✓ No real estate commissions
✓ We handle all paperwork

I'd love to learn more about your property and situation. I'll be following up shortly to schedule a brief call.

In the meantime, feel free to reach out with any questions:
• Phone: [Your Phone Number]
• Email: {self.email_address}

Best regards,
[Your Name]
[Your Company]
        """.strip()
        
        return await self.send_email(to_email, subject, body)
