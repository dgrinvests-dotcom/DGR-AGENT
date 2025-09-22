"""
Supervisor Agent - Campaign Orchestrator
Manages high-level routing and campaign decisions
"""

import os
from typing import Dict, Any, Literal
from datetime import datetime

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


class SupervisorAgent(BaseRealEstateAgent):
    """
    Supervisor Agent responsible for:
    - Campaign orchestration
    - High-level routing decisions
    - Compliance oversight
    - Agent handoffs
    """
    
    def __init__(self):
        super().__init__("supervisor")
        self.compliance_checker = ComplianceChecker()
    
    def process_message(self, state: RealEstateAgentState, user_message: str = None) -> Dict[str, Any]:
        """
        Main entry point for supervisor agent
        Routes to appropriate specialist or communication agent
        """
        try:
            self.log_agent_action(state, "processing_supervisor_decision")
            
            # Update agent tracking
            state["current_agent"] = "supervisor"
            if "supervisor" not in state["agent_history"]:
                state["agent_history"].append("supervisor")
            
            # Check if this is initial contact or response processing
            if user_message is None:
                # Initial contact - route to communication
                return self._route_initial_contact(state)
            else:
                # Processing user response - route to specialist
                return self._route_user_response(state, user_message)
                
        except Exception as e:
            self.handle_error(state, e)
            return {"next_agent": "END", "action": "error"}
    
    def _route_initial_contact(self, state: RealEstateAgentState) -> Dict[str, Any]:
        """
        Route initial contact to appropriate communication channel
        """
        # Check compliance first
        compliance_result = self._check_compliance(state)
        if not compliance_result["overall_compliant"]:
            self.log_agent_action(state, "compliance_failed", compliance_result)
            return {
                "next_agent": "END",
                "action": "compliance_failed",
                "state_updates": {"last_error": "Compliance check failed"}
            }
        
        # Update compliance info in state
        state["compliance_info"].update({
            "tcpa_compliant": compliance_result["overall_compliant"],
            "quiet_hours_respected": compliance_result["quiet_hours"],
            "dnc_checked": True,
            "last_compliance_check": datetime.now().isoformat()
        })
        
        # Route to communication router
        return {
            "next_agent": "communication_router",
            "action": "initial_outreach",
            "state_updates": {
                "compliance_info": state["compliance_info"],
                "next_action": "initial_outreach"
            }
        }
    
    def _route_user_response(self, state: RealEstateAgentState, user_message: str) -> Dict[str, Any]:
        """
        Route user response to appropriate property specialist
        """
        # Analyze the user message
        message_analysis = self.analyze_user_message(user_message, {
            "property_type": state["property_type"],
            "conversation_stage": state["conversation_stage"],
            "qualification_data": state["qualification_data"]
        })
        
        # Update state with analysis
        state["conversation_sentiment"] = message_analysis.get("sentiment", "neutral")
        state["user_communication_style"] = message_analysis.get("style", "neutral")
        
        # Check for immediate routing needs
        intent = message_analysis.get("intent", "unknown")
        
        if intent == "not_interested":
            return {
                "next_agent": "END",
                "action": "mark_not_interested",
                "state_updates": {
                    "conversation_stage": "not_interested",
                    "next_action": "mark_not_interested"
                }
            }
        
        elif intent == "ready_to_book":
            return {
                "next_agent": "booking_agent",
                "action": "schedule_appointment",
                "state_updates": {
                    "conversation_stage": "booking",
                    "next_action": "schedule_appointment"
                }
            }
        
        elif intent == "objection":
            # Route to property specialist for objection handling
            return self._route_to_property_specialist(state, "handle_objection")
        
        else:
            # Route to appropriate property specialist
            return self._route_to_property_specialist(state, "continue_qualification")
    
    def _route_to_property_specialist(self, state: RealEstateAgentState, action: str) -> Dict[str, Any]:
        """
        Route to appropriate property specialist based on property type
        """
        property_agents = {
            "fix_flip": "fix_flip_agent",
            "vacant_land": "vacant_land_agent",
            "long_term_rental": "rental_agent"
        }
        
        target_agent = property_agents.get(state["property_type"], "fix_flip_agent")
        
        return {
            "next_agent": target_agent,
            "action": action,
            "state_updates": {
                "current_agent": target_agent,
                "next_action": action
            }
        }
    
    def _check_compliance(self, state: RealEstateAgentState) -> Dict[str, Any]:
        """
        Comprehensive compliance check before any communication
        """
        return self.compliance_checker.is_compliant_to_contact(
            phone_number=state.get("lead_phone"),
            email=state.get("lead_email"),
            timezone="America/New_York"  # TODO: Get from lead data
        )
    
    def should_escalate_conversation(self, state: RealEstateAgentState) -> bool:
        """
        Determine if conversation should be escalated to human
        """
        escalation_conditions = [
            state["retry_count"] > 3,
            state["booking_attempts"] > 3,
            len(state["objections_handled"]) > 5,
            state["conversation_sentiment"] == "negative",
            state["no_show_count"] > 2,
            "legal" in str(state.get("last_error", "")).lower()
        ]
        
        return any(escalation_conditions)
    
    def create_handoff_result(self, target_agent: str, action: str, update_data: Dict[str, Any] = None):
        """
        Create result to hand off to another agent
        """
        return {
            "next_agent": target_agent,
            "action": action,
            "state_updates": update_data or {}
        }
    
    def get_system_prompt(self, state: RealEstateAgentState) -> str:
        """
        System prompt for supervisor agent
        """
        return f"""
        You are the Supervisor Agent for a real estate outreach system.
        
        Current Lead: {state['lead_name']}
        Property: {state['property_address']}
        Property Type: {state['property_type']}
        Campaign: {state['campaign_id']}
        Stage: {state['conversation_stage']}
        
        Your responsibilities:
        1. Route conversations to appropriate specialist agents
        2. Ensure compliance with TCPA/DNC regulations
        3. Monitor conversation quality and escalate when needed
        4. Coordinate between communication channels and specialists
        
        Make routing decisions based on:
        - User intent and sentiment
        - Property type requirements
        - Conversation stage and history
        - Compliance requirements
        
        Always prioritize compliance and lead experience.
        """


