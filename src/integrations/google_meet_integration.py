import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
import logging

class GoogleMeetIntegration:
    def __init__(self):
        self.credentials_file = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
        self.token_file = os.getenv("GOOGLE_TOKEN_FILE", "token.json")
        self.scopes = [
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/calendar.events'
        ]
        
        self.credentials = None
        self.logger = logging.getLogger(__name__)
        
        # Load credentials if available
        self._load_credentials()
    
    def _load_credentials(self):
        """Load Google credentials from token file"""
        try:
            if os.path.exists(self.token_file):
                self.credentials = Credentials.from_authorized_user_file(
                    self.token_file, self.scopes
                )
                
                # Refresh credentials if expired
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                    self._save_credentials()
                    
        except Exception as e:
            self.logger.error(f"Error loading Google credentials: {e}")
    
    def _save_credentials(self):
        """Save credentials to token file"""
        try:
            with open(self.token_file, 'w') as token:
                token.write(self.credentials.to_json())
        except Exception as e:
            self.logger.error(f"Error saving Google credentials: {e}")
    
    def get_authorization_url(self) -> str:
        """Get authorization URL for OAuth flow"""
        try:
            flow = Flow.from_client_secrets_file(
                self.credentials_file, 
                scopes=self.scopes,
                redirect_uri='urn:ietf:wg:oauth:2.0:oob'
            )
            
            auth_url, _ = flow.authorization_url(prompt='consent')
            return auth_url
            
        except Exception as e:
            self.logger.error(f"Error getting authorization URL: {e}")
            return ""
    
    def authorize_with_code(self, auth_code: str) -> bool:
        """Complete OAuth flow with authorization code"""
        try:
            flow = Flow.from_client_secrets_file(
                self.credentials_file,
                scopes=self.scopes,
                redirect_uri='urn:ietf:wg:oauth:2.0:oob'
            )
            
            flow.fetch_token(code=auth_code)
            self.credentials = flow.credentials
            self._save_credentials()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error authorizing with code: {e}")
            return False
    
    async def create_meeting(self, 
                           title: str,
                           start_time: datetime,
                           duration_minutes: int = 30,
                           attendee_email: str = None,
                           description: str = "") -> Optional[Dict[str, Any]]:
        """Create a Google Meet meeting"""
        
        if not self.credentials:
            self.logger.error("No Google credentials available")
            return None
        
        try:
            # Calculate end time
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            # Create event payload
            event = {
                'summary': title,
                'description': description,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'America/New_York',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'America/New_York',
                },
                'conferenceData': {
                    'createRequest': {
                        'requestId': f"meet_{int(datetime.now().timestamp())}",
                        'conferenceSolutionKey': {
                            'type': 'hangoutsMeet'
                        }
                    }
                },
                'attendees': []
            }
            
            # Add attendee if provided
            if attendee_email:
                event['attendees'].append({'email': attendee_email})
            
            # Make API request
            headers = {
                'Authorization': f'Bearer {self.credentials.token}',
                'Content-Type': 'application/json'
            }
            
            url = 'https://www.googleapis.com/calendar/v3/calendars/primary/events'
            params = {'conferenceDataVersion': 1}
            
            response = requests.post(
                url, 
                headers=headers, 
                params=params,
                json=event
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Extract meeting details
            meet_link = None
            if 'conferenceData' in result and 'entryPoints' in result['conferenceData']:
                for entry in result['conferenceData']['entryPoints']:
                    if entry.get('entryPointType') == 'video':
                        meet_link = entry.get('uri')
                        break
            
            return {
                'event_id': result.get('id'),
                'meet_link': meet_link,
                'event_link': result.get('htmlLink'),
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'title': title
            }
            
        except Exception as e:
            self.logger.error(f"Error creating Google Meet: {e}")
            return None
    
    async def get_available_slots(self, 
                                date: datetime,
                                duration_minutes: int = 30) -> List[datetime]:
        """Get available time slots for a given date"""
        
        if not self.credentials:
            return []
        
        try:
            # Get events for the day
            start_of_day = date.replace(hour=9, minute=0, second=0, microsecond=0)
            end_of_day = date.replace(hour=17, minute=0, second=0, microsecond=0)
            
            headers = {
                'Authorization': f'Bearer {self.credentials.token}',
                'Content-Type': 'application/json'
            }
            
            url = 'https://www.googleapis.com/calendar/v3/calendars/primary/events'
            params = {
                'timeMin': start_of_day.isoformat() + 'Z',
                'timeMax': end_of_day.isoformat() + 'Z',
                'singleEvents': True,
                'orderBy': 'startTime'
            }
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            events = response.json().get('items', [])
            
            # Find available slots
            available_slots = []
            current_time = start_of_day
            
            for event in events:
                event_start = datetime.fromisoformat(
                    event['start'].get('dateTime', event['start'].get('date'))
                )
                event_end = datetime.fromisoformat(
                    event['end'].get('dateTime', event['end'].get('date'))
                )
                
                # Add slots before this event
                while current_time + timedelta(minutes=duration_minutes) <= event_start:
                    available_slots.append(current_time)
                    current_time += timedelta(minutes=30)  # 30-minute intervals
                
                # Move current time to after this event
                current_time = max(current_time, event_end)
            
            # Add remaining slots until end of day
            while current_time + timedelta(minutes=duration_minutes) <= end_of_day:
                available_slots.append(current_time)
                current_time += timedelta(minutes=30)
            
            return available_slots
            
        except Exception as e:
            self.logger.error(f"Error getting available slots: {e}")
            return []
    
    async def cancel_meeting(self, event_id: str) -> bool:
        """Cancel a Google Meet meeting"""
        
        if not self.credentials:
            return False
        
        try:
            headers = {
                'Authorization': f'Bearer {self.credentials.token}',
            }
            
            url = f'https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}'
            
            response = requests.delete(url, headers=headers)
            response.raise_for_status()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error cancelling meeting: {e}")
            return False
    
    async def get_meeting_details(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a scheduled meeting"""
        
        if not self.credentials:
            return None
        
        try:
            headers = {
                'Authorization': f'Bearer {self.credentials.token}',
            }
            
            url = f'https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}'
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            event = response.json()
            
            # Extract meeting link
            meet_link = None
            if 'conferenceData' in event and 'entryPoints' in event['conferenceData']:
                for entry in event['conferenceData']['entryPoints']:
                    if entry.get('entryPointType') == 'video':
                        meet_link = entry.get('uri')
                        break
            
            return {
                'event_id': event.get('id'),
                'title': event.get('summary'),
                'description': event.get('description'),
                'start_time': event.get('start', {}).get('dateTime'),
                'end_time': event.get('end', {}).get('dateTime'),
                'meet_link': meet_link,
                'status': event.get('status'),
                'attendees': [att.get('email') for att in event.get('attendees', [])]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting meeting details: {e}")
            return None
    
    def generate_booking_link(self, lead_name: str = "", property_address: str = "") -> str:
        """Generate a simple booking instruction since Google Meet doesn't have public booking pages"""
        
        # This creates a simple message with instructions
        # In a real implementation, you might create a simple web form
        # or integrate with a scheduling service that works with Google Calendar
        
        return f"""
To schedule a call about your property:

1. Reply with your preferred date and time
2. I'll send you a Google Meet link
3. Available times: Monday-Friday 9 AM - 5 PM EST

Example: "Tuesday 2 PM" or "Wednesday morning"
        """.strip()
    
    async def create_quick_meeting(self, minutes_from_now: int = 15) -> Optional[str]:
        """Create a quick meeting starting in X minutes"""
        
        start_time = datetime.now() + timedelta(minutes=minutes_from_now)
        
        meeting = await self.create_meeting(
            title="Real Estate Consultation Call",
            start_time=start_time,
            duration_minutes=30,
            description="Quick consultation call about your property"
        )
        
        if meeting:
            return meeting.get('meet_link')
        
        return None
