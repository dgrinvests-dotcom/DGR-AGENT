"""
Booking Agent - Google Calendar & Meet Integration
Handles appointment scheduling and calendar management
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import requests
import json
import base64
from email.mime.text import MIMEText

from agents.base_agent import BaseRealEstateAgent
from schemas.agent_state import (
    RealEstateAgentState, 
    update_state_timestamp,
    advance_conversation_stage
)


class BookingAgent(BaseRealEstateAgent):
    """
    Booking Agent responsible for:
    - Google Calendar integration for appointment scheduling
    - Google Meet link generation and sharing
    - Follow-up scheduling for no-shows
    - Meeting confirmation and reminders
    - Calendar availability checking
    """
    
    def __init__(self):
        super().__init__("booking_agent")
        
        # Google Calendar configuration
        self.google_calendar_credentials = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_PATH")
        self.google_calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
        self.google_service_account_key = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")
        
        # Google Calendar API setup
        self.calendar_service = None
        self._initialize_google_services()
        
        # Default meeting configuration
        self.default_meeting_duration = 15  # minutes
        self.meeting_buffer = 30  # minutes between meetings
        
        # Meeting types by property type
        self.meeting_types = {
            "fix_flip": "Property Consultation - Fix & Flip",
            "vacant_land": "Land Consultation - 15 Minutes",
            "long_term_rental": "Rental Property Consultation"
        }
    
    def _initialize_google_services(self):
        """
        Initialize Google Calendar and Meet services
        """
        try:
            # Try to initialize Google Calendar service
            if self.google_calendar_credentials or self.google_service_account_key:
                from google.oauth2.service_account import Credentials
                from googleapiclient.discovery import build
                
                if self.google_service_account_key:
                    # Use service account key
                    credentials_info = json.loads(self.google_service_account_key)
                    credentials = Credentials.from_service_account_info(
                        credentials_info,
                        scopes=['https://www.googleapis.com/auth/calendar']
                    )
                else:
                    # Use credentials file
                    credentials = Credentials.from_service_account_file(
                        self.google_calendar_credentials,
                        scopes=['https://www.googleapis.com/auth/calendar']
                    )
                
                self.calendar_service = build('calendar', 'v3', credentials=credentials)
                self.google_available = True
                self.logger.info("Google Calendar service initialized successfully")
                
            else:
                self.calendar_service = None
                self.google_available = False
                self.logger.warning("Google Calendar credentials not configured")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize Google services: {e}")
            self.calendar_service = None
            self.google_available = False
    
    def process_message(self, state: RealEstateAgentState, user_message: str = None) -> Dict[str, Any]:
        """
        Process booking request and schedule appointment
        """
        try:
            self.log_agent_action(state, "processing_booking_request")
            
            # Update agent tracking
            state["current_agent"] = "booking_agent"
            if "booking_agent" not in state["agent_history"]:
                state["agent_history"].append("booking_agent")
            
            # If SMS agent already confirmed time+email, auto-schedule now
            bc = state.get("booking_context", {}) or {}
            if bc.get("confirmed_time") and (bc.get("email") or state.get("lead_email")):
                confirmed_str = bc.get("confirmed_time")
                lead_email = (bc.get("email") or state.get("lead_email"))
                # Try to parse to datetime using existing helper on the string
                selected_time = self._parse_time_selection(confirmed_str) if hasattr(self, "_parse_time_selection") else None
                if not selected_time:
                    # Fallback: schedule for next business day at 2 PM
                    from datetime import datetime, timedelta
                    selected_time = (datetime.now() + timedelta(days=1)).replace(hour=14, minute=0, second=0, microsecond=0)
                
                event_result = self.create_google_meet_event(state, selected_time)
                suppress = bool(state.get("suppress_booking_message"))
                if event_result.get("success"):
                    meet_link = event_result.get("meet_link")
                    formatted_time = selected_time.strftime('%A, %B %d at %I:%M %p')
                    state["booking_details"] = {
                        "scheduled_time": selected_time.isoformat(),
                        "meet_link": meet_link,
                        "event_id": event_result.get("event_id"),
                        "status": "scheduled"
                    }
                    state["conversation_stage"] = "scheduled"
                    # Send a confirmation email as well (backup to Google invite emails)
                    self._send_confirmation_email(state, lead_email, formatted_time, meet_link)
                    if suppress:
                        return {
                            "next_agent": "supervisor",
                            "action": "scheduled_no_sms",
                            "state_updates": {
                                "conversation_stage": "scheduled",
                                "booking_details": state["booking_details"],
                                "next_action": None
                            }
                        }
                    else:
                        message = f"All set! I’ve scheduled us for {formatted_time}. I’ve also emailed the Meet invite to {lead_email}." + (f" Link: {meet_link}" if meet_link else "")
                        return {
                            "next_agent": "communication_router",
                            "action": "send_message",
                            "message": message,
                            "state_updates": {
                                "conversation_stage": "scheduled",
                                "booking_details": state["booking_details"],
                                "next_action": "send_message"
                            }
                        }
                else:
                    # Could not create calendar event; still confirm via SMS and rely on manual follow-up
                    formatted_time = selected_time.strftime('%A, %B %d at %I:%M %p')
                    # Attempt to send a manual confirmation email if Gmail is available
                    self._send_confirmation_email(state, lead_email, formatted_time, None)
                    if suppress:
                        return {
                            "next_agent": "supervisor",
                            "action": "scheduled_no_sms",
                            "state_updates": {"next_action": None}
                        }
                    else:
                        message = f"I’ve noted {formatted_time}. I’ll follow up with a calendar invite to {lead_email} shortly."
                        return {
                            "next_agent": "communication_router",
                            "action": "send_message",
                            "message": message,
                            "state_updates": {"next_action": "send_message"}
                        }
            
            # Handle different booking scenarios
            if user_message:
                return self._handle_booking_response(state, user_message)
            else:
                return self._initiate_booking_process(state)
                
        except Exception as e:
            self.handle_error(state, e)
            return {"next_agent": "supervisor", "action": "error"}

    def _send_confirmation_email(self, state: RealEstateAgentState, to_email: str, formatted_time: str, meet_link: Optional[str]):
        """Send a confirmation email using the EmailAgent if configured."""
        try:
            if not to_email:
                return
            from agents.email_agent import EmailAgent
            email_agent = EmailAgent()
            if not getattr(email_agent, 'email_available', False):
                return
            subject = f"Confirmed: 15-minute Google Meet on {formatted_time}"
            body_lines = [
                f"Hi {state['lead_name']},",
                "",
                f"This confirms our 15-minute call on {formatted_time}.",
                (f"Google Meet link: {meet_link}" if meet_link else "You'll receive a calendar invite with the Meet link shortly."),
                "",
                "If you need to reschedule, just reply to this email.",
                "",
                "Thanks,",
                state.get('agent_name', 'Derek')
            ]
            body = "\n".join(body_lines)
            email_agent._send_email(
                to_email=to_email,
                subject=subject,
                message=body,
                state=state,
                threading_info=None
            )
        except Exception as e:
            self.logger.error(f"Failed to send confirmation email: {e}")
    
    def _initiate_booking_process(self, state: RealEstateAgentState) -> Dict[str, Any]:
        """
        Start the booking process
        """
        # Generate booking message with Calendly link
        booking_message = self._generate_booking_message(state)
        
        # Update conversation stage
        advance_conversation_stage(state, "booking")
        
        return {
            "next_agent": "communication_router",
            "action": "send_message",
            "message": booking_message,
            "state_updates": {
                "conversation_stage": "booking",
                "next_action": "send_message"
            }
        }
    
    def _handle_booking_response(self, state: RealEstateAgentState, user_message: str) -> Dict[str, Any]:
        """
        Handle user response to booking request
        """
        # Analyze user message for booking intent
        analysis = self.analyze_user_message(user_message, {
            "context": "booking_request",
            "property_type": state["property_type"]
        })
        
        intent = analysis.get("intent", "unknown")
        
        if intent == "ready_to_book" or any(word in user_message.lower() for word in ["yes", "sure", "ok", "schedule", "book"]):
            return self._provide_booking_options(state)
        elif intent == "not_interested" or any(word in user_message.lower() for word in ["no", "not interested", "not now"]):
            return self._handle_booking_declined(state)
        elif any(word in user_message.lower() for word in ["when", "time", "available", "schedule"]):
            return self._provide_availability(state)
        else:
            return self._clarify_booking_preference(state, user_message)
    
    def _generate_booking_message(self, state: RealEstateAgentState) -> str:
        """
        Generate booking message with Google Meet scheduling
        """
        lead_name = state["lead_name"]
        property_type = state["property_type"]
        property_address = state["property_address"]
        
        # Get property-specific meeting type
        meeting_type = self.meeting_types.get(property_type, "Property Consultation")
        
        # Generate available time slots
        available_times = self._get_available_time_slots()
        
        if property_type == "vacant_land":
            message = f"""Perfect, {lead_name}! I'd love to learn more about your land near {property_address}.

