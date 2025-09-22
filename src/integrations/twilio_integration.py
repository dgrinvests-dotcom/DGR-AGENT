import os
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
from typing import Dict, Any, Optional, List
import logging

class TwilioIntegration:
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.phone_number = os.getenv("TWILIO_PHONE_NUMBER")
        
        if not all([self.account_sid, self.auth_token, self.phone_number]):
            raise ValueError("Missing required Twilio credentials in environment variables")
        
        self.client = Client(self.account_sid, self.auth_token)
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
    
    async def send_sms(self, to_number: str, message: str) -> bool:
        """Send SMS message to a phone number"""
        try:
            message_obj = self.client.messages.create(
                body=message,
                from_=self.phone_number,
                to=to_number
            )
            
            self.logger.info(f"SMS sent successfully to {to_number}, SID: {message_obj.sid}")
            return True
            
        except TwilioException as e:
            self.logger.error(f"Twilio error sending SMS to {to_number}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending SMS to {to_number}: {e}")
            return False
    
    async def get_message_status(self, message_sid: str) -> Optional[Dict[str, Any]]:
        """Get the status of a sent message"""
        try:
            message = self.client.messages(message_sid).fetch()
            
            return {
                "sid": message.sid,
                "status": message.status,
                "error_code": message.error_code,
                "error_message": message.error_message,
                "date_sent": message.date_sent,
                "date_updated": message.date_updated,
                "price": message.price,
                "price_unit": message.price_unit
            }
            
        except TwilioException as e:
            self.logger.error(f"Error fetching message status for {message_sid}: {e}")
            return None
    
    async def get_incoming_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent incoming messages"""
        try:
            messages = self.client.messages.list(
                to=self.phone_number,
                limit=limit
            )
            
            return [
                {
                    "sid": msg.sid,
                    "from": msg.from_,
                    "to": msg.to,
                    "body": msg.body,
                    "date_sent": msg.date_sent,
                    "status": msg.status
                }
                for msg in messages
            ]
            
        except TwilioException as e:
            self.logger.error(f"Error fetching incoming messages: {e}")
            return []
    
    def validate_webhook(self, url: str, params: Dict[str, str], signature: str) -> bool:
        """Validate Twilio webhook signature"""
        from twilio.request_validator import RequestValidator
        
        validator = RequestValidator(self.auth_token)
        return validator.validate(url, params, signature)
    
    async def setup_webhook(self, webhook_url: str) -> bool:
        """Configure webhook URL for incoming messages"""
        try:
            # Get the phone number resource
            incoming_phone_number = self.client.incoming_phone_numbers.list(
                phone_number=self.phone_number
            )[0]
            
            # Update the webhook URL
            incoming_phone_number.update(sms_url=webhook_url)
            
            self.logger.info(f"Webhook configured successfully: {webhook_url}")
            return True
            
        except TwilioException as e:
            self.logger.error(f"Error setting up webhook: {e}")
            return False
        except IndexError:
            self.logger.error(f"Phone number {self.phone_number} not found in account")
            return False
    
    async def get_account_balance(self) -> Optional[Dict[str, Any]]:
        """Get current account balance"""
        try:
            balance = self.client.balance.fetch()
            
            return {
                "balance": balance.balance,
                "currency": balance.currency
            }
            
        except TwilioException as e:
            self.logger.error(f"Error fetching account balance: {e}")
            return None
    
    async def get_usage_stats(self, category: str = "sms") -> Optional[Dict[str, Any]]:
        """Get usage statistics for SMS"""
        try:
            from datetime import datetime, timedelta
            
            # Get usage for the last 30 days
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
            
            usage_records = self.client.usage.records.list(
                category=category,
                start_date=start_date.date(),
                end_date=end_date.date()
            )
            
            total_usage = sum(float(record.usage) for record in usage_records)
            total_price = sum(float(record.price) for record in usage_records)
            
            return {
                "category": category,
                "period_days": 30,
                "total_usage": total_usage,
                "total_price": total_price,
                "currency": usage_records[0].price_unit if usage_records else "USD"
            }
            
        except TwilioException as e:
            self.logger.error(f"Error fetching usage stats: {e}")
            return None
    
    def format_phone_number(self, phone_number: str) -> str:
        """Format phone number for Twilio (E.164 format)"""
        # Remove all non-digit characters
        digits_only = ''.join(filter(str.isdigit, phone_number))
        
        # Add country code if not present (assuming US)
        if len(digits_only) == 10:
            return f"+1{digits_only}"
        elif len(digits_only) == 11 and digits_only.startswith('1'):
            return f"+{digits_only}"
        else:
            return f"+{digits_only}"
