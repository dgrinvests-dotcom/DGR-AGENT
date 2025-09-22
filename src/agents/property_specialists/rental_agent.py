"""
Long-Term Rental Property Specialist Agent
Handles qualification and conversation flow for rental properties
Based on project dialogue flows and requirements
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from typing import Dict, Any, Optional, List
from datetime import datetime

from agents.base_agent import BaseRealEstateAgent
from schemas.agent_state import (
    RealEstateAgentState, 
    update_state_timestamp,
    update_qualification_data,
    advance_conversation_stage
)


class RentalPropertySpecialistAgent(BaseRealEstateAgent):
    """
    Long-Term Rental Property Specialist Agent
    
    Specializes in:
    - Rental property qualification and evaluation
    - Tenant situation assessment
    - Lease terms and rental income analysis
    - Property management challenges
    - Landlord motivation and timeline
    - Working with existing leases
    """
    
    def __init__(self):
        super().__init__("rental_agent")
        
        # Rental property specific qualification flow
        self.qualification_sequence = [
            "rental_status",
            "tenant_situation", 
            "rental_income",
            "property_condition",
            "landlord_challenges",
            "timeline"
        ]
    
    def process_message(self, state: RealEstateAgentState, user_message: str = None) -> Dict[str, Any]:
        """
        Process incoming message for rental property
        """
        try:
            self.log_agent_action(state, "processing_rental_message")
            
            # Update agent tracking
            state["current_agent"] = "rental_agent"
            if "rental_agent" not in state["agent_history"]:
                state["agent_history"].append("rental_agent")
            
            # Determine conversation stage and next action
            if user_message:
                return self._handle_user_response(state, user_message)
            else:
                return self._initiate_qualification(state)
                
        except Exception as e:
            self.handle_error(state, e)
            return {"next_agent": "supervisor", "action": "error"}
    
    def _handle_user_response(self, state: RealEstateAgentState, user_message: str) -> Dict[str, Any]:
        """
        Handle user response and continue qualification flow
        """
        # Analyze user message
        analysis = self.analyze_user_message(user_message, {
            "property_type": "long_term_rental",
            "qualification_data": state["qualification_data"]
        })
        
        intent = analysis.get("intent", "unknown")
        
        # Handle different intents
        if intent == "not_interested":
            return self._handle_not_interested(state)
        elif intent == "ready_to_book":
            return self._route_to_booking(state)
        elif intent == "question" or intent == "objection":
            return self._handle_objection(state, user_message, analysis)
        else:
            # Continue qualification flow
            return self._continue_qualification(state, user_message, analysis)
    
    def _initiate_qualification(self, state: RealEstateAgentState) -> Dict[str, Any]:
        """
        Start the rental property qualification process
        """
        # Generate initial qualification message
        message = self._generate_qualification_message(state)
        
        # Update conversation stage
        advance_conversation_stage(state, "qualifying")
        
        return {
            "next_agent": "communication_router",
            "action": "send_message", 
            "message": message,
            "state_updates": {
                "conversation_stage": "qualifying",
                "next_action": "send_message"
            }
        }
    
    def _continue_qualification(self, state: RealEstateAgentState, user_message: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Continue the qualification process based on current stage
        """
        # Extract information from user message
        extracted_info = self._extract_qualification_info(user_message, analysis)
        
        # Update qualification data
        for field, value in extracted_info.items():
            update_qualification_data(state, field, value)
        
        # Determine next qualification step
        next_step = self._get_next_qualification_step(state)
        
        if next_step:
            # Continue qualification
            message = self._generate_qualification_message(state, next_step)
            return {
                "next_agent": "communication_router",
                "action": "send_message",
                "message": message,
                "state_updates": {"next_action": "send_message"}
            }
        else:
            # Qualification complete, move to booking
            return self._complete_qualification(state)
    
    def _extract_qualification_info(self, user_message: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract qualification information from user message
        """
        message_lower = user_message.lower()
        extracted = {}
        
        # Rental status
        if any(word in message_lower for word in ["currently rented", "have tenants", "occupied"]):
            extracted["rental_status"] = "rented"
        elif any(word in message_lower for word in ["vacant", "empty", "no tenants"]):
            extracted["rental_status"] = "vacant"
        elif any(word in message_lower for word in ["between tenants", "just moved out"]):
            extracted["rental_status"] = "transitioning"
        
        # Tenant situation
        if any(word in message_lower for word in ["good tenants", "pay on time", "no problems"]):
            extracted["tenant_situation"] = "good"
        elif any(word in message_lower for word in ["problem tenants", "late payments", "eviction"]):
            extracted["tenant_situation"] = "problematic"
        elif any(word in message_lower for word in ["section 8", "housing voucher"]):
            extracted["tenant_situation"] = "section_8"
        
        # Rental income
        import re
        income_patterns = [
            r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:per\s*month|monthly|/month)',
            r'(\d+(?:,\d{3})*)\s*(?:per\s*month|monthly|/month)',
            r'rent\s+(?:is\s+)?\$?(\d+(?:,\d{3})*)'
        ]
        
        for pattern in income_patterns:
            match = re.search(pattern, message_lower)
            if match:
                income_str = match.group(1).replace(',', '')
                extracted["rental_income"] = float(income_str)
                break
        
        # Property condition
        if any(word in message_lower for word in ["good condition", "well maintained", "updated"]):
            extracted["property_condition"] = "good"
        elif any(word in message_lower for word in ["needs work", "outdated", "repairs needed"]):
            extracted["property_condition"] = "needs_work"
        elif any(word in message_lower for word in ["poor condition", "major repairs", "falling apart"]):
            extracted["property_condition"] = "poor"
        
        # Landlord challenges
        if any(word in message_lower for word in ["tired of", "headache", "stress", "don't want to deal"]):
            extracted["landlord_challenges"] = "management_fatigue"
        elif any(word in message_lower for word in ["repairs", "maintenance", "always breaking"]):
            extracted["landlord_challenges"] = "maintenance_issues"
        elif any(word in message_lower for word in ["vacancy", "hard to rent", "can't find tenants"]):
            extracted["landlord_challenges"] = "vacancy_issues"
        elif any(word in message_lower for word in ["distance", "out of state", "far away"]):
            extracted["landlord_challenges"] = "distance_management"
        
        # Timeline
        if any(word in message_lower for word in ["asap", "immediately", "right away"]):
            extracted["timeline"] = "immediate"
        elif any(word in message_lower for word in ["end of lease", "when lease expires"]):
            extracted["timeline"] = "lease_expiration"
        elif any(word in message_lower for word in ["few months", "this year"]):
            extracted["timeline"] = "3-6_months"
        elif any(word in message_lower for word in ["flexible", "no rush"]):
            extracted["timeline"] = "flexible"
        
        return extracted
    
    def _get_next_qualification_step(self, state: RealEstateAgentState) -> Optional[str]:
        """
        Determine the next step in qualification process
        """
        qualification_data = state["qualification_data"]
        
        for step in self.qualification_sequence:
            if not qualification_data.get(step):
                return step
        
        return None  # All steps completed
    
    def _generate_qualification_message(self, state: RealEstateAgentState, step: str = None) -> str:
        """
        Generate qualification message based on current step
        """
        lead_name = state["lead_name"]
        property_address = state["property_address"]
        
        if not step:
            step = self._get_next_qualification_step(state) or "rental_status"
        
        messages = {
            "rental_status": f"Great! Is the property at {property_address} currently rented or vacant?",
            
            "tenant_situation": f"And how are the tenants? Are they good tenants who pay on time, or have there been any challenges?",
            
            "rental_income": f"What's the current monthly rent, if you don't mind me asking?",
            
            "property_condition": f"How's the condition of the property? Has it been well-maintained or are there repairs needed?",
            
            "landlord_challenges": f"What's been the biggest challenge with managing this rental? Is it the tenants, maintenance, distance, or something else?",
            
            "timeline": f"What's your ideal timeline for selling? Are you looking to sell right away, or would you prefer to wait until the lease expires?"
        }
        
        return messages.get(step, f"Thanks for that information, {lead_name}! Let me ask about the rental situation...")
    
    def _complete_qualification(self, state: RealEstateAgentState) -> Dict[str, Any]:
        """
        Complete qualification and move to booking
        """
        lead_name = state["lead_name"]
        qualification_data = state["qualification_data"]
        
        # Generate completion message based on rental situation
        if qualification_data.get("rental_status") == "rented":
            message = f"Thanks for all that info, {lead_name}! We specialize in rental properties and can definitely work around existing leases - we can either honor the current lease or work with you on other options. The next step is a quick 15-minute call where I can review everything and give you a cash offer range. What works better for you— afternoon or evening this week?"
        elif qualification_data.get("landlord_challenges") == "management_fatigue":
            message = f"I totally understand, {lead_name}! Property management can be exhausting. We buy rental properties specifically to take that headache off landlords' hands. Let's do a quick 15-minute call where I can show you how we can make this simple and stress-free. What's easier— afternoon or evening this week?"
        else:
            message = f"Perfect, {lead_name}! Based on what you've shared, this sounds like it could be a great fit. We specialize in rental properties and understand the unique challenges landlords face. The next step is a quick 15-minute call where I can review your property details and give you a cash range. What's easier for you— afternoon or evening this week?"
        
        # Update state
        advance_conversation_stage(state, "interested")
        
        return {
            "next_agent": "communication_router",
            "action": "send_message",
            "message": message,
            "state_updates": {
                "conversation_stage": "interested",
                "next_action": "send_message"
            }
        }
    
    def _handle_objection(self, state: RealEstateAgentState, user_message: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle objections and concerns specific to rental properties
        """
        lead_name = state["lead_name"]
        message_lower = user_message.lower()
        
        # Common rental property objection responses
        if any(word in message_lower for word in ["cash flow", "income", "making money"]):
            response = f"I understand, {lead_name}. Positive cash flow is great when it works! Sometimes though, landlords find that the time, stress, and unexpected costs add up. We can show you what a lump sum cash offer looks like versus the ongoing management - might be worth comparing the options."
            
        elif any(word in message_lower for word in ["good tenants", "no problems", "paying well"]):
            response = f"That's fantastic, {lead_name}! Good tenants are worth their weight in gold. Even with great tenants though, many landlords eventually want to simplify their lives. We can work around existing leases, so you have options either way."
            
        elif any(word in message_lower for word in ["lease", "contract", "can't sell"]):
            response = f"Great question, {lead_name}! We actually specialize in properties with existing leases. We can either honor the current lease and work with the tenants, or we can discuss other options. It's definitely not a barrier for us."
            
        elif any(word in message_lower for word in ["market value", "worth more", "appreciation"]):
            response = f"You're absolutely right to think about that, {lead_name}. Real estate can appreciate over time. The question is usually whether the ongoing management, maintenance costs, and time investment are worth it versus having cash in hand now. Worth exploring both options, don't you think?"
            
        elif any(word in message_lower for word in ["property manager", "management company"]):
            response = f"That's definitely an option, {lead_name}! Property managers can help, though they typically take 8-12% of rent plus markup on repairs. Some landlords find they still get calls and stress even with managers. But it's worth comparing - management company versus selling for cash."
            
        else:
            response = f"I hear you, {lead_name}. Every rental situation is unique, and I want to make sure you have all the information to make the best decision. How about a quick 15-minute call where we can discuss your specific situation and concerns?"
        
        # Track objection
        if user_message not in state["objections_handled"]:
            state["objections_handled"].append(user_message)
        
        return {
            "next_agent": "communication_router",
            "action": "send_message",
            "message": response,
            "state_updates": {"next_action": "send_message"}
        }
    
    def _handle_not_interested(self, state: RealEstateAgentState) -> Dict[str, Any]:
        """
        Handle not interested response
        """
        lead_name = state["lead_name"]
        
        message = f"No problem at all, {lead_name}! I appreciate you letting me know. If your situation with the rental ever changes, feel free to reach out. Have a great day!"
        
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
    
    def _route_to_booking(self, state: RealEstateAgentState) -> Dict[str, Any]:
        """
        Route to booking agent
        """
        advance_conversation_stage(state, "booking")
        
        return {
            "next_agent": "booking_agent",
            "action": "schedule_appointment",
            "state_updates": {
                "conversation_stage": "booking",
                "next_action": "schedule_appointment"
            }
        }
    
    def get_system_prompt(self, state: RealEstateAgentState) -> str:
        """
        System prompt for rental property specialist
        """
        return f"""
        You are a Long-Term Rental Property Specialist for a real estate investment company.
        
        Lead: {state['lead_name']}
        Property: {state['property_address']}
        Stage: {state['conversation_stage']}
        
        Your expertise:
        - Rental property acquisition and management
        - Working with existing leases and tenants
        - Understanding landlord challenges and motivations
        - Quick cash offers for rental properties
        
        Qualification Focus:
        1. Current rental status (rented/vacant/transitioning)
        2. Tenant situation and quality
        3. Monthly rental income
        4. Property condition and maintenance needs
        5. Landlord challenges and pain points
        6. Timeline and motivation for selling
        
        Communication Style:
        - Empathetic to landlord challenges
        - Understanding of rental property complexities
        - Emphasize simplicity and stress relief
        - Address lease and tenant concerns
        - Focus on eliminating management headaches
        
        Key Messages:
        - "We specialize in rental properties"
        - "Can work around existing leases"
        - "Eliminate management headaches"
        - "Quick cash offers"
        - "Handle tenant communications"
        
        Common Landlord Pain Points:
        - Management fatigue and stress
        - Maintenance and repair costs
        - Problem tenants and vacancies
        - Distance management challenges
        - Time investment vs. returns
        """


def rental_agent_node(state: RealEstateAgentState) -> Dict[str, Any]:
    """
    Node function for rental property specialist agent
    """
    agent = RentalPropertySpecialistAgent()
    
    # Get the most recent message if available
    user_message = None
    if state["messages"] and len(state["messages"]) > 0:
        last_message = state["messages"][-1]
        if hasattr(last_message, 'content'):
            user_message = last_message.content
    
    return agent.process_message(state, user_message)


def route_rental_result(state: RealEstateAgentState) -> str:
    """
    Routing function for rental property agent results
    """
    next_action = state.get("next_action")
    
    if next_action == "send_message":
        return "communication_router"
    elif next_action == "schedule_appointment":
        return "booking_agent"
    else:
        return "supervisor"