The next step is simple: let's schedule a quick 15-minute consultation where I can:
• Review your land details
• Provide a cash offer range
• Answer any questions you have

Here are some available times:
{available_times}

Just reply with your preferred time and I'll send you a Google Meet link!

Or if none of these work, let me know what day/time is better for you."""
        
        elif property_type == "fix_flip":
            message = f"""Excellent, {lead_name}! Based on what you've shared about {property_address}, I'd like to schedule a quick call to:
• Review the property details
• Provide a fair cash offer range  
• Explain our simple process

It's just 15 minutes and completely no-obligation.

Here are some available times:
{available_times}

Just reply with your preferred time and I'll send you a Google Meet link!

Or let me know what works better - afternoon or evening this week?"""
        
        else:  # long_term_rental
            message = f"""Great, {lead_name}! I'd love to discuss your rental property at {property_address}.

Let's schedule a quick 15-minute call where I can:
• Review your rental situation
• Explain how we work with existing leases
• Provide a cash offer range

Here are some available times:
{available_times}

Just reply with your preferred time and I'll send you a Google Meet link!

Or tell me your preference - morning, afternoon, or evening?"""
        
        return message
    
    def _provide_booking_options(self, state: RealEstateAgentState) -> Dict[str, Any]:
        """
        Provide specific booking options and times
        """
        lead_name = state["lead_name"]
        
        # Get available time slots
        available_slots = self._get_available_time_slots()
        
        message = f"""Perfect, {lead_name}! Here are some options for our call:

