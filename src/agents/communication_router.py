"""
Communication Router Agent
Handles multi-channel communication priority and routing
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from langchain_core.messages import HumanMessage, AIMessage

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.base_agent import BaseRealEstateAgent, ComplianceChecker
from schemas.agent_state import (
    RealEstateAgentState, 
    update_state_timestamp,
    add_communication_attempt
)


class CommunicationRouterAgent(BaseRealEstateAgent):
    """
    Communication Router Agent responsible for:
    - Multi-channel communication priority (SMS → Email)
    - Channel availability checking
    - Communication timing optimization
    - Fallback routing
    """
    
    def __init__(self):
        super().__init__("communication_router")
        self.compliance_checker = ComplianceChecker()
    
    def process_message(self, state: RealEstateAgentState, user_message: str = None) -> Dict[str, Any]:
        """
        Route communication to appropriate channel based on priority and availability
        """
        try:
            self.log_agent_action(state, "routing_communication")
            
            # Update agent tracking
            state["current_agent"] = "communication_router"
            if "communication_router" not in state["agent_history"]:
                state["agent_history"].append("communication_router")
            
            # Determine best communication channel
            channel_decision = self._determine_communication_channel(state)
            
            if channel_decision["channel"] == "sms":
                return {
                    "next_agent": "sms_agent",
                    "action": channel_decision["action"],
                    "state_updates": {
                        "preferred_channel": "sms",
                        "next_action": channel_decision["action"],
                        "routing_reason": channel_decision["reason"]
                    }
                }
            
            elif channel_decision["channel"] == "email":
                return {
                    "next_agent": "email_agent",
                    "action": channel_decision["action"],
                    "state_updates": {
                        "preferred_channel": "email",
                        "next_action": channel_decision["action"],
                        "routing_reason": channel_decision["reason"]
                    }
                }
            
            else:
                # No communication channel available
                return {
                    "next_agent": "END",
                    "action": "no_channels_available",
                    "state_updates": {
                        "last_error": "No available communication channels",
                        "conversation_stage": "failed"
                    }
                }
                
        except Exception as e:
            self.handle_error(state, e)
            return {"next_agent": "END", "action": "error"}
    
    def _determine_communication_channel(self, state: RealEstateAgentState) -> Dict[str, Any]:
        """
        Determine the best communication channel based on priority and availability
        
        Priority: SMS > Email
        """
        
        # Check SMS availability and priority
        if self._can_use_sms(state):
            return {
                "channel": "sms",
                "action": "send_message",
                "reason": "SMS available and preferred",
                "priority": 1
            }
        
        # Check Email availability as fallback
        elif self._can_use_email(state):
            return {
                "channel": "email", 
                "action": "send_message",
                "reason": "Email fallback - SMS unavailable",
                "priority": 2
            }
        
        # No channels available
        else:
            return {
                "channel": None,
                "action": "escalate",
                "reason": "No communication channels available",
                "priority": 0
            }
    
    def _can_use_sms(self, state: RealEstateAgentState) -> bool:
        """
        Check if SMS communication is available and compliant
        """
        # Check if phone number exists
        if not state.get("lead_phone"):
            self.log_agent_action(state, "sms_unavailable", {"reason": "no_phone_number"})
            return False
        
        # Check if SMS has failed recently
        if state.get("sms_failed"):
            if self._sms_failed_recently(state):
                self.log_agent_action(state, "sms_unavailable", {"reason": "recent_failure"})
                return False
        
        # Check compliance
        compliance_result = self.compliance_checker.is_compliant_to_contact(
            phone_number=state["lead_phone"]
        )
        
        if not compliance_result["overall_compliant"]:
            self.log_agent_action(state, "sms_unavailable", {"reason": "compliance_failed", "details": compliance_result})
            return False
        
        # Check daily SMS limits
        if self._reached_sms_limits(state):
            self.log_agent_action(state, "sms_unavailable", {"reason": "daily_limits_reached"})
            return False
        
        return True
    
    def _can_use_email(self, state: RealEstateAgentState) -> bool:
        """
        Check if Email communication is available
        """
        # Check if email address exists
        if not state.get("lead_email"):
            self.log_agent_action(state, "email_unavailable", {"reason": "no_email_address"})
            return False
        
        # Check if email has failed recently
        if state.get("email_failed"):
            if self._email_failed_recently(state):
                self.log_agent_action(state, "email_unavailable", {"reason": "recent_failure"})
                return False
        
        # Check opt-out status
        if self.compliance_checker.check_opt_out_status(state["lead_email"]):
            self.log_agent_action(state, "email_unavailable", {"reason": "opted_out"})
            return False
        
        # Check daily email limits
        if self._reached_email_limits(state):
            self.log_agent_action(state, "email_unavailable", {"reason": "daily_limits_reached"})
            return False
        
        return True
    
    def _sms_failed_recently(self, state: RealEstateAgentState, hours: int = 24) -> bool:
        """
        Check if SMS failed within the last N hours
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        for attempt in state["communication_attempts"]:
            if (attempt["method"] == "sms" and 
                not attempt["success"] and
                datetime.fromisoformat(attempt["timestamp"]) > cutoff_time):
                return True
        
        return False
    
    def _email_failed_recently(self, state: RealEstateAgentState, hours: int = 6) -> bool:
        """
        Check if Email failed within the last N hours
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        for attempt in state["communication_attempts"]:
            if (attempt["method"] == "email" and 
                not attempt["success"] and
                datetime.fromisoformat(attempt["timestamp"]) > cutoff_time):
                return True
        
        return False
    
    def _reached_sms_limits(self, state: RealEstateAgentState) -> bool:
        """
        Check if daily SMS limits have been reached
        """
        today = datetime.now().date()
        sms_count_today = 0
        
        for attempt in state["communication_attempts"]:
            if (attempt["method"] == "sms" and 
                datetime.fromisoformat(attempt["timestamp"]).date() == today):
                sms_count_today += 1
        
        # Max 5 SMS per lead per day
        return sms_count_today >= 5
    
    def _reached_email_limits(self, state: RealEstateAgentState) -> bool:
        """
        Check if daily email limits have been reached
        """
        today = datetime.now().date()
        email_count_today = 0
        
        for attempt in state["communication_attempts"]:
            if (attempt["method"] == "email" and 
                datetime.fromisoformat(attempt["timestamp"]).date() == today):
                email_count_today += 1
        
        # Max 3 emails per lead per day
        return email_count_today >= 3
    
    def get_optimal_send_time(self, state: RealEstateAgentState, channel: str) -> Optional[datetime]:
        """
        Determine optimal time to send message based on lead behavior
        """
        # For now, return immediate send if within business hours
        now = datetime.now()
        hour = now.hour
        
        # Business hours: 9 AM - 6 PM
        if 9 <= hour <= 18:
            return now
        
        # Schedule for next business day at 9 AM
        next_send = now.replace(hour=9, minute=0, second=0, microsecond=0)
        if hour >= 18:
            next_send += timedelta(days=1)
        
        return next_send
    
    def get_system_prompt(self, state: RealEstateAgentState) -> str:
        """
        System prompt for communication router
        """
        return f"""
        You are the Communication Router for a real estate outreach system.
        
        Lead: {state['lead_name']}
        Property: {state['property_address']}
        Available Channels: SMS ({state.get('lead_phone', 'N/A')}), Email ({state.get('lead_email', 'N/A')})
        
        Your responsibilities:
        1. Route communications to the best available channel
        2. Prioritize SMS over Email when both are available
        3. Ensure compliance with communication regulations
        4. Handle channel failures and fallbacks
        5. Respect daily communication limits
        
        Channel Priority:
        1. SMS (immediate, high engagement)
        2. Email (fallback, professional)
        
        Always check:
        - Channel availability
        - Compliance requirements
        - Recent failures
        - Daily limits
        - Optimal timing
        """


def communication_router_node(state: RealEstateAgentState) -> Dict[str, Any]:
    """
    Node function for communication router in LangGraph
    """
    agent = CommunicationRouterAgent()
    return agent.process_message(state)


def route_communication_channel(state: RealEstateAgentState) -> str:
    """
    Routing function for communication channel decisions
    """
    preferred_channel = state.get("preferred_channel")
    
    if preferred_channel == "sms":
        return "sms_agent"
    elif preferred_channel == "email":
        return "email_agent"
    else:
        # Default to END if no channel available
        return "END"


# Utility functions for communication management
def get_communication_stats(lead_id: str) -> Dict[str, Any]:
    """
    Get communication statistics for a lead
    """
    import sqlite3
    
    conn = sqlite3.connect("agent_estate.db")
    try:
        # Get message counts by method
        stats = conn.execute("""
            SELECT 
                method,
                COUNT(*) as total_messages,
                SUM(CASE WHEN ai_generated = 1 THEN 1 ELSE 0 END) as ai_messages,
                MAX(timestamp) as last_message
            FROM messages m
            JOIN conversations c ON m.conversation_id = c.id
            WHERE c.lead_id = ?
            GROUP BY method
        """, (lead_id,)).fetchall()
        
        result = {
            "sms": {"total": 0, "ai_generated": 0, "last_message": None},
            "email": {"total": 0, "ai_generated": 0, "last_message": None}
        }
        
        for stat in stats:
            method = stat["method"]
            if method in result:
                result[method] = {
                    "total": stat["total_messages"],
                    "ai_generated": stat["ai_messages"],
                    "last_message": stat["last_message"]
                }
        
        return result
        
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()


def update_channel_failure(state: RealEstateAgentState, channel: str, error: str):
    """
    Update state when a communication channel fails
    """
    if channel == "sms":
        state["sms_failed"] = True
    elif channel == "email":
        state["email_failed"] = True
    
    state["last_error"] = f"{channel} failure: {error}"
    state["retry_count"] += 1
    
    return update_state_timestamp(state)
