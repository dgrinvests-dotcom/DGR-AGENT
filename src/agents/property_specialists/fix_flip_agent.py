"""
Fix & Flip Property Specialist Agent
Handles qualification and conversation flow for fix & flip properties
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


class FixFlipSpecialistAgent(BaseRealEstateAgent):
    """
    Fix & Flip Property Specialist Agent
    
    Specializes in:
    - Fix & flip property qualification
    - Occupancy status assessment
    - Condition evaluation
    - Repair needs analysis
    - Timeline and motivation assessment
    - Smooth transition to booking calls
    """
    
    def __init__(self):
        super().__init__("fix_flip_agent")
        
        # Fix & Flip specific qualification flow
        self.qualification_sequence = [
            "occupancy_status",
            "condition", 
            "repairs_needed",
            "timeline",
            "motivation"
        ]
    
    def process_message(self, state: RealEstateAgentState, user_message: str = None) -> Dict[str, Any]:
        """
        Process incoming message for fix & flip property
        """
        try:
            self.log_agent_action(state, "processing_fix_flip_message")
            
            # Update agent tracking
            state["current_agent"] = "fix_flip_agent"
            if "fix_flip_agent" not in state["agent_history"]:
                state["agent_history"].append("fix_flip_agent")
            
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
            "property_type": "fix_flip",
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
        Start the fix & flip qualification process
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
        
        # Occupancy status
        if any(word in message_lower for word in ["vacant", "empty", "nobody living"]):
            extracted["occupancy_status"] = "vacant"
        elif any(word in message_lower for word in ["rented", "tenant", "occupied by tenant"]):
            extracted["occupancy_status"] = "rented"
        elif any(word in message_lower for word in ["live there", "i live", "owner occupied"]):
            extracted["occupancy_status"] = "owner_occupied"
        
        # Condition assessment
        if any(word in message_lower for word in ["good condition", "great shape", "well maintained"]):
            extracted["condition"] = "good"
        elif any(word in message_lower for word in ["needs work", "fixer upper", "rough shape"]):
            extracted["condition"] = "needs_work"
        elif any(word in message_lower for word in ["bad condition", "terrible", "falling apart"]):
            extracted["condition"] = "poor"
        
        # Repairs needed
        if any(word in message_lower for word in ["roof", "roofing", "leak"]):
            extracted["repairs_needed"] = "roof_issues"
        elif any(word in message_lower for word in ["plumbing", "pipes", "water"]):
            extracted["repairs_needed"] = "plumbing_issues"
        elif any(word in message_lower for word in ["electrical", "wiring", "electric"]):
            extracted["repairs_needed"] = "electrical_issues"
        elif any(word in message_lower for word in ["foundation", "structural", "sinking"]):
            extracted["repairs_needed"] = "structural_issues"
        
        # Timeline
        if any(word in message_lower for word in ["asap", "immediately", "right away", "urgent"]):
            extracted["timeline"] = "immediate"
        elif any(word in message_lower for word in ["few weeks", "month", "soon"]):
            extracted["timeline"] = "1-3_months"
        elif any(word in message_lower for word in ["few months", "later this year"]):
            extracted["timeline"] = "3-6_months"
        elif any(word in message_lower for word in ["no rush", "flexible", "whenever"]):
            extracted["timeline"] = "flexible"
        
        # Motivation
        if any(word in message_lower for word in ["divorce", "separated"]):
            extracted["motivation"] = "divorce"
        elif any(word in message_lower for word in ["inherited", "estate", "passed away"]):
            extracted["motivation"] = "inherited"
        elif any(word in message_lower for word in ["relocating", "moving", "job transfer"]):
            extracted["motivation"] = "relocation"
        elif any(word in message_lower for word in ["financial", "behind on payments", "foreclosure"]):
            extracted["motivation"] = "financial_distress"
        
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
            step = self._get_next_qualification_step(state) or "occupancy_status"
        
        messages = {
            "occupancy_status": f"Great! I just need a few quick details to see if it's a fit. Is the property at {property_address} currently vacant, rented, or owner-occupied?",
            
            "condition": f"And how's the condition of the property? Any recent repairs or major issues we should know about?",
            
            "repairs_needed": f"What would you say are the main things that need attention? (roof, plumbing, electrical, etc.)",
            
            "timeline": f"Perfect! What's your ideal timeline for selling? Are you looking to move quickly or do you have some flexibility?",
            
            "motivation": f"Just to help me understand your situation better - what's prompting you to consider selling? (No pressure, just helps me provide better options)"
        }
        
        return messages.get(step, f"Thanks for that information, {lead_name}! Let me ask you about the property condition...")
    
    def _complete_qualification(self, state: RealEstateAgentState) -> Dict[str, Any]:
        """
        Complete qualification and move to booking
        """
        lead_name = state["lead_name"]
        
        # Generate completion message
        message = f"Thanks for all that info, {lead_name}! Based on what you've shared, we may be able to make a fair cash offer. The next step is super simple: we'll do a quick 15-minute call where I can review your property details and give you a cash range. What's easier for you— afternoon or evening this week?"
        
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
        Handle objections and concerns
        """
        lead_name = state["lead_name"]
        message_lower = user_message.lower()
        
        # Common objection responses
        if any(word in message_lower for word in ["price", "low offer", "worth more"]):
            response = f"I completely understand, {lead_name}. We always aim to make fair offers based on current market conditions and the property's condition. The great thing about our process is there's no obligation - we can give you a range and you can decide if it makes sense for your situation."
            
        elif any(word in message_lower for word in ["agent", "realtor", "list it"]):
            response = f"That's definitely an option, {lead_name}! The main difference is we can close in as little as 7 days with cash, no repairs needed, and no agent commissions. But I totally understand if you want to explore all your options first."
            
        elif any(word in message_lower for word in ["think about it", "need time"]):
            response = f"Of course, {lead_name}! This is a big decision. How about we just do a quick 10-minute call so you have all the information? No pressure at all - just want to make sure you know what your options are."
            
        else:
            response = f"I hear you, {lead_name}. Let me see if I can address your concerns. Would you be open to a quick call where we can discuss this more? It's much easier to explain over the phone."
        
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
        
        message = f"No problem at all, {lead_name}! I appreciate you letting me know. If your situation changes in the future, feel free to reach out. Have a great day!"
        
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
        System prompt for fix & flip specialist
        """
        return f"""
        You are a Fix & Flip Property Specialist for a real estate investment company.
        
        Lead: {state['lead_name']}
        Property: {state['property_address']}
        Stage: {state['conversation_stage']}
        
        Your expertise:
        - Fix & flip property evaluation
        - Quick cash offers for any condition
        - 7-day closing capability
        - No repair requirements
        
        Qualification Focus:
        1. Occupancy status (vacant/rented/owner-occupied)
        2. Property condition assessment
        3. Repair needs identification
        4. Seller timeline and urgency
        5. Motivation for selling
        
        Communication Style:
        - Professional but friendly
        - Short, conversational responses
        - Always push toward booking calls
        - Handle objections with empathy
        - Emphasize speed, convenience, and cash offers
        
        Key Messages:
        - "We buy houses in any condition"
        - "Close in as little as 7 days"
        - "No repairs needed"
        - "Fair cash offers"
        - "No obligation consultation"
        """


def fix_flip_agent_node(state: RealEstateAgentState) -> Dict[str, Any]:
    """
    Node function for fix & flip specialist agent
    """
    agent = FixFlipSpecialistAgent()
    
    # Get the most recent message if available
    user_message = None
    if state["messages"] and len(state["messages"]) > 0:
        last_message = state["messages"][-1]
        if hasattr(last_message, 'content'):
            user_message = last_message.content
    
    return agent.process_message(state, user_message)


def route_fix_flip_result(state: RealEstateAgentState) -> str:
    """
    Routing function for fix & flip agent results
    """
    next_action = state.get("next_action")
    
    if next_action == "send_message":
        return "communication_router"
    elif next_action == "schedule_appointment":
        return "booking_agent"
    else:
        return "supervisor"