{available_slots}

Just reply with your preferred time and I'll create a Google Meet link for us!

If none of these times work, let me know what would be better for you."""
        
        return {
            "next_agent": "communication_router",
            "action": "send_message",
            "message": message,
            "state_updates": {"next_action": "send_message"}
        }
    
    def _provide_availability(self, state: RealEstateAgentState) -> Dict[str, Any]:
        """
        Provide availability information
        """
        lead_name = state["lead_name"]
        available_slots = self._get_available_time_slots()
        
        message = f"""Here's my availability, {lead_name}:

{available_slots}

Just reply with your preferred time and I'll send you a Google Meet link!

Or tell me which day/time works best for you."""
        
        return {
            "next_agent": "communication_router",
            "action": "send_message",
            "message": message,
            "state_updates": {"next_action": "send_message"}
        }
    
    def _handle_booking_declined(self, state: RealEstateAgentState) -> Dict[str, Any]:
        """
        Handle when user declines booking
        """
        lead_name = state["lead_name"]
        
        message = f"""No problem at all, {lead_name}! I understand you might need some time to think about it.

If you change your mind or have any questions, feel free to reach out anytime. I'm here to help when you're ready.

Have a great day!"""
        
        advance_conversation_stage(state, "not_interested")
        
        return {
            "next_agent": "communication_router",
            "action": "send_message",
            "message": message,
            "state_updates": {
                "conversation_stage": "not_interested",
                "next_action": "send_message"
            }
        }
    
    def _clarify_booking_preference(self, state: RealEstateAgentState, user_message: str) -> Dict[str, Any]:
        """
        Clarify booking preferences based on user message
        """
        lead_name = state["lead_name"]
        
        message = f"""I want to make this as convenient as possible for you, {lead_name}.

Would you prefer to:
1. Pick a time yourself using my calendar link
2. Have me suggest some specific times
3. Schedule for a different day

