import os
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json

class CalendlyIntegration:
    def __init__(self):
        self.api_token = os.getenv("CALENDLY_API_TOKEN")
        self.user_uri = os.getenv("CALENDLY_USER_URI")
        self.base_url = "https://api.calendly.com"
        
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
    
    async def get_booking_link(self, event_type: str = "consultation") -> str:
        """Get the booking link for a specific event type"""
        try:
            # Get available event types
            event_types = await self.get_event_types()
            
            # Find the consultation event type or use the first available
            target_event = None
            for event in event_types:
                if event_type.lower() in event.get("name", "").lower():
                    target_event = event
                    break
            
            if not target_event and event_types:
                target_event = event_types[0]  # Use first available
            
            if target_event:
                return target_event.get("scheduling_url", "")
            
            # Fallback to generic booking page
            return f"https://calendly.com/{self.user_uri.split('/')[-1]}"
            
        except Exception as e:
            print(f"Error getting Calendly booking link: {e}")
            return f"https://calendly.com/{self.user_uri.split('/')[-1]}"
    
    async def get_event_types(self) -> List[Dict[str, Any]]:
        """Get available event types for the user"""
        try:
            url = f"{self.base_url}/event_types"
            params = {"user": self.user_uri}
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            return data.get("collection", [])
            
        except Exception as e:
            print(f"Error fetching event types: {e}")
            return []
    
    async def get_scheduled_events(self, start_date: datetime = None, end_date: datetime = None) -> List[Dict[str, Any]]:
        """Get scheduled events within a date range"""
        try:
            if not start_date:
                start_date = datetime.utcnow()
            if not end_date:
                end_date = start_date + timedelta(days=30)
            
            url = f"{self.base_url}/scheduled_events"
            params = {
                "user": self.user_uri,
                "min_start_time": start_date.isoformat(),
                "max_start_time": end_date.isoformat()
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            return data.get("collection", [])
            
        except Exception as e:
            print(f"Error fetching scheduled events: {e}")
            return []
    
    async def get_event_details(self, event_uuid: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific scheduled event"""
        try:
            url = f"{self.base_url}/scheduled_events/{event_uuid}"
            
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            return response.json().get("resource", {})
            
        except Exception as e:
            print(f"Error fetching event details: {e}")
            return None
    
    async def cancel_event(self, event_uuid: str, reason: str = "Cancelled by system") -> bool:
        """Cancel a scheduled event"""
        try:
            url = f"{self.base_url}/scheduled_events/{event_uuid}/cancellation"
            
            payload = {
                "reason": reason
            }
            
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            return True
            
        except Exception as e:
            print(f"Error cancelling event: {e}")
            return False
    
    async def get_invitee_details(self, event_uuid: str) -> List[Dict[str, Any]]:
        """Get invitee details for a scheduled event"""
        try:
            url = f"{self.base_url}/scheduled_events/{event_uuid}/invitees"
            
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            return data.get("collection", [])
            
        except Exception as e:
            print(f"Error fetching invitee details: {e}")
            return []
    
    async def check_no_shows(self) -> List[Dict[str, Any]]:
        """Check for no-shows in recent appointments"""
        try:
            # Get events from the past 7 days
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)
            
            events = await self.get_scheduled_events(start_date, end_date)
            no_shows = []
            
            for event in events:
                event_time = datetime.fromisoformat(event.get("start_time", "").replace("Z", "+00:00"))
                
                # If event was more than 30 minutes ago and status is still scheduled
                if (datetime.utcnow() - event_time).total_seconds() > 1800:  # 30 minutes
                    if event.get("status") == "active":  # Still shows as scheduled
                        invitees = await self.get_invitee_details(event.get("uri", "").split("/")[-1])
                        
                        for invitee in invitees:
                            if invitee.get("status") == "no_show":
                                no_shows.append({
                                    "event": event,
                                    "invitee": invitee,
                                    "phone": self._extract_phone_from_invitee(invitee)
                                })
            
            return no_shows
            
        except Exception as e:
            print(f"Error checking no-shows: {e}")
            return []
    
    def _extract_phone_from_invitee(self, invitee: Dict[str, Any]) -> Optional[str]:
        """Extract phone number from invitee data"""
        # Check custom questions for phone number
        questions = invitee.get("tracking", {}).get("utm_source", "")
        
        # This would need to be customized based on how you collect phone numbers
        # in your Calendly booking form
        
        return None  # Placeholder - implement based on your form setup
    
    async def create_webhook(self, webhook_url: str, events: List[str] = None) -> bool:
        """Create a webhook for Calendly events"""
        try:
            if not events:
                events = ["invitee.created", "invitee.canceled"]
            
            url = f"{self.base_url}/webhook_subscriptions"
            
            payload = {
                "url": webhook_url,
                "events": events,
                "organization": self.user_uri.replace("/users/", "/organizations/"),
                "scope": "user"
            }
            
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            return True
            
        except Exception as e:
            print(f"Error creating webhook: {e}")
            return False
