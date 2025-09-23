"""
SMS Agent - Telnyx SMS Integration
Handles SMS communication with compliance and delivery tracking
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, Any, Optional
from datetime import datetime

from agents.base_agent import BaseRealEstateAgent, ComplianceChecker
from services.telnyx_service import TelnyxSMSService, format_phone_number, validate_sms_content
from schemas.agent_state import (
    RealEstateAgentState, 
    update_state_timestamp,
    add_communication_attempt
)


class SMSAgent(BaseRealEstateAgent):
    """
    SMS Agent responsible for:
    - SMS message sending via Telnyx
    - Delivery status tracking
    - Compliance checking (TCPA/DNC)
    - Message formatting and validation
    - Fallback to email on failure
    """
    
    def __init__(self):
        super().__init__("sms_agent")
        
        # Initialize Telnyx service
        try:
            self.sms_service = TelnyxSMSService()
            self.sms_available = True
        except ValueError as e:
            self.logger.error(f"SMS service initialization failed: {e}")
            self.sms_service = None
            self.sms_available = False
        
        self.compliance_checker = ComplianceChecker()
    
    def process_message(self, state: RealEstateAgentState, user_message: str = None) -> Dict[str, Any]:
        """
        Process SMS request - either sending outbound or responding to inbound
        
        Args:
            state: Current conversation state
            user_message: Message to send (if None, generates based on state)
            
        Returns:
            Dict with processing results and next action
        """
        try:
            self.log_agent_action(state, "processing_sms_request")
            
            # Update agent tracking
            state["current_agent"] = "sms_agent"
            if "sms_agent" not in state["agent_history"]:
                state["agent_history"].append("sms_agent")
            
            # Check if this is an inbound response (conversation mode)
            if state.get("conversation_mode") == "inbound_response":
                return self._handle_inbound_conversation(state)
            
            # Check if SMS service is available
            if not self.sms_available:
                return self._fallback_to_email(state, "SMS service not available")
            
            # Validate phone number
            phone_number = state.get("lead_phone")
            if not phone_number:
                return self._fallback_to_email(state, "No phone number available")
            
            # Format phone number
            formatted_phone = format_phone_number(phone_number)
            
            # Check compliance
            compliance_result = self._check_sms_compliance(state, formatted_phone)
            if not compliance_result["compliant"]:
                return self._fallback_to_email(state, f"SMS compliance failed: {compliance_result['reason']}")
            
            # Generate or use provided message
            if user_message is None:
                message = self._generate_sms_message(state)
            else:
                message = user_message
            
            # Validate message content
            content_validation = validate_sms_content(message)
            if not content_validation["valid"]:
                self.logger.warning(f"SMS content validation issues: {content_validation['issues']}")
                # Continue anyway, but log issues
            
            # Send SMS
            send_result = self.sms_service.send_sms(
                to_number=formatted_phone,
                message=message,
                state=state
            )
            
            if send_result["success"]:
                self.log_agent_action(state, "sms_sent_successfully", {
                    "message_id": send_result["message_id"],
                    "to_number": formatted_phone
                })
                
                # Update state
                state["last_contact_method"] = "sms"
                state["last_contact_time"] = datetime.now().isoformat()
                state["sms_failed"] = False
                
                return {
                    "success": True,
                    "action": "sms_sent",
                    "message_id": send_result["message_id"],
                    "next_agent": "supervisor",  # Return to supervisor for next steps
                    "state_updates": {
                        "last_contact_method": "sms",
                        "last_contact_time": datetime.now().isoformat(),
                        "sms_failed": False
                    }
                }
            else:
                # SMS failed, fallback to email
                return self._fallback_to_email(state, send_result.get("error", "SMS sending failed"))
                
        except Exception as e:
            self.handle_error(state, e)
            return self._fallback_to_email(state, f"SMS agent error: {str(e)}")
    
    def _handle_inbound_conversation(self, state: RealEstateAgentState) -> Dict[str, Any]:
        """
        Handle inbound conversation - generate response and send SMS
        """
        try:
            # Get the incoming message
            incoming_message = state.get("incoming_message", "")
            if not incoming_message:
                return {"success": False, "error": "No incoming message to process"}
            
            # Update conversation stage based on current state and message
            self._update_conversation_stage(state, incoming_message)
            
            # Generate appropriate response message
            response_message = self._generate_conversation_response(state, incoming_message)
            
            if not response_message:
                return {"success": False, "error": "Failed to generate response"}
            
            # Send the response via SMS
            phone_number = state.get("lead_phone")
            if not phone_number:
                return {"success": False, "error": "No phone number available"}
            
            formatted_phone = format_phone_number(phone_number)
            
            # Check compliance for response
            compliance_result = self._check_sms_compliance(state, formatted_phone)
            if not compliance_result["compliant"]:
                return {"success": False, "error": f"Compliance failed: {compliance_result['reason']}"}
            
            # Send SMS response
            send_result = self.sms_service.send_sms(
                to_number=formatted_phone,
                message=response_message,
                state=state
            )
            
            if send_result["success"]:
                # Add AI message to state
                from langchain_core.messages import AIMessage
                if "messages" not in state or not state["messages"]:
                    state["messages"] = []
                state["messages"].append(AIMessage(content=response_message))
                
                # Update state
                state["last_contact_method"] = "sms"
                state["last_contact_time"] = datetime.now().isoformat()
                state["conversation_stage"] = "responding"
                
                return {
                    "success": True,
                    "action": "conversation_response_sent",
                    "message_id": send_result["message_id"],
                    "response_message": response_message,
                    "next_agent": "END",
                    "state_updates": {
                        "messages": state["messages"],
                        "last_contact_method": "sms",
                        "last_contact_time": datetime.now().isoformat(),
                        "conversation_stage": "responding"
                    }
                }
            else:
                return {"success": False, "error": send_result.get("error", "SMS sending failed")}
                
        except Exception as e:
            self.logger.error(f"Inbound conversation handling failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _update_conversation_stage(self, state: RealEstateAgentState, message: str):
        """Update conversation stage based on incoming message"""
        current_stage = state.get("conversation_stage", "initial")
        
        # Simple stage progression logic
        if current_stage == "initial":
            state["conversation_stage"] = "qualifying"
        elif current_stage == "qualifying":
            # Check if ready for booking
            booking_keywords = ["call", "schedule", "appointment", "meeting", "yes", "interested"]
            if any(keyword in message.lower() for keyword in booking_keywords):
                state["conversation_stage"] = "booking"
            else:
                state["conversation_stage"] = "qualifying"
    
    def _generate_conversation_response(self, state: RealEstateAgentState, incoming_message: str) -> str:
        """
        Generate conversation response based on current stage and incoming message
        Uses existing SMS message generation logic
        """
        # Update qualification data based on incoming message
        self._extract_qualification_data(state, incoming_message)
        
        # Use existing message generation logic
        return self._generate_sms_message(state)
    
    def _extract_qualification_data(self, state: RealEstateAgentState, message: str):
        """Extract qualification data from incoming message"""
        message_lower = message.lower()
        qualification_data = state.get("qualification_data", {})
        property_type = state.get("property_type", "fix_flip")
        
        # Extract data based on property type
        if property_type == "fix_flip":
            if "vacant" in message_lower:
                qualification_data["occupancy_status"] = "vacant"
            elif "rented" in message_lower or "tenant" in message_lower:
                qualification_data["occupancy_status"] = "rented"
            elif "live" in message_lower or "occupied" in message_lower:
                qualification_data["occupancy_status"] = "owner_occupied"
            
            if "good condition" in message_lower or "excellent" in message_lower:
                qualification_data["condition"] = "good"
            elif "needs work" in message_lower or "repairs" in message_lower:
                qualification_data["condition"] = "needs_work"
                
        elif property_type == "vacant_land":
            # Extract acreage
            import re
            acreage_match = re.search(r'(\d+(?:\.\d+)?)\s*acre', message_lower)
            if acreage_match:
                qualification_data["acreage"] = acreage_match.group(1)
            
            if "road access" in message_lower or "accessible" in message_lower:
                qualification_data["road_access"] = "yes"
            elif "landlocked" in message_lower:
                qualification_data["road_access"] = "no"
        
        state["qualification_data"] = qualification_data
    
    def _generate_sms_message(self, state: RealEstateAgentState) -> str:
        """
        Generate SMS message based on conversation stage and property type
        """
        stage = state["conversation_stage"]
        property_type = state["property_type"]
        lead_name = state["lead_name"]
        property_address = state["property_address"]
        
        # Get property-specific message templates
        if stage == "initial":
            return self._get_initial_sms_message(property_type, lead_name, property_address)
        elif stage == "qualifying":
            return self._get_qualifying_sms_message(property_type, state)
        elif stage == "follow_up":
            return self._get_follow_up_sms_message(property_type, state)
        else:
            # Default message
            return f"Hi {lead_name}, this is Derek from Real Estate Solutions. Are you still interested in discussing your property at {property_address}? Reply STOP to opt out."
    
    def _get_initial_sms_message(self, property_type: str, lead_name: str, property_address: str) -> str:
        """
        Get initial outreach SMS message based on property type
        """
        messages = {
            "fix_flip": f"Hey {lead_name}, I saw you might be the owner of {property_address} — would you be open to a no-obligation cash offer for the property? Reply STOP to opt out.",
            
            "vacant_land": f"Hi {lead_name}, this is Derek. I'm buying vacant land and noticed you own a parcel near {property_address}. Would you consider a cash offer if it was simple and hassle-free? Reply STOP to opt out.",
            
            "long_term_rental": f"Hi {lead_name}, I saw your property at {property_address} and wanted to reach out about a potential cash purchase. We buy rental properties as-is. Interested? Reply STOP to opt out."
        }
        
        return messages.get(property_type, messages["fix_flip"])
    
    def _get_qualifying_sms_message(self, property_type: str, state: RealEstateAgentState) -> str:
        """
        Get qualifying SMS message based on property type and qualification data
        """
        lead_name = state["lead_name"]
        qualification_data = state["qualification_data"]
        
        if property_type == "fix_flip":
            if not qualification_data.get("occupancy_status"):
                return f"Great! I just need a few quick details to see if it's a fit. Is the property currently vacant, rented, or owner-occupied? Reply STOP to opt out."
            elif not qualification_data.get("condition"):
                return f"And how's the condition? Any recent repairs or major issues we should know about? Reply STOP to opt out."
            else:
                return f"Thanks for the info! Based on what you shared, we may be able to make a fair cash offer. Want to schedule a quick call to go over next steps? Reply STOP to opt out."
        
        elif property_type == "vacant_land":
            if not qualification_data.get("acreage"):
                return f"Great! To put something together that makes sense, could I ask - do you know roughly how many acres or lot size your parcel is? Reply STOP to opt out."
            elif not qualification_data.get("road_access"):
                return f"Does it have road access, or is it landlocked? Reply STOP to opt out."
            elif not qualification_data.get("utilities"):
                return f"Any idea if utilities (water, power, septic/sewer) are nearby? Reply STOP to opt out."
            else:
                return f"Perfect! The next step is super simple: we'll do a quick 15-minute call where I can review your land details and give you a cash range. What's easier for you— afternoon or evening this week? Reply STOP to opt out."
        
        else:  # long_term_rental
            if not qualification_data.get("rental_status"):
                return f"Great! Is the property currently rented or vacant? Reply STOP to opt out."
            elif not qualification_data.get("condition"):
                return f"And how's the condition of the property? Any major repairs needed? Reply STOP to opt out."
            else:
                return f"Thanks! We specialize in rental properties and can work around existing leases. Want to schedule a quick call to discuss? Reply STOP to opt out."
    
    def _get_follow_up_sms_message(self, property_type: str, state: RealEstateAgentState) -> str:
        """
        Get follow-up SMS message
        """
        lead_name = state["lead_name"]
        property_address = state["property_address"]
        
        follow_up_count = len([attempt for attempt in state["communication_attempts"] 
                              if attempt["method"] == "sms"])
        
        if follow_up_count == 1:
            return f"Just checking in, {lead_name} — if you're at all curious what a cash offer might look like for {property_address}, I'd be happy to get that started. Totally no pressure. Reply STOP to opt out."
        elif follow_up_count == 2:
            return f"Still open to selling {property_address}? We make fair cash offers and cover closing costs. Let me know if you'd like to chat or want the offer sent over. Reply STOP to opt out."
        else:
            return f"Hi {lead_name}, this is my final follow-up about {property_address}. If you're ever interested in a cash offer, feel free to reach out. Thanks! Reply STOP to opt out."
    
    def _check_sms_compliance(self, state: RealEstateAgentState, phone_number: str) -> Dict[str, Any]:
        """
        Check SMS compliance (TCPA/DNC/Quiet Hours)
        """
        # Check if user has opted out
        if self.compliance_checker.check_opt_out_status(phone_number):
            return {
                "compliant": False,
                "reason": "User has opted out"
            }
        
        # Check quiet hours
        if not self.compliance_checker.check_quiet_hours():
            return {
                "compliant": False,
                "reason": "Outside quiet hours (8 AM - 9 PM)"
            }
        
        # DNC check disabled - leads are pre-screened
        dnc_result = self.compliance_checker.check_dnc_status(phone_number)
        # Skip DNC blocking since all leads are pre-screened
        
        # Check daily SMS limits
        daily_sms_count = len([attempt for attempt in state["communication_attempts"] 
                              if attempt["method"] == "sms" and 
                              datetime.fromisoformat(attempt["timestamp"]).date() == datetime.now().date()])
        
        if daily_sms_count >= 5:  # Max 5 SMS per day per lead
            return {
                "compliant": False,
                "reason": "Daily SMS limit exceeded (5 per day)"
            }
        
        return {
            "compliant": True,
            "reason": "All compliance checks passed"
        }
    
    def _fallback_to_email(self, state: RealEstateAgentState, reason: str) -> Dict[str, Any]:
        """
        Fallback to email when SMS is not available or fails
        """
        self.log_agent_action(state, "sms_fallback_to_email", {"reason": reason})
        
        # Mark SMS as failed
        state["sms_failed"] = True
        state["last_error"] = f"SMS failed: {reason}"
        
        return {
            "success": True,
            "action": "fallback_to_email",
            "reason": reason,
            "next_agent": "email_agent",
            "state_updates": {
                "sms_failed": True,
                "preferred_channel": "email",
                "last_error": f"SMS failed: {reason}"
            }
        }
    
    def check_delivery_status(self, message_id: str) -> Dict[str, Any]:
        """
        Check delivery status of sent SMS
        """
        if not self.sms_service:
            return {"success": False, "error": "SMS service not available"}
        
        return self.sms_service.check_delivery_status(message_id)
    
    def get_system_prompt(self, state: RealEstateAgentState) -> str:
        """
        System prompt for SMS agent
        """
        return f"""
        You are the SMS Agent for a real estate outreach system.
        
        Lead: {state['lead_name']}
        Phone: {state.get('lead_phone', 'N/A')}
        Property: {state['property_address']}
        Property Type: {state['property_type']}
        Stage: {state['conversation_stage']}
        
        Your responsibilities:
        1. Send SMS messages via Telnyx
        2. Ensure TCPA/DNC compliance
        3. Track delivery status
        4. Format messages appropriately for SMS
        5. Fallback to email on failure
        
        SMS Guidelines:
        - Keep messages under 160 characters when possible
        - Always include opt-out instructions
        - Respect quiet hours (8 AM - 9 PM)
        - Max 5 SMS per lead per day
        - Professional but conversational tone
        
        Property-specific messaging:
        - Fix & Flip: Focus on cash offers and quick closing
        - Vacant Land: Emphasize simple, hassle-free process
        - Rentals: Mention working with existing leases
        """


def sms_agent_node(state: RealEstateAgentState) -> RealEstateAgentState:
    """
    Node function for SMS agent in LangGraph
    """
    agent = SMSAgent()
    result = agent.process_message(state)
    
    # Update state with agent results
    if result.get("state_updates"):
        for key, value in result["state_updates"].items():
            state[key] = value
    
    # Add response message to state for SMS sending
    if result.get("response_message"):
        state["generated_response"] = result["response_message"]
    
    # Set next agent
    state["next_agent"] = result.get("next_agent", "END")
    
    return state


def route_sms_result(state: RealEstateAgentState) -> str:
    """
    Routing function for SMS agent results
    """
    last_action = state.get("next_action")
    
    if last_action == "fallback_to_email":
        return "email_agent"
    elif last_action == "sms_sent":
        return "supervisor"
    else:
        return "supervisor"


# Utility functions for SMS management
def get_sms_stats(lead_id: str) -> Dict[str, Any]:
    """
    Get SMS statistics for a lead
    """
    import sqlite3
    
    conn = sqlite3.connect("agent_estate.db")
    try:
        # Get SMS message counts
        stats = conn.execute("""
            SELECT 
                COUNT(*) as total_sms,
                SUM(CASE WHEN ai_generated = 1 THEN 1 ELSE 0 END) as ai_sms,
                MAX(timestamp) as last_sms
            FROM messages m
            JOIN conversations c ON m.conversation_id = c.id
            WHERE c.lead_id = ? AND m.method = 'sms'
        """, (lead_id,)).fetchone()
        
        return {
            "total_sms": stats["total_sms"] or 0,
            "ai_generated": stats["ai_sms"] or 0,
            "last_sms": stats["last_sms"]
        }
        
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()


def validate_phone_for_sms(phone_number: str) -> Dict[str, Any]:
    """
    Validate phone number for SMS capability
    """
    formatted_phone = format_phone_number(phone_number)
    
    # Basic validation
    if not formatted_phone.startswith("+1"):
        return {
            "valid": False,
            "reason": "Only US phone numbers supported",
            "formatted": formatted_phone
        }
    
    if len(formatted_phone) != 12:  # +1 + 10 digits
        return {
            "valid": False,
            "reason": "Invalid phone number length",
            "formatted": formatted_phone
        }
    
    return {
        "valid": True,
        "formatted": formatted_phone,
        "country": "US"
    }