Just let me know what works best!"""
        
        return {
            "next_agent": "communication_router",
            "action": "send_message",
            "message": message,
            "state_updates": {"next_action": "send_message"}
        }
    
    def create_google_meet_event(self, state: RealEstateAgentState, meeting_datetime: datetime) -> Dict[str, Any]:
        """
        Create Google Calendar event with Google Meet link
        """
        try:
            if not self.google_available:
                return {"success": False, "error": "Google Calendar not available"}
            
            lead_name = state["lead_name"]
            property_address = state["property_address"]
            property_type = state["property_type"]
            lead_email = state.get("lead_email")
            
            # Create event
            event = {
                'summary': f'{self.meeting_types[property_type]} - {lead_name}',
                'description': f'Property consultation for {property_address}\n\nProperty Type: {property_type.replace("_", " ").title()}\nLead: {lead_name}',
                'start': {
                    'dateTime': meeting_datetime.isoformat(),
                    'timeZone': 'America/New_York',  # TODO: Get from lead timezone
                },
                'end': {
                    'dateTime': (meeting_datetime + timedelta(minutes=self.default_meeting_duration)).isoformat(),
                    'timeZone': 'America/New_York',
                },
                'conferenceData': {
                    'createRequest': {
                        'requestId': f"meet_{state['lead_id']}_{int(meeting_datetime.timestamp())}",
                        'conferenceSolutionKey': {
                            'type': 'hangoutsMeet'
                        }
                    }
                },
                'attendees': []
            }
            
            # Add lead email if available
            if lead_email:
                event['attendees'].append({'email': lead_email})
            
            # Create the event
            created_event = self.calendar_service.events().insert(
                calendarId=self.google_calendar_id,
                body=event,
                conferenceDataVersion=1
            ).execute()
            
            # Extract Google Meet link
            meet_link = None
            if 'conferenceData' in created_event and 'entryPoints' in created_event['conferenceData']:
                for entry_point in created_event['conferenceData']['entryPoints']:
                    if entry_point['entryPointType'] == 'video':
                        meet_link = entry_point['uri']
                        break
            
            return {
                "success": True,
                "event_id": created_event['id'],
                "meet_link": meet_link,
                "event_link": created_event.get('htmlLink'),
                "start_time": meeting_datetime.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create Google Meet event: {e}")
            return {"success": False, "error": str(e)}
    
    def get_calendar_availability(self, days_ahead: int = 3) -> List[Dict[str, Any]]:
        """
        Get available time slots from Google Calendar
        """
        try:
            if not self.google_available:
                return self._get_default_availability_slots()
            
            # Get busy times for the next few days
            time_min = datetime.now().isoformat() + 'Z'
            time_max = (datetime.now() + timedelta(days=days_ahead)).isoformat() + 'Z'
            
            freebusy_query = {
                'timeMin': time_min,
                'timeMax': time_max,
                'items': [{'id': self.google_calendar_id}]
            }
            
            freebusy_result = self.calendar_service.freebusy().query(body=freebusy_query).execute()
            busy_times = freebusy_result['calendars'][self.google_calendar_id]['busy']
            
            # Generate available slots
            available_slots = []
            current_time = datetime.now().replace(minute=0, second=0, microsecond=0)
            
            for day in range(days_ahead):
                day_start = (current_time + timedelta(days=day+1)).replace(hour=9)  # 9 AM
                day_end = day_start.replace(hour=17)  # 5 PM
                
                # Check each hour slot
                slot_time = day_start
                while slot_time < day_end:
                    slot_end = slot_time + timedelta(minutes=self.default_meeting_duration)
                    
                    # Check if slot conflicts with busy times
                    is_available = True
                    for busy_period in busy_times:
                        busy_start = datetime.fromisoformat(busy_period['start'].replace('Z', '+00:00'))
                        busy_end = datetime.fromisoformat(busy_period['end'].replace('Z', '+00:00'))
                        
                        if (slot_time < busy_end and slot_end > busy_start):
                            is_available = False
                            break
                    
                    if is_available:
                        available_slots.append({
                            'datetime': slot_time,
                            'formatted': slot_time.strftime('%A, %B %d at %I:%M %p')
                        })
                    
                    slot_time += timedelta(hours=1)
            
            return available_slots[:6]  # Return first 6 available slots
            
        except Exception as e:
            self.logger.error(f"Failed to get calendar availability: {e}")
            return self._get_default_availability_slots()
    
    def _get_available_time_slots(self) -> str:
        """
        Get available time slots for the next few days
        """
        # Get availability from Google Calendar
        available_slots = self.get_calendar_availability()
        
        if not available_slots:
            return self._get_default_availability_text()
        
        # Format slots by day
        slots_by_day = {}
        for slot in available_slots:
            day_key = slot['datetime'].strftime('%A, %B %d')
            time_str = slot['datetime'].strftime('%I:%M %p')
            
            if day_key not in slots_by_day:
                slots_by_day[day_key] = []
            slots_by_day[day_key].append(time_str)
        
        # Format output
        formatted_slots = []
        for day, times in slots_by_day.items():
            time_list = '\n'.join([f"• {time}" for time in times])
            formatted_slots.append(f"📅 {day}:\n{time_list}")
        
        return '\n\n'.join(formatted_slots)
    
    def _get_default_availability_slots(self) -> List[Dict[str, Any]]:
        """
        Get default availability slots when Google Calendar is not available
        """
        slots = []
        today = datetime.now()
        
        for day_offset in range(1, 4):  # Next 3 days
            day = today + timedelta(days=day_offset)
            
            if day.weekday() < 5:  # Weekday
                times = [10, 14, 16]  # 10 AM, 2 PM, 4 PM
            else:  # Weekend
                times = [11, 14]  # 11 AM, 2 PM
            
            for hour in times:
                slot_time = day.replace(hour=hour, minute=0, second=0, microsecond=0)
                slots.append({
                    'datetime': slot_time,
                    'formatted': slot_time.strftime('%A, %B %d at %I:%M %p')
                })
        
        return slots
    
    def _get_default_availability_text(self) -> str:
        """
        Get default availability text when Google Calendar is not available
        """
        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        day_after = today + timedelta(days=2)
        
        return f"""📅 {tomorrow.strftime('%A, %B %d')}:
