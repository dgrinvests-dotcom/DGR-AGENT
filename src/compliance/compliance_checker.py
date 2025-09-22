import os
import pytz
from datetime import datetime, time
from typing import Dict, Any, Optional, List, Set
import phonenumbers
from phonenumbers import NumberParseException
import requests
import json
import logging

class DatabaseManager:
    # This is a placeholder class for a database manager
    pass

class ComplianceChecker:
    def __init__(self):
        self.db = DatabaseManager()
        
        # Load compliance settings (DNC not needed - user provides pre-approved numbers)
        self.quiet_hours_start = self._parse_time(os.getenv("QUIET_HOURS_START", "21:00"))
        self.quiet_hours_end = self._parse_time(os.getenv("QUIET_HOURS_END", "08:00"))
        self.timezone = pytz.timezone(os.getenv("TIMEZONE", "America/New_York"))
        
        # Opt-out keywords (based on project compliance requirements)
        self.opt_out_keywords = [
            "stop", "unsubscribe", "remove", "opt out", "opt-out",
            "no more", "don't contact", "dont contact", "leave me alone"
        ]
        
        # Compliance logging for TCPA requirements
        self.logger = logging.getLogger(__name__)
        
        # In-memory opt-out list (in production, use database)
        self.opt_out_numbers: Set[str] = set()
    
    def can_contact(self, phone_number: str) -> bool:
        """Check if we can legally contact this phone number"""
        
        # Normalize phone number
        normalized_phone = self._normalize_phone(phone_number)
        if not normalized_phone:
            return False
        
        # Check opt-out list
        if normalized_phone in self.opt_out_numbers:
            return False
        
        # Check quiet hours
        if self._is_quiet_hours():
            return False
        
        # Skip DNC check - user will only add pre-approved numbers
        return True
    
    def add_to_opt_out(self, phone_number: str) -> bool:
        """Add phone number to opt-out list"""
        normalized_phone = self._normalize_phone(phone_number)
        if normalized_phone:
            self.opt_out_numbers.add(normalized_phone)
            return True
        return False
    
    def remove_from_opt_out(self, phone_number: str) -> bool:
        """Remove phone number from opt-out list (for re-opt-in)"""
        normalized_phone = self._normalize_phone(phone_number)
        if normalized_phone and normalized_phone in self.opt_out_numbers:
            self.opt_out_numbers.remove(normalized_phone)
            return True
        return False
    
    def _normalize_phone(self, phone_number: str) -> Optional[str]:
        """Normalize phone number to E.164 format"""
        try:
            # Parse the phone number (assuming US if no country code)
            parsed = phonenumbers.parse(phone_number, "US")
            
            # Validate the number
            if phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            
        except NumberParseException:
            pass
        
        return None
    
    def _is_quiet_hours(self) -> bool:
        """Check if current time is within quiet hours"""
        now = datetime.now(self.timezone).time()
        
        # Handle case where quiet hours span midnight
        if self.quiet_hours_start > self.quiet_hours_end:
            return now >= self.quiet_hours_start or now <= self.quiet_hours_end
        else:
            return self.quiet_hours_start <= now <= self.quiet_hours_end
    
    
    def _parse_time(self, time_str: str) -> time:
        """Parse time string in HH:MM format"""
        try:
            hour, minute = map(int, time_str.split(":"))
            return time(hour, minute)
        except (ValueError, AttributeError):
            # Default to 9 PM if parsing fails
            return time(21, 0)
    
    def get_compliance_report(self) -> Dict[str, Any]:
        """Generate compliance report"""
        return {
            "opt_out_count": len(self.opt_out_numbers),
            "quiet_hours_active": self._is_quiet_hours(),
            "quiet_hours_config": {
                "start": self.quiet_hours_start.strftime("%H:%M"),
                "end": self.quiet_hours_end.strftime("%H:%M"),
                "timezone": str(self.timezone)
            },
            "note": "DNC checking disabled - using pre-approved numbers only"
        }
    
    def validate_campaign_compliance(self, campaign_data: Dict[str, Any]) -> List[str]:
        """Validate campaign for compliance issues"""
        issues = []
        
        # Check for required compliance elements
        if not campaign_data.get("opt_out_instructions"):
            issues.append("Missing opt-out instructions in campaign")
        
        if not campaign_data.get("sender_identification"):
            issues.append("Missing sender identification")
        
        # Check message content for compliance
        message = campaign_data.get("message", "")
        if len(message) > 160:
            issues.append("Message exceeds SMS length limit")
        
        if "STOP" not in message.upper():
            issues.append("Message should include STOP instructions")
        
        return issues
    
    def log_contact_attempt(self, phone_number: str, method: str, success: bool, reason: str = None):
        """Log contact attempt for compliance tracking"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "phone_number": self._normalize_phone(phone_number),
            "method": method,
            "success": success,
            "reason": reason,
            "compliance_checks": {
                "quiet_hours": not self._is_quiet_hours(),
                "opt_out_status": phone_number not in self.opt_out_numbers,
                "pre_approved": True  # All numbers are pre-approved
            }
        }
        
        # In production, save to database or compliance log file
        print(f"Compliance log: {json.dumps(log_entry, indent=2)}")
        
        return log_entry
