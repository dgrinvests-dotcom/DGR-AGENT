"""
Telnyx SMS Service Integration
Handles SMS sending, delivery tracking, and webhook processing
"""

import os
from telnyx import Telnyx
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import hashlib
import hmac
import json

from schemas.agent_state import RealEstateAgentState, add_communication_attempt


class TelnyxSMSService:
    """
    Telnyx SMS service for real estate outreach
    Handles SMS sending, delivery tracking, and compliance
    """
    
    def __init__(self):
        self.api_key = os.getenv("TELNYX_API_KEY")
        self.messaging_profile_id = os.getenv("TELNYX_MESSAGING_PROFILE_ID")
        self.from_number = os.getenv("TELNYX_PHONE_NUMBER")
        self.webhook_secret = os.getenv("TELNYX_WEBHOOK_SECRET")
        
        if not self.api_key:
            raise ValueError("TELNYX_API_KEY environment variable is required")
        
        # Configure Telnyx client with new SDK
        self.client = Telnyx(api_key=self.api_key)
        
        self.logger = logging.getLogger("telnyx_service")
        
        # Message status tracking
        self.delivery_statuses = {}
    
    def send_sms(
        self, 
        to_number: str, 
        message: str, 
        state: RealEstateAgentState,
        media_urls: List[str] = None
    ) -> Dict[str, Any]:
        """
        Send SMS message with delivery tracking
        
        Args:
            to_number: Recipient phone number (E.164 format)
            message: SMS message content
            state: Current conversation state
            media_urls: Optional list of media URLs for MMS
            
        Returns:
            Dict with success status, message_id, and details
        """
        try:
            # Validate phone number format
            if not self._is_valid_phone_number(to_number):
                return {
                    "success": False,
                    "error": "Invalid phone number format",
                    "phone_number": to_number
                }
            
            # Check message length
            if len(message) > 1600:  # SMS limit
                return {
                    "success": False,
                    "error": "Message too long (max 1600 characters)",
                    "length": len(message)
                }
            
            # Prepare message data
            message_data = {
                "from": self.from_number,
                "to": to_number,
                "text": message
            }
            
            # Add messaging profile if configured
            if self.messaging_profile_id:
                message_data["messaging_profile_id"] = self.messaging_profile_id
            
            # Add media URLs for MMS
            if media_urls:
                message_data["media_urls"] = media_urls
            
            # Add webhook URL for delivery reports
            webhook_url = self._get_webhook_url()
            if webhook_url:
                message_data["webhook_url"] = webhook_url
            
            # Send SMS via Telnyx
            self.logger.info(f"Sending SMS to {to_number}: {message[:50]}...")
            
            response = self.client.messages.create(**message_data)
            
            # Extract response data
            message_id = response.data.id if hasattr(response, 'data') else response.id
            status = response.data.status if hasattr(response, 'data') else getattr(response, 'status', 'unknown')
            
            # Log successful send
            self.logger.info(f"SMS sent successfully - ID: {message_id}, Status: {status}")
            
            # Update state with communication attempt
            add_communication_attempt(
                state,
                method="sms",
                message=message,
                success=True,
                message_id=message_id
            )
            
            # Store delivery status for tracking
            self.delivery_statuses[message_id] = {
                "status": status,
                "sent_at": datetime.now().isoformat(),
                "to_number": to_number,
                "lead_id": state["lead_id"]
            }
            
            return {
                "success": True,
                "message_id": message_id,
                "status": status,
                "to_number": to_number,
                "sent_at": datetime.now().isoformat()
            }
            
        except telnyx.error.TelnyxError as e:
            error_msg = f"Telnyx API error: {str(e)}"
            self.logger.error(error_msg)
            
            # Update state with failed attempt
            add_communication_attempt(
                state,
                method="sms",
                message=message,
                success=False,
                error=error_msg
            )
            
            return {
                "success": False,
                "error": error_msg,
                "error_type": "telnyx_api_error"
            }
            
        except Exception as e:
            error_msg = f"Unexpected error sending SMS: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                "success": False,
                "error": error_msg,
                "error_type": "unexpected_error"
            }
    
    def check_delivery_status(self, message_id: str) -> Dict[str, Any]:
        """
        Check delivery status of a sent message
        
        Args:
            message_id: Telnyx message ID
            
        Returns:
            Dict with delivery status information
        """
        try:
            # Check local cache first
            if message_id in self.delivery_statuses:
                cached_status = self.delivery_statuses[message_id]
                
                # If status is final, return cached result
                if cached_status["status"] in ["delivered", "failed", "undelivered"]:
                    return {
                        "success": True,
                        "message_id": message_id,
                        "status": cached_status["status"],
                        "cached": True,
                        **cached_status
                    }
            
            # Query Telnyx API for current status
            message = telnyx.Message.retrieve(message_id)
            message_data = message.to_dict().get("data", {})
            
            status = message_data.get("status", "unknown")
            
            # Update cache
            self.delivery_statuses[message_id] = {
                "status": status,
                "updated_at": datetime.now().isoformat(),
                "message_data": message_data
            }
            
            return {
                "success": True,
                "message_id": message_id,
                "status": status,
                "cached": False,
                "message_data": message_data
            }
            
        except telnyx.error.TelnyxError as e:
            error_msg = f"Error checking delivery status: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                "success": False,
                "error": error_msg,
                "message_id": message_id
            }
    
    def process_webhook(self, webhook_data: Dict[str, Any], signature: str = None) -> Dict[str, Any]:
        """
        Process Telnyx webhook for delivery reports and incoming messages
        
        Args:
            webhook_data: Webhook payload from Telnyx
            signature: Webhook signature for verification
            
        Returns:
            Dict with processing results
        """
        try:
            # Verify webhook signature if provided
            if signature and self.webhook_secret:
                if not self._verify_webhook_signature(webhook_data, signature):
                    return {
                        "success": False,
                        "error": "Invalid webhook signature"
                    }
            
            # Extract event data
            event_type = webhook_data.get("data", {}).get("event_type")
            payload = webhook_data.get("data", {}).get("payload", {})
            
            self.logger.info(f"Processing Telnyx webhook: {event_type}")
            
            if event_type == "message.sent":
                return self._handle_message_sent(payload)
            elif event_type == "message.delivered":
                return self._handle_message_delivered(payload)
            elif event_type == "message.failed":
                return self._handle_message_failed(payload)
            elif event_type == "message.received":
                return self._handle_message_received(payload)
            else:
                self.logger.warning(f"Unhandled webhook event type: {event_type}")
                return {
                    "success": True,
                    "message": f"Event type {event_type} not handled"
                }
                
        except Exception as e:
            error_msg = f"Error processing webhook: {str(e)}"
            self.logger.error(error_msg)
            
            return {
                "success": False,
                "error": error_msg
            }
    
    def _handle_message_sent(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle message sent webhook"""
        message_id = payload.get("id")
        status = payload.get("status")
        
        if message_id:
            self.delivery_statuses[message_id] = {
                "status": status,
                "sent_at": datetime.now().isoformat(),
                "payload": payload
            }
        
        return {"success": True, "event": "message_sent", "message_id": message_id}
    
    def _handle_message_delivered(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle message delivered webhook"""
        message_id = payload.get("id")
        
        if message_id:
            self.delivery_statuses[message_id] = {
                "status": "delivered",
                "delivered_at": datetime.now().isoformat(),
                "payload": payload
            }
        
        return {"success": True, "event": "message_delivered", "message_id": message_id}
    
    def _handle_message_failed(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle message failed webhook"""
        message_id = payload.get("id")
        error_code = payload.get("error_code")
        
        if message_id:
            self.delivery_statuses[message_id] = {
                "status": "failed",
                "failed_at": datetime.now().isoformat(),
                "error_code": error_code,
                "payload": payload
            }
        
        return {"success": True, "event": "message_failed", "message_id": message_id}
    
    def _handle_message_received(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming message webhook"""
        from_number = payload.get("from", {}).get("phone_number")
        message_text = payload.get("text")
        
        # This would trigger the conversation agent to process the reply
        # For now, just log it
        self.logger.info(f"Received SMS from {from_number}: {message_text}")
        
        return {
            "success": True, 
            "event": "message_received", 
            "from": from_number,
            "message": message_text
        }
    
    def _is_valid_phone_number(self, phone_number: str) -> bool:
        """
        Validate phone number format (E.164)
        """
        import re
        
        # Basic E.164 format validation
        pattern = r'^\+[1-9]\d{1,14}$'
        return bool(re.match(pattern, phone_number))
    
    def _get_webhook_url(self) -> Optional[str]:
        """
        Get webhook URL for delivery reports
        """
        base_url = os.getenv("WEBHOOK_BASE_URL")
        if base_url:
            return f"{base_url}/webhooks/telnyx"
        return None
    
    def _verify_webhook_signature(self, payload: Dict[str, Any], signature: str) -> bool:
        """
        Verify Telnyx webhook signature
        """
        if not self.webhook_secret:
            return True  # Skip verification if no secret configured
        
        try:
            # Convert payload to string
            payload_string = json.dumps(payload, separators=(',', ':'), sort_keys=True)
            
            # Calculate expected signature
            expected_signature = hmac.new(
                self.webhook_secret.encode('utf-8'),
                payload_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            self.logger.error(f"Error verifying webhook signature: {e}")
            return False
    
    def get_messaging_stats(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get messaging statistics for the last N hours
        """
        from datetime import timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        stats = {
            "total_sent": 0,
            "delivered": 0,
            "failed": 0,
            "pending": 0,
            "delivery_rate": 0.0
        }
        
        for message_id, status_info in self.delivery_statuses.items():
            sent_time_str = status_info.get("sent_at")
            if sent_time_str:
                sent_time = datetime.fromisoformat(sent_time_str)
                if sent_time > cutoff_time:
                    stats["total_sent"] += 1
                    
                    status = status_info.get("status", "unknown")
                    if status == "delivered":
                        stats["delivered"] += 1
                    elif status in ["failed", "undelivered"]:
                        stats["failed"] += 1
                    else:
                        stats["pending"] += 1
        
        # Calculate delivery rate
        if stats["total_sent"] > 0:
            stats["delivery_rate"] = (stats["delivered"] / stats["total_sent"]) * 100
        
        return stats


# Utility functions
def format_phone_number(phone_number: str) -> str:
    """
    Format phone number to E.164 format
    """
    import re
    
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone_number)
    
    # Add country code if missing (assume US)
    if len(digits) == 10:
        digits = "1" + digits
    
    # Add + prefix
    return "+" + digits


def validate_sms_content(message: str) -> Dict[str, Any]:
    """
    Validate SMS message content for compliance and deliverability
    """
    issues = []
    
    # Check length
    if len(message) > 1600:
        issues.append("Message too long (max 1600 characters)")
    
    # Check for spam keywords (basic check)
    spam_keywords = ["free", "winner", "urgent", "act now", "limited time"]
    for keyword in spam_keywords:
        if keyword.lower() in message.lower():
            issues.append(f"Potential spam keyword detected: {keyword}")
    
    # Check for required opt-out language for marketing messages
    if "stop" not in message.lower() and "opt" not in message.lower():
        issues.append("Consider adding opt-out instructions (Reply STOP to opt out)")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "length": len(message),
        "estimated_segments": (len(message) // 160) + 1
    }