• 10:00 AM
• 2:00 PM
• 4:00 PM

📅 {day_after.strftime('%A, %B %d')}:
• 10:00 AM
• 1:00 PM
• 3:00 PM"""
    
    def _fetch_calendly_availability(self) -> str:
        """
        Fetch real availability from Calendly API
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.calendly_token}",
                "Content-Type": "application/json"
            }
            
            # Get availability for next 3 days
            start_time = datetime.now().isoformat()
            end_time = (datetime.now() + timedelta(days=3)).isoformat()
            
            url = f"https://api.calendly.com/user_availability_schedules"
            params = {
                "user": self.calendly_user_uri,
                "start_time": start_time,
                "end_time": end_time
            }
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return self._format_availability_response(data)
            else:
                self.logger.warning(f"Calendly API error: {response.status_code}")
                return self._get_default_availability()
                
        except Exception as e:
            self.logger.error(f"Error fetching Calendly availability: {e}")
            return self._get_default_availability()
    
    def _format_availability_response(self, calendly_data: Dict[str, Any]) -> str:
        """
        Format Calendly availability data into readable text
        """
        # Parse Calendly response and format into readable slots
        # This is a simplified version - real implementation would parse the actual API response
        return self._get_default_availability()
    
    def _get_default_availability(self) -> str:
        """
        Get default availability when Calendly API is not available
        """
        today = datetime.now()
        slots = []
        
        for i in range(1, 4):  # Next 3 days
            date = today + timedelta(days=i)
            day_name = date.strftime('%A, %B %d')
            
            if date.weekday() < 5:  # Weekday
                slots.append(f"📅 {day_name}:\n• 10:00 AM - 10:15 AM\n• 2:00 PM - 2:15 PM\n• 4:00 PM - 4:15 PM")
            else:  # Weekend
                slots.append(f"📅 {day_name}:\n• 11:00 AM - 11:15 AM\n• 2:00 PM - 2:15 PM")
        
        return "\n\n".join(slots)
    
    def create_meeting_reminder(self, state: RealEstateAgentState, meeting_time: datetime) -> Dict[str, Any]:
        """
        Create meeting reminder for scheduled appointment
        """
        lead_name = state["lead_name"]
        property_address = state["property_address"]
        
        reminder_message = f"""Hi {lead_name}! 

Just a friendly reminder about our call tomorrow at {meeting_time.strftime('%I:%M %p')} to discuss your property at {property_address}.

I'm looking forward to learning more about your situation and providing you with a cash offer range.

If you need to reschedule, just let me know!

Talk soon,
Derek"""
        
        return {
            "message": reminder_message,
            "send_time": meeting_time - timedelta(hours=24),  # 24 hours before
            "type": "reminder"
        }
    
    def handle_no_show(self, state: RealEstateAgentState) -> Dict[str, Any]:
        """
        Handle no-show follow-up sequence
        """
        lead_name = state["lead_name"]
        no_show_count = state.get("no_show_count", 0) + 1
        
        # Update no-show count
        state["no_show_count"] = no_show_count
        
        if no_show_count == 1:
            # First no-show - friendly follow-up
            message = f"""Hi {lead_name},

I noticed we missed each other for our scheduled call today. No worries at all - things come up!

Would you like to reschedule? I'm still very interested in discussing your property and providing you with a cash offer.

Just let me know what works better for you!"""
            
        elif no_show_count == 2:
            # Second no-show - more direct
            message = f"""Hi {lead_name},

We've missed each other a couple times now. I understand you're busy!

If you're still interested in exploring a cash offer for your property, just reply with a good time to call.

If now isn't the right time, no problem at all - just let me know.

Thanks!"""
            
        else:
            # Third no-show - final follow-up
            message = f"""Hi {lead_name},

I don't want to keep bothering you, but I wanted to reach out one more time about your property.

If you'd still like to explore a cash offer, I'm here to help. Otherwise, I'll assume now isn't the right time.

Feel free to reach out anytime in the future if your situation changes.

Best regards,
Derek"""
        
        return {
            "next_agent": "communication_router",
            "action": "send_message",
            "message": message,
            "state_updates": {
                "no_show_count": no_show_count,
                "next_action": "send_message"
            }
        }
    
    def handle_time_selection(self, state: RealEstateAgentState, user_message: str) -> Dict[str, Any]:
        """
        Handle when user selects a meeting time and create Google Meet event
        """
        try:
            # Parse the user's time selection
            selected_time = self._parse_time_selection(user_message)
            
            if selected_time:
                # Create Google Meet event
                event_result = self.create_google_meet_event(state, selected_time)
                
                if event_result["success"]:
                    lead_name = state["lead_name"]
                    formatted_time = selected_time.strftime('%A, %B %d at %I:%M %p')
                    meet_link = event_result["meet_link"]
                    
                    confirmation_message = f"""Perfect, {lead_name}! I've scheduled our 15-minute consultation for {formatted_time}.

Here's your Google Meet link:
{meet_link}

I'll also send you a calendar invitation with all the details.

Looking forward to discussing your property and providing you with a cash offer range!

If you need to reschedule, just let me know."""
                    
                    # Update state with booking details
                    state["booking_details"] = {
                        "scheduled_time": selected_time.isoformat(),
                        "meet_link": meet_link,
                        "event_id": event_result["event_id"],
                        "status": "scheduled"
                    }
                    
                    advance_conversation_stage(state, "scheduled")
                    
                    return {
                        "next_agent": "communication_router",
                        "action": "send_message",
                        "message": confirmation_message,
                        "state_updates": {
                            "conversation_stage": "scheduled",
                            "booking_details": state["booking_details"],
                            "next_action": "send_message"
                        }
                    }
                else:
                    # Failed to create event
                    error_message = f"I apologize, but I'm having trouble scheduling that time. Let me suggest some alternative times that I know are available. What works better for you?"
                    
                    return {
                        "next_agent": "communication_router",
                        "action": "send_message",
                        "message": error_message,
                        "state_updates": {"next_action": "send_message"}
                    }
            else:
                # Couldn't parse time selection
                clarification_message = f"I want to make sure I get the right time for you. Could you let me know which specific day and time works best? For example: 'Tuesday at 2 PM' or 'Wednesday at 10 AM'?"
                
                return {
                    "next_agent": "communication_router",
                    "action": "send_message",
                    "message": clarification_message,
                    "state_updates": {"next_action": "send_message"}
                }
                
        except Exception as e:
            self.logger.error(f"Error handling time selection: {e}")
            return self._clarify_booking_preference(state, user_message)
    
    def _parse_time_selection(self, user_message: str) -> Optional[datetime]:
        """
        Parse user's time selection from natural language
        """
        import re
        
        try:
            # Simple parsing for common time formats
            message_lower = user_message.lower()
            
            # Look for day and time patterns
            day_patterns = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 
                'friday': 4, 'saturday': 5, 'sunday': 6,
                'tomorrow': 1, 'today': 0
            }
            
            # Find day
            target_day = None
            for day_name, day_offset in day_patterns.items():
                if day_name in message_lower:
                    if day_name in ['tomorrow', 'today']:
                        target_day = datetime.now() + timedelta(days=day_offset)
                    else:
                        # Find next occurrence of this weekday
                        today = datetime.now()
                        days_ahead = (day_offset - today.weekday()) % 7
                        if days_ahead == 0:
                            days_ahead = 7  # Next week
                        target_day = today + timedelta(days=days_ahead)
                    break
            
            # Find time
            time_patterns = [
                r'(\d{1,2}):?(\d{0,2})\s*(am|pm)',
                r'(\d{1,2})\s*(am|pm)',
            ]
            
            target_time = None
            for pattern in time_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    hour = int(match.group(1))
                    minute = int(match.group(2)) if match.group(2) else 0
                    
                    if len(match.groups()) >= 3 and match.group(3):
                        if match.group(3) == 'pm' and hour != 12:
                            hour += 12
                        elif match.group(3) == 'am' and hour == 12:
                            hour = 0
                    
                    target_time = (hour, minute)
                    break
            
            # Combine day and time
            if target_day and target_time:
                return target_day.replace(hour=target_time[0], minute=target_time[1], second=0, microsecond=0)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error parsing time selection: {e}")
            return None
    
    def get_system_prompt(self, state: RealEstateAgentState) -> str:
        """
        System prompt for booking agent
        """
        return f"""
        You are the Booking Agent for a real estate investment company.
        
        Lead: {state['lead_name']}
        Property: {state['property_address']}
        Property Type: {state['property_type']}
        Stage: {state['conversation_stage']}
        
        Your responsibilities:
        - Schedule 15-minute consultation calls
        - Create Google Calendar events with Google Meet links
        - Handle scheduling preferences and time selection
        - Manage no-shows and reschedules
        - Send meeting reminders and confirmations
        
        Meeting Types:
        - Fix & Flip: Property evaluation and cash offer discussion
        - Vacant Land: Land consultation and offer range
        - Rental: Rental property discussion and lease options
        
        Communication Style:
        - Helpful and accommodating
        - Flexible with scheduling
        - Professional but friendly
        - Emphasize convenience and no-obligation
        - Provide clear time options
        
        Key Messages:
        - "15-minute consultation"
        - "Completely no-obligation"
        - "Google Meet link"
        - "Calendar invitation"
        - "Flexible scheduling options"
        - "Looking forward to helping"
        
        Process:
        1. Show available time slots
        2. Parse user's time selection
        3. Create Google Calendar event
        4. Send Google Meet link
        5. Confirm appointment details
        """


def booking_agent_node(state: RealEstateAgentState) -> Dict[str, Any]:
    """
    Node function for booking agent
    """
    agent = BookingAgent()
    
    # Get the most recent message if available
    user_message = None
    if state["messages"] and len(state["messages"]) > 0:
        last_message = state["messages"][-1]
        if hasattr(last_message, 'content'):
            user_message = last_message.content
    
    return agent.process_message(state, user_message)


def route_booking_result(state: RealEstateAgentState) -> str:
    """
    Routing function for booking agent results
    """
    next_action = state.get("next_action")
    conversation_stage = state.get("conversation_stage")
    
    if next_action == "send_message":
        return "communication_router"
    elif conversation_stage == "not_interested":
        return "END"
    else:
        return "supervisor"
