"""
Base Agent Class for Real Estate LangGraph Agents
Provides common functionality for all agent types
"""

import os
import sqlite3
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schemas.agent_state import RealEstateAgentState, update_state_timestamp


class BaseRealEstateAgent(ABC):
    """
    Base class for all Real Estate agents in the LangGraph system
    """
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.logger = logging.getLogger(f"agent.{agent_name}")
        
        # Initialize OpenAI client
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key and openai_api_key != "test-key":
            self.llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.3,
                api_key=openai_api_key
            )
            self.openai_available = True
        else:
            self.llm = None
            self.openai_available = False
            self.logger.warning("OpenAI API key not configured - AI features disabled")
        
        # Database connection
        self.db_path = "agent_estate.db"
    
    def get_db_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def log_agent_action(self, state: RealEstateAgentState, action: str, details: Dict[str, Any] = None):
        """Log agent actions for debugging and analytics"""
        self.logger.info(f"Agent {self.agent_name} - Lead {state['lead_id']} - {action}")
        if details:
            self.logger.debug(f"Details: {details}")
    
    def update_conversation_in_db(self, state: RealEstateAgentState):
        """Update conversation state in database"""
        conn = self.get_db_connection()
        try:
            # Update lead status
            conn.execute("""
                UPDATE leads 
                SET status = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (state["conversation_stage"], state["lead_id"]))
            
            # Update conversation
            conn.execute("""
                UPDATE conversations 
                SET updated_at = CURRENT_TIMESTAMP 
                WHERE lead_id = ? AND status = 'active'
            """, (state["lead_id"],))
            
            conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to update conversation in DB: {e}")
        finally:
            conn.close()
    
    def analyze_user_message(self, message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze user message for intent, sentiment, and information extraction
        """
        # If OpenAI is not available, return basic analysis
        if not self.openai_available:
            self.logger.info("OpenAI not available, using basic message analysis")
            return self._basic_message_analysis(message, context)
        
        prompt = f"""
        Analyze this user message from a real estate lead:
        
        Message: "{message}"
        Context: {context or {}}
        
        Extract and return:
        1. Intent (interested, not_interested, question, objection, ready_to_book, need_info)
        2. Sentiment (positive, neutral, negative)
        3. Communication style (formal, casual, neutral)
        4. Any specific information mentioned (price, timeline, condition, etc.)
        5. Urgency level (low, medium, high)
        
        Return as JSON format.
        """
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            # Parse the response - in production, you'd want more robust parsing
            return {"intent": "interested", "sentiment": "positive", "style": "casual"}
        except Exception as e:
            self.logger.error(f"Failed to analyze message: {e}")
            return self._basic_message_analysis(message, context)
    
    def _basic_message_analysis(self, message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Basic message analysis without OpenAI
        """
        message_lower = message.lower()
        
        # Basic intent detection
        if any(word in message_lower for word in ["yes", "interested", "sure", "ok", "sounds good"]):
            intent = "interested"
        elif any(word in message_lower for word in ["no", "not interested", "stop", "remove"]):
            intent = "not_interested"
        elif any(word in message_lower for word in ["book", "schedule", "call", "appointment"]):
            intent = "ready_to_book"
        elif "?" in message:
            intent = "question"
        else:
            intent = "unknown"
        
        # Basic sentiment detection
        if any(word in message_lower for word in ["great", "awesome", "perfect", "excellent"]):
            sentiment = "positive"
        elif any(word in message_lower for word in ["bad", "terrible", "awful", "hate"]):
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        return {
            "intent": intent,
            "sentiment": sentiment,
            "style": "neutral",
            "urgency": "medium"
        }
    
    def check_conversation_limits(self, state: RealEstateAgentState) -> bool:
        """
        Check if conversation has reached limits (max messages, time, etc.)
        """
        max_messages = 20
        max_days = 30
        
        if state["total_messages_sent"] >= max_messages:
            self.logger.warning(f"Lead {state['lead_id']} reached max messages limit")
            return False
        
        # Check time limits
        started_at = datetime.fromisoformat(state["conversation_started_at"])
        days_elapsed = (datetime.now() - started_at).days
        
        if days_elapsed >= max_days:
            self.logger.warning(f"Lead {state['lead_id']} reached max time limit")
            return False
        
        return True
    
    def should_escalate_to_human(self, state: RealEstateAgentState) -> bool:
        """
        Determine if conversation should be escalated to human agent
        """
        escalation_triggers = [
            state["retry_count"] > 3,
            len(state["objections_handled"]) > 5,
            state["conversation_sentiment"] == "negative",
            "legal" in str(state.get("last_error", "")).lower(),
            state["booking_attempts"] > 3
        ]
        
        return any(escalation_triggers)
    
    def generate_response_with_context(
        self, 
        state: RealEstateAgentState, 
        user_message: str,
        system_prompt: str
    ) -> str:
        """
        Generate contextual response using conversation history
        """
        # If OpenAI is not available, return basic response
        if not self.openai_available:
            return self._generate_basic_response(state, user_message)
        
        # Build conversation context
        context_messages = []
        
        # Add system prompt
        context_messages.append(HumanMessage(content=system_prompt))
        
        # Add recent conversation history
        recent_messages = state["messages"][-10:]  # Last 10 messages
        context_messages.extend(recent_messages)
        
        # Add current user message
        context_messages.append(HumanMessage(content=user_message))
        
        try:
            response = self.llm.invoke(context_messages)
            return response.content
        except Exception as e:
            self.logger.error(f"Failed to generate response: {e}")
            return self._generate_basic_response(state, user_message)
    
    def _generate_basic_response(self, state: RealEstateAgentState, user_message: str) -> str:
        """
        Generate basic response without OpenAI
        """
        lead_name = state.get("lead_name", "there")
        property_address = state.get("property_address", "your property")
        
        return f"Hi {lead_name}, thanks for your message about {property_address}. I'd love to discuss this further with you. Would you be available for a quick call?"
    
    @abstractmethod
    def process_message(self, state: RealEstateAgentState, user_message: str) -> Dict[str, Any]:
        """
        Process incoming message and return next action
        Must be implemented by each agent
        """
        pass
    
    @abstractmethod
    def get_system_prompt(self, state: RealEstateAgentState) -> str:
        """
        Get system prompt for this agent type
        Must be implemented by each agent
        """
        pass
    
    def handle_error(self, state: RealEstateAgentState, error: Exception) -> RealEstateAgentState:
        """
        Handle errors gracefully and update state
        """
        error_message = str(error)
        self.logger.error(f"Agent {self.agent_name} error for lead {state['lead_id']}: {error_message}")
        
        state["last_error"] = error_message
        state["retry_count"] += 1
        
        return update_state_timestamp(state)
    
    def create_handoff_command(self, target_agent: str, update_data: Dict[str, Any] = None):
        """
        Create command to hand off to another agent
        """
        from langgraph.graph import Command
        
        return Command(
            goto=target_agent,
            update=update_data or {}
        )


class ComplianceChecker:
    """
    Utility class for compliance checking
    """
    
    def __init__(self):
        self.logger = logging.getLogger("compliance")
    
    def check_quiet_hours(self, timezone: str = "America/New_York") -> bool:
        """Check if current time respects quiet hours (8 AM - 9 PM)"""
        import pytz
        
        try:
            tz = pytz.timezone(timezone)
            local_time = datetime.now(tz)
            hour = local_time.hour
            return 8 <= hour <= 21
        except Exception as e:
            self.logger.error(f"Failed to check quiet hours: {e}")
            return False
    
    def check_dnc_status(self, phone_number: str) -> Dict[str, Any]:
        """
        DNC check disabled - leads are pre-screened
        """
        # DNC checking disabled - all provided leads are pre-screened
        return {
            "is_on_dnc": False,
            "checked_at": datetime.now().isoformat(),
            "source": "pre_screened_leads",
            "note": "DNC checking disabled - leads are pre-screened"
        }
    
    def check_opt_out_status(self, phone_number: str) -> bool:
        """
        Check if user has opted out
        """
        conn = sqlite3.connect("agent_estate.db")
        try:
            result = conn.execute("""
                SELECT COUNT(*) FROM opt_outs 
                WHERE phone_number = ? OR email = ?
            """, (phone_number, phone_number)).fetchone()
            return result[0] > 0
        except Exception as e:
            self.logger.error(f"Failed to check opt-out status: {e}")
            return False
        finally:
            conn.close()
    
    def is_compliant_to_contact(
        self, 
        phone_number: Optional[str] = None, 
        email: Optional[str] = None,
        timezone: str = "America/New_York"
    ) -> Dict[str, Any]:
        """
        Comprehensive compliance check
        """
        # Check quiet hours
        quiet_hours_ok = self.check_quiet_hours(timezone)
        
        # Check opt-out status if phone provided
        opt_out_status = False
        if phone_number:
            opt_out_status = self.check_opt_out_status(phone_number)
        
        # DNC check disabled - leads are pre-screened
        dnc_result = {"is_on_dnc": False, "note": "DNC checking disabled - leads are pre-screened"}
        
        # Overall compliance (skip DNC since leads are pre-screened)
        overall_compliant = quiet_hours_ok and not opt_out_status
        
        return {
            "overall_compliant": overall_compliant,
            "quiet_hours": quiet_hours_ok,
            "dnc_status": dnc_result,
            "opt_out_status": opt_out_status,
            "reason": "DNC check skipped - leads are pre-screened" if not overall_compliant else "All checks passed"
        }
