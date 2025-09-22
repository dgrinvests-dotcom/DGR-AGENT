"""
Vacant Land Property Specialist Agent
Handles qualification and conversation flow for vacant land properties
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


class VacantLandSpecialistAgent(BaseRealEstateAgent):
    """
    Vacant Land Property Specialist Agent
    
    Specializes in:
    - Vacant land qualification and evaluation
    - Acreage and lot size assessment
    - Road access verification
    - Utilities availability check
    - Lien and title status
    - Quick 15-minute consultation scheduling
    """
    
    def __init__(self):
        super().__init__("vacant_land_agent")
        
        # Vacant land specific qualification flow
        self.qualification_sequence = [
            "acreage",
            "road_access",
            "utilities",
            "liens_taxes",
            "price_expectations"
        ]
    
    def process_message(self, state: RealEstateAgentState, user_message: str = None) -> Dict[str, Any]:
        """
        Process incoming message for vacant land property
        """
        try:
            self.log_agent_action(state, "processing_vacant_land_message")
            
            # Update agent tracking
            state["current_agent"] = "vacant_land_agent"
            if "vacant_land_agent" not in state["agent_history"]:
                state["agent_history"].append("vacant_land_agent")
            
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
            "property_type": "vacant_land",
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
        Start the vacant land qualification process
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
        
        # Acreage/lot size
        import re
        
        # Look for acreage patterns
        acreage_patterns = [
            r'(\d+(?:\.\d+)?)\s*acres?',
            r'(\d+(?:\.\d+)?)\s*ac\b',
            r'about\s+(\d+(?:\.\d+)?)\s*acres?'
        ]
        
        for pattern in acreage_patterns:
            match = re.search(pattern, message_lower)
            if match:
                extracted["acreage"] = float(match.group(1))
                break
        
        # Look for lot size patterns
        lot_patterns = [
            r'(\d+(?:\.\d+)?)\s*sq\s*ft',
            r'(\d+(?:\.\d+)?)\s*square\s*feet',
            r'lot\s+size\s+(\d+(?:\.\d+)?)'
        ]
        
        for pattern in lot_patterns:
            match = re.search(pattern, message_lower)
            if match:
                extracted["lot_size_sqft"] = float(match.group(1))
                break
        
        # Road access
        if any(word in message_lower for word in ["road access", "paved road", "county road", "accessible"]):
            extracted["road_access"] = "yes"
        elif any(word in message_lower for word in ["no road", "landlocked", "no access"]):
            extracted["road_access"] = "no"
        elif any(word in message_lower for word in ["dirt road", "gravel", "unpaved"]):
            extracted["road_access"] = "dirt_road"
        
        # Utilities
        if any(word in message_lower for word in ["utilities available", "power nearby", "water hookup"]):
            extracted["utilities"] = "available"
        elif any(word in message_lower for word in ["no utilities", "off grid", "no power"]):
            extracted["utilities"] = "none"
        elif any(word in message_lower for word in ["some utilities", "partial", "water only"]):
            extracted["utilities"] = "partial"
        
        # Liens and taxes
        if any(word in message_lower for word in ["no liens", "clear title", "taxes current"]):
            extracted["liens_taxes"] = "clear"
        elif any(word in message_lower for word in ["back taxes", "tax lien", "behind on taxes"]):
            extracted["liens_taxes"] = "tax_issues"
        elif any(word in message_lower for word in ["lien", "mortgage", "debt"]):
            extracted["liens_taxes"] = "liens_present"
        
        # Price expectations
        price_patterns = [
            r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'(\d+(?:,\d{3})*)\s*dollars?',
            r'around\s+\$?(\d+(?:,\d{3})*)'
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, message_lower)
            if match:
                price_str = match.group(1).replace(',', '')
                extracted["price_expectations"] = float(price_str)
                break
        
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
        
        if not step:
            step = self._get_next_qualification_step(state) or "acreage"
        
        messages = {
            "acreage": f"Great! To put something together that makes sense, could I ask - do you know roughly how many acres or the lot size of your parcel?",
            
            "road_access": f"Perfect! Does it have road access, or is it landlocked? And if there is road access, is it paved or more of a dirt/gravel situation?",
            
            "utilities": f"Got it! Any idea if utilities like water, power, or septic/sewer are nearby or available to the property?",
            
            "liens_taxes": f"And just to make sure we can move quickly - are the taxes current and is there a clear title, or are there any liens or back taxes we should know about?",
            
            "price_expectations": f"Last question - do you have a ballpark of what you're hoping to get for the land? Just helps me see if we're in the same neighborhood."
        }
        
        return messages.get(step, f"Thanks for that information, {lead_name}! Let me ask about the property details...")
    
    def _complete_qualification(self, state: RealEstateAgentState) -> Dict[str, Any]:
        """
        Complete qualification and move to booking
        """
        lead_name = state["lead_name"]
        
        # Generate completion message based on qualification
        qualification_data = state["qualification_data"]
        
        # Customize message based on land characteristics
        if qualification_data.get("road_access") == "no":
            message = f"Thanks for all that info, {lead_name}! Even though it's landlocked, we still work with those situations. The next step is super simple: we'll do a quick 15-minute call where I can review your land details and give you a cash range. What's easier for you— afternoon or evening this week?"
        elif qualification_data.get("utilities") == "none":
            message = f"Perfect, {lead_name}! Off-grid land can actually be quite valuable. The next step is a quick 15-minute consultation where I can review everything and give you a cash offer range. Would afternoon or evening work better for you this week?"
        else:
            message = f"Excellent, {lead_name}! Based on what you've shared, this sounds like it could be a great fit. The next step is super simple: we'll do a quick 15-minute call where I can review your land details and give you a cash range. What's easier for you— afternoon or evening this week?"
        
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
        Handle objections and concerns specific to vacant land
        """
        lead_name = state["lead_name"]
        message_lower = user_message.lower()
        
        # Common vacant land objection responses
        if any(word in message_lower for word in ["price", "low offer", "worth more"]):
            response = f"I totally understand, {lead_name}. Land values can vary so much based on location, access, and development potential. That's exactly why I'd love to do a quick call - I can give you a much more accurate range once I understand all the details about your specific parcel."
            
        elif any(word in message_lower for word in ["develop", "build", "subdivision"]):
            response = f"That's a great point, {lead_name}! Development potential definitely affects value. We work with land in all stages - some for development, some for conservation, some for agricultural use. A quick call would help me understand your land's best use and give you options accordingly."
            
        elif any(word in message_lower for word in ["family land", "inherited", "sentimental"]):
            response = f"I completely understand, {lead_name}. Family land often has sentimental value that goes beyond dollars. There's no pressure here at all - sometimes it just helps to know what your options are, even if you're not ready to make a decision right now."
            
        elif any(word in message_lower for word in ["taxes", "expensive", "costs"]):
            response = f"You're absolutely right, {lead_name} - carrying costs on land can add up. That's actually one of the main reasons people reach out to us. We can often close quickly and take that ongoing expense off your hands. Worth a quick conversation to see if the numbers make sense?"
            
        else:
            response = f"I hear you, {lead_name}. Every piece of land is unique, and I want to make sure you have all the information to make the best decision for your situation. How about a quick 10-15 minute call where we can discuss your specific concerns?"
        
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
        
        message = f"No problem at all, {lead_name}! I appreciate you letting me know. If you ever want to explore your options in the future, feel free to reach out. Have a great day!"
        
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
        System prompt for vacant land specialist
        """
        return f"""
        You are a Vacant Land Property Specialist for a land investment company.
        
        Lead: {state['lead_name']}
        Property: {state['property_address']}
        Stage: {state['conversation_stage']}
        
        Your expertise:
        - Vacant land evaluation and acquisition
        - Quick cash offers for raw land
        - All types: residential lots, agricultural, recreational
        - Simple, hassle-free process
        
        Qualification Focus:
        1. Acreage/lot size assessment
        2. Road access verification (paved, dirt, landlocked)
        3. Utilities availability (water, power, septic)
        4. Liens and tax status
        5. Price expectations and motivation
        
        Communication Style:
        - Professional but approachable
        - Emphasize simplicity and speed
        - Quick 15-minute consultations
        - Handle concerns about land value
        - Focus on eliminating carrying costs
        
        Key Messages:
        - "We buy all types of vacant land"
        - "Quick 15-minute consultation"
        - "Simple, hassle-free process"
        - "Eliminate carrying costs and taxes"
        - "Cash offers for raw land"
        
        Special Considerations:
        - Land can be emotional (family property)
        - Carrying costs are often a motivator
        - Access and utilities greatly affect value
        - Development potential varies widely
        """


def vacant_land_agent_node(state: RealEstateAgentState) -> Dict[str, Any]:
    """
    Node function for vacant land specialist agent
    """
    agent = VacantLandSpecialistAgent()
    
    # Get the most recent message if available
    user_message = None
    if state["messages"] and len(state["messages"]) > 0:
        last_message = state["messages"][-1]
        if hasattr(last_message, 'content'):
            user_message = last_message.content
    
    return agent.process_message(state, user_message)


def route_vacant_land_result(state: RealEstateAgentState) -> str:
    """
    Routing function for vacant land agent results
    """
    next_action = state.get("next_action")
    
    if next_action == "send_message":
        return "communication_router"
    elif next_action == "schedule_appointment":
        return "booking_agent"
    else:
        return "supervisor"