def supervisor_agent_node(state: RealEstateAgentState) -> Dict[str, Any]:
    """
    Node function for supervisor agent in LangGraph
    """
    agent = SupervisorAgent()
    
    # Get the most recent message if available
    user_message = None
    if state["messages"] and isinstance(state["messages"][-1], HumanMessage):
        user_message = state["messages"][-1].content
    
    return agent.process_message(state, user_message)


def route_supervisor_decision(state: RealEstateAgentState) -> str:
    """
    Routing function for supervisor agent decisions
    """
    next_action = state.get("next_action")
    
    if next_action == "initial_outreach":
        return "communication_router"
    elif next_action == "schedule_appointment":
        return "booking_agent"
    elif next_action in ["continue_qualification", "handle_objection"]:
        # Route to property specialist
        property_agents = {
            "fix_flip": "fix_flip_agent",
            "vacant_land": "vacant_land_agent", 
            "long_term_rental": "rental_agent"
        }
        return property_agents.get(state["property_type"], "fix_flip_agent")
    elif next_action == "mark_not_interested":
        return "END"
    else:
        # Default routing
        return "communication_router"


# Utility functions for campaign management
def initialize_campaign_conversation(
    lead_id: str,
    lead_name: str,
    property_address: str,
    property_type: Literal["fix_flip", "vacant_land", "long_term_rental"],
    campaign_id: str,
    lead_phone: str = None,
    lead_email: str = None
) -> RealEstateAgentState:
    """
    Initialize a new conversation state for campaign execution
    """
    from schemas.agent_state import create_initial_state
    
    state = create_initial_state(
        lead_id=lead_id,
        lead_name=lead_name,
        property_address=property_address,
        property_type=property_type,
        campaign_id=campaign_id,
        lead_phone=lead_phone,
        lead_email=lead_email
    )
    
    # Set initial routing
    state["current_agent"] = "supervisor"
    state["next_action"] = "initial_outreach"
    
    return state


def check_campaign_limits(campaign_id: str) -> Dict[str, Any]:
    """
    Check if campaign has reached daily/monthly limits
    """
    import sqlite3
    
    conn = sqlite3.connect("agent_estate.db")
    try:
        # Check daily message limits
        daily_count = conn.execute("""
            SELECT COUNT(*) FROM messages 
            WHERE DATE(timestamp) = DATE('now') 
            AND conversation_id IN (
                SELECT id FROM conversations 
                WHERE campaign_id = ?
            )
        """, (campaign_id,)).fetchone()[0]
        
        # Check monthly limits
        monthly_count = conn.execute("""
            SELECT COUNT(*) FROM messages 
            WHERE DATE(timestamp) >= DATE('now', 'start of month')
            AND conversation_id IN (
                SELECT id FROM conversations 
                WHERE campaign_id = ?
            )
        """, (campaign_id,)).fetchone()[0]
        
        return {
            "daily_count": daily_count,
            "monthly_count": monthly_count,
            "daily_limit": 100,  # TODO: Make configurable
            "monthly_limit": 2000,  # TODO: Make configurable
            "can_send": daily_count < 100 and monthly_count < 2000
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "can_send": False
        }
    finally:
        conn.close()
