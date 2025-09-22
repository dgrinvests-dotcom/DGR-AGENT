import os
import requests
from typing import Dict, Any, Optional, List
import logging
import json

class TelnyxIntegration:
    def __init__(self):
        self.api_key = os.getenv("TELNYX_API_KEY")
        self.messaging_profile_id = os.getenv("TELNYX_MESSAGING_PROFILE_ID")
        self.phone_number = os.getenv("TELNYX_PHONE_NUMBER")
        self.base_url = "https://api.telnyx.com/v2"
        
        if not all([self.api_key, self.messaging_profile_id, self.phone_number]):
            raise ValueError("Missing required Telnyx credentials in environment variables")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
    
    async def send_sms(self, to_number: str, message: str) -> bool:
        """Send SMS message to a phone number"""
        try:
            url = f"{self.base_url}/messages"
            
            payload = {
                "from": self.phone_number,
                "to": to_number,
                "text": message,
                "messaging_profile_id": self.messaging_profile_id
            }
            
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            message_id = result.get("data", {}).get("id")
            
            self.logger.info(f"SMS sent successfully to {to_number}, ID: {message_id}")
            return True
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Telnyx error sending SMS to {to_number}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending SMS to {to_number}: {e}")
            return False
    
    async def get_message_status(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a sent message"""
        try:
            url = f"{self.base_url}/messages/{message_id}"
            
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            result = response.json()
            data = result.get("data", {})
            
            return {
                "id": data.get("id"),
                "status": data.get("status"),
                "direction": data.get("direction"),
                "from": data.get("from"),
                "to": data.get("to"),
                "text": data.get("text"),
                "sent_at": data.get("sent_at"),
                "received_at": data.get("received_at")
            }
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching message status for {message_id}: {e}")
            return None
    
    async def get_incoming_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent incoming messages"""
        try:
            url = f"{self.base_url}/messages"
            params = {
                "filter[direction]": "inbound",
                "filter[to]": self.phone_number,
                "page[size]": limit
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            result = response.json()
            messages = result.get("data", [])
            
            return [
                {
                    "id": msg.get("id"),
                    "from": msg.get("from"),
                    "to": msg.get("to"),
                    "text": msg.get("text"),
                    "received_at": msg.get("received_at"),
                    "status": msg.get("status")
                }
                for msg in messages
            ]
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching incoming messages: {e}")
            return []
    
    def validate_webhook(self, payload: str, signature: str, timestamp: str) -> bool:
        """Validate Telnyx webhook signature"""
        try:
            import hmac
            import hashlib
            
            # Get webhook signing secret from environment
            signing_secret = os.getenv("TELNYX_WEBHOOK_SECRET")
            if not signing_secret:
                self.logger.warning("No Telnyx webhook secret configured")
                return True  # Skip validation if no secret
            
            # Create expected signature
            expected_signature = hmac.new(
                signing_secret.encode(),
                f"{timestamp}|{payload}".encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            self.logger.error(f"Error validating webhook signature: {e}")
            return False
    
    async def setup_webhook(self, webhook_url: str) -> bool:
        """Configure webhook URL for incoming messages"""
        try:
            url = f"{self.base_url}/messaging_profiles/{self.messaging_profile_id}"
            
            payload = {
                "inbound_webhook_url": webhook_url,
                "webhook_failover_url": f"{webhook_url}/failover"
            }
            
            response = requests.patch(url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            self.logger.info(f"Webhook configured successfully: {webhook_url}")
            return True
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error setting up webhook: {e}")
            return False
    
    async def get_account_balance(self) -> Optional[Dict[str, Any]]:
        """Get current account balance"""
        try:
            url = f"{self.base_url}/balance"
            
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            result = response.json()
            data = result.get("data", {})
            
            return {
                "balance": data.get("balance"),
                "currency": data.get("currency"),
                "credit_limit": data.get("credit_limit")
            }
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching account balance: {e}")
            return None
    
    async def get_messaging_profile(self) -> Optional[Dict[str, Any]]:
        """Get messaging profile details"""
        try:
            url = f"{self.base_url}/messaging_profiles/{self.messaging_profile_id}"
            
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            result = response.json()
            return result.get("data", {})
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching messaging profile: {e}")
            return None
    
    def format_phone_number(self, phone_number: str) -> str:
        """Format phone number for Telnyx (E.164 format)"""
        # Remove all non-digit characters
        digits_only = ''.join(filter(str.isdigit, phone_number))
        
        # Add country code if not present (assuming US)
        if len(digits_only) == 10:
            return f"+1{digits_only}"
        elif len(digits_only) == 11 and digits_only.startswith('1'):
            return f"+{digits_only}"
        else:
            return f"+{digits_only}"
