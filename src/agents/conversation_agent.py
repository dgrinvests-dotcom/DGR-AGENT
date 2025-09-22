import openai
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from ..models import Lead, LeadStatus, PropertyType, ConversationMessage, ContactMethod
from ..utils.database import DatabaseManager
from ..compliance.compliance_checker import ComplianceChecker
from ..integrations.google_meet_integration import GoogleMeetIntegration

class ConversationAgent:
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.db = DatabaseManager()
        self.compliance = ComplianceChecker()
        self.google_meet = GoogleMeetIntegration()
        
        # Load conversation templates from config
        from ..config.dialogue_templates import DIALOGUE_TEMPLATES, get_template, get_follow_up_sequence
        self.templates = DIALOGUE_TEMPLATES
    
    async def process_message(self, phone_number: str, message_body: str) -> str:
        """Process incoming message and generate AI response"""
        
        # Get or create lead
        lead = await self.db.get_lead_by_phone(phone_number)
        if not lead:
            return "I'm sorry, I don't have your information in our system."
        
        # Check compliance
        if not self.compliance.can_contact(phone_number):
            return None
        
        # Handle opt-out requests
        if self._is_opt_out_request(message_body):
            await self._handle_opt_out(lead)
            return "You have been removed from our contact list. Thank you."
        
        # Add message to conversation history
        conversation_msg = ConversationMessage(
            direction="inbound",
            method=ContactMethod.SMS,
            content=message_body
        )
        
        # Generate AI response based on property type and conversation state
        ai_response = await self._generate_response(lead, message_body)
        
        # Update conversation history
        conversation_msg.ai_response = ai_response
        lead.conversation_history.append(conversation_msg.dict())
        
        # Update lead status based on response
        await self._update_lead_status(lead, message_body, ai_response)
        
        # Save updated lead
        await self.db.update_lead(lead)
        
        return ai_response
    
    async def _generate_response(self, lead: Lead, message: str) -> str:
        """Generate AI response using OpenAI with property-specific context"""
        
        # Get conversation context
        context = self._build_conversation_context(lead)
        
        # Get property-specific system prompt
        system_prompt = self._get_system_prompt(lead.property_type)
        
        # Build conversation history for OpenAI
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Lead context: {context}"},
            {"role": "user", "content": f"Lead message: {message}"}
        ]
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                max_tokens=200,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Check if response indicates interest and should trigger meeting booking
            if self._indicates_interest(ai_response, message):
                # Create a Google Meet for this lead
                meeting_details = await self.google_meet.create_meeting(
                    summary=f"Property Discussion - {lead.property_address}",
                    description=f"Call with {lead.first_name} {lead.last_name} about their property at {lead.property_address}",
                    duration_minutes=30
                )
                
                if meeting_details and meeting_details.get('meet_link'):
                    meet_link = meeting_details['meet_link']
                    ai_response += f"\n\nGreat! I've created a meeting for us: {meet_link}"
                else:
                    ai_response += f"\n\nGreat! I'd love to schedule a call with you. Please let me know what time works best."
            
            return ai_response
            
        except Exception as e:
            print(f"Error generating AI response: {e}")
            return "I apologize, but I'm having technical difficulties. Can you please try again?"
    
    def _get_system_prompt(self, property_type: PropertyType) -> str:
        """Get property-specific system prompt for AI"""
        
        base_prompt = """You are a professional real estate assistant helping to qualify wholesale leads. 
        Keep responses short, natural, and conversational. Always push toward scheduling a call when the seller shows interest.
        Be helpful but direct. Ask one question at a time."""
        
        if property_type == PropertyType.FIX_FLIP:
            return base_prompt + """
            
            Focus on:
            - Property condition and needed repairs
            - Timeline for selling
            - Asking price expectations
            - Access to the property for inspection
            
            Key qualifying questions:
            - What condition is the property in?
            - What repairs does it need?
            - How quickly are you looking to sell?
            - What price were you hoping to get?
            """
            
        elif property_type == PropertyType.RENTAL:
            return base_prompt + """
            
            Focus on:
            - Current rental status (occupied/vacant)
            - Rental income potential
            - Property management challenges
            - Reason for selling
            
            Key qualifying questions:
            - Is the property currently rented?
            - What's the monthly rental income?
            - Are you dealing with any tenant issues?
            - Why are you considering selling?
            """
            
        elif property_type == PropertyType.VACANT_LAND:
            return base_prompt + """
            
            Focus on:
            - Land size and zoning
            - Development potential
            - Utilities availability
            - Location and access
            
            Key qualifying questions:
            - How many acres is the land?
            - What's the zoning designation?
            - Are utilities available to the property?
            - What were you planning to do with it?
            """
        
        return base_prompt
    
    def _build_conversation_context(self, lead: Lead) -> str:
        """Build context string for AI about the lead"""
        context = f"""
        Lead: {lead.first_name or 'Unknown'} {lead.last_name or ''}
        Property: {lead.property_address}
        Property Type: {lead.property_type}
        Status: {lead.status}
        """
        
        if lead.qualification_data:
            context += f"\nQualification Data: {json.dumps(lead.qualification_data, indent=2)}"
        
        # Add recent conversation history
        if lead.conversation_history:
            recent_messages = lead.conversation_history[-3:]  # Last 3 messages
            context += "\nRecent Conversation:\n"
            for msg in recent_messages:
                direction = "Lead" if msg["direction"] == "inbound" else "Agent"
                context += f"{direction}: {msg['content']}\n"
        
        return context
    
    def _indicates_interest(self, ai_response: str, user_message: str) -> bool:
        """Check if the conversation indicates interest in scheduling a call"""
        interest_keywords = [
            "interested", "yes", "sure", "okay", "sounds good", 
            "tell me more", "what's your offer", "how much"
        ]
        
        return any(keyword in user_message.lower() for keyword in interest_keywords)
    
    def _is_opt_out_request(self, message: str) -> bool:
        """Check if message is an opt-out request"""
        opt_out_keywords = ["stop", "unsubscribe", "remove", "opt out", "don't contact"]
        return any(keyword in message.lower() for keyword in opt_out_keywords)
    
    async def _handle_opt_out(self, lead: Lead):
        """Handle opt-out request"""
        lead.opted_out = True
        lead.status = LeadStatus.DNC
        await self.db.update_lead(lead)
    
    async def _update_lead_status(self, lead: Lead, message: str, ai_response: str):
        """Update lead status based on conversation"""
        if self._indicates_interest(ai_response, message):
            if lead.status == LeadStatus.NEW or lead.status == LeadStatus.CONTACTED:
                lead.status = LeadStatus.INTERESTED
        
        # Update last contact date
        lead.last_contact_date = datetime.utcnow()
    
    def _load_conversation_templates(self) -> Dict[str, Any]:
        """Load conversation templates from config"""
        # This would load from your Google Docs content
        # For now, return empty dict - we'll populate this with your specific dialogues
        return {}
    
    async def send_initial_message(self, lead: Lead) -> str:
        """Send initial outreach message based on property type"""
        template = self.templates.get(lead.property_type, {})
        initial_message = template.get("initial_message", "Hi! I'm interested in your property. Are you considering selling?")
        
        # Personalize the message
        if lead.first_name:
            initial_message = f"Hi {lead.first_name}! " + initial_message
        
        return initial_message
