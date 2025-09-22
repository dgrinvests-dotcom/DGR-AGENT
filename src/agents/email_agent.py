"""
Email Agent - Enhanced Gmail Integration
Handles email communication with threading and reply monitoring
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, Any, Optional, List
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import make_msgid

from agents.base_agent import BaseRealEstateAgent, ComplianceChecker
from schemas.agent_state import (
    RealEstateAgentState, 
    update_state_timestamp,
    add_communication_attempt
)


class EmailAgent(BaseRealEstateAgent):
    """
    Email Agent responsible for:
    - Email sending via Gmail SMTP
    - Email threading maintenance
    - Reply monitoring and processing
    - Professional email formatting
    - Fallback when SMS fails
    """
    
    def __init__(self):
        super().__init__("email_agent")
        
        # Gmail configuration
        self.gmail_address = os.getenv("GMAIL_ADDRESS")
        self.gmail_password = os.getenv("GMAIL_APP_PASSWORD")
        
        if not self.gmail_address or not self.gmail_password:
            self.logger.error("Gmail credentials not configured")
            self.email_available = False
        else:
            self.email_available = True
        
        self.compliance_checker = ComplianceChecker()
        
        # Email threading storage
        self.thread_info = {}
    
    def process_message(self, state: RealEstateAgentState, user_message: str = None) -> Dict[str, Any]:
        """
        Process email sending request
        
        Args:
            state: Current conversation state
            user_message: Message to send (if None, generates based on state)
            
        Returns:
            Dict with processing results and next action
        """
        try:
            self.log_agent_action(state, "processing_email_request")
            
            # Update agent tracking
            state["current_agent"] = "email_agent"
            if "email_agent" not in state["agent_history"]:
                state["agent_history"].append("email_agent")
            
            # Check if email service is available
            if not self.email_available:
                return self._handle_email_failure(state, "Email service not configured")
            
            # Validate email address
            email_address = state.get("lead_email")
            if not email_address:
                return self._handle_email_failure(state, "No email address available")
            
            # Check compliance (basic opt-out check)
            if self.compliance_checker.check_opt_out_status(email_address):
                return self._handle_email_failure(state, "Lead has opted out of email communication")
            
            # Generate or use provided message
            if user_message is None:
                email_content = self._generate_email_content(state)
            else:
                email_content = self._format_user_message_as_email(state, user_message)
            
            # Get threading information
            threading_info = self._get_threading_info(state)
            
            # Send email
            send_result = self._send_email(
                to_email=email_address,
                subject=email_content["subject"],
                message=email_content["body"],
                state=state,
                threading_info=threading_info
            )
            
            if send_result["success"]:
                self.log_agent_action(state, "email_sent_successfully", {
                    "to_email": email_address,
                    "subject": email_content["subject"]
                })
                
                # Update state
                state["last_contact_method"] = "email"
                state["last_contact_time"] = datetime.now().isoformat()
                state["email_failed"] = False
                
                # Store threading info for future emails
                self._store_threading_info(state, send_result.get("message_id"))
                
                return {
                    "success": True,
                    "action": "email_sent",
                    "to_email": email_address,
                    "subject": email_content["subject"],
                    "next_agent": "supervisor",
                    "state_updates": {
                        "last_contact_method": "email",
                        "last_contact_time": datetime.now().isoformat(),
                        "email_failed": False
                    }
                }
            else:
                return self._handle_email_failure(state, send_result.get("error", "Email sending failed"))
                
        except Exception as e:
            self.handle_error(state, e)
            return self._handle_email_failure(state, f"Email agent error: {str(e)}")
    
    def _generate_email_content(self, state: RealEstateAgentState) -> Dict[str, str]:
        """
        Generate email content based on conversation stage and property type
        """
        stage = state["conversation_stage"]
        property_type = state["property_type"]
        
        if stage == "initial":
            return self._get_initial_email_content(state)
        elif stage == "qualifying":
            return self._get_qualifying_email_content(state)
        elif stage == "follow_up":
            return self._get_follow_up_email_content(state)
        else:
            return self._get_default_email_content(state)
    
    def _get_initial_email_content(self, state: RealEstateAgentState) -> Dict[str, str]:
        """
        Get initial outreach email content
        """
        lead_name = state["lead_name"]
        property_address = state["property_address"]
        property_type = state["property_type"]
        
        subjects = {
            "fix_flip": f"Quick Cash Offer for Your Property - {property_address}",
            "vacant_land": f"Cash Offer for Your Land Near {property_address}",
            "long_term_rental": f"Cash Purchase Inquiry - {property_address}"
        }
        
        bodies = {
            "fix_flip": f"""Hi {lead_name},

I hope this email finds you well. I noticed you might be the owner of the property at {property_address}, and I wanted to reach out about a potential opportunity.

We're local real estate investors who specialize in purchasing homes for cash. We can:
• Close quickly (as fast as 7 days)
• Buy houses in any condition
• Handle all the paperwork
• Cover closing costs

Would you be open to a no-obligation cash offer for your property? We make the process simple and straightforward.

If you're interested, I'd be happy to schedule a quick 15-minute call to discuss your situation and see if we can help.

Best regards,
Derek
Real Estate Solutions Team

P.S. If you're not interested, just reply and let me know - I completely understand and won't contact you again.""",

            "vacant_land": f"""Hi {lead_name},

I hope you're doing well. My name is Derek, and I'm actively buying vacant land in your area.

I noticed you own a parcel near {property_address}, and I wanted to see if you'd be interested in a cash offer. We specialize in making the land selling process simple and hassle-free:

• All-cash purchases
• Quick 15-minute consultation calls
• No complicated paperwork
• Fast closing process

Would you be open to a brief conversation about your land? I can usually provide a cash range right over the phone after asking a few quick questions.

You can reply to this email or we can schedule a quick call at your convenience.

Best regards,
Derek
Land Investment Team

P.S. If you're not interested in selling, just let me know and I won't reach out again.""",

            "long_term_rental": f"""Hi {lead_name},

I hope this message finds you well. I came across your property at {property_address} and wanted to reach out about a potential cash purchase opportunity.

We specialize in purchasing rental properties and understand the unique challenges that come with them:
• We can work around existing leases
• Handle tenant communications if needed
• Close quickly with all cash
• Take the property as-is

Whether your property is currently rented or vacant, we'd love to discuss a potential purchase that works for your timeline and situation.

Would you be interested in a quick 15-minute call to explore this opportunity?

Best regards,
Derek
Real Estate Investment Team

P.S. If this isn't something you're interested in, just reply and let me know - no problem at all."""
        }
        
        return {
            "subject": subjects.get(property_type, subjects["fix_flip"]),
            "body": bodies.get(property_type, bodies["fix_flip"])
        }
    
    def _get_qualifying_email_content(self, state: RealEstateAgentState) -> Dict[str, str]:
        """
        Get qualifying email content
        """
        lead_name = state["lead_name"]
        property_address = state["property_address"]
        
        return {
            "subject": f"Re: Your Property Inquiry - {property_address}",
            "body": f"""Hi {lead_name},

Thanks for your interest in our cash offer for {property_address}!

To provide you with the most accurate offer, I'd like to ask a few quick questions about the property. This will help me give you a fair and competitive cash offer.

Would you prefer to discuss this over a quick phone call, or would you like me to send the questions via email?

Either way works great for me - I just want to make this as convenient as possible for you.

Looking forward to hearing from you!

Best regards,
Derek
Real Estate Solutions Team"""
        }
    
    def _get_follow_up_email_content(self, state: RealEstateAgentState) -> Dict[str, str]:
        """
        Get follow-up email content
        """
        lead_name = state["lead_name"]
        property_address = state["property_address"]
        
        follow_up_count = len([attempt for attempt in state["communication_attempts"] 
                              if attempt["method"] == "email"])
        
        if follow_up_count == 1:
            return {
                "subject": f"Following up - Cash Offer for {property_address}",
                "body": f"""Hi {lead_name},

I wanted to follow up on my previous email about your property at {property_address}.

I understand you're probably busy, but I didn't want you to miss out on this opportunity if you're interested in a cash offer.

We're still very interested in purchasing your property and can move quickly if the numbers work for both of us.

Would you like to schedule a brief call this week to discuss?

Best regards,
Derek
Real Estate Solutions Team"""
            }
        else:
            return {
                "subject": f"Final Follow-up - {property_address}",
                "body": f"""Hi {lead_name},

This will be my final follow-up regarding your property at {property_address}.

I don't want to be a bother, but I wanted to give you one last opportunity to explore a cash sale if you're interested.

If now isn't the right time, I completely understand. Feel free to reach out in the future if your situation changes.

Thanks for your time, and I wish you all the best!

Best regards,
Derek
Real Estate Solutions Team"""
            }
    
    def _get_default_email_content(self, state: RealEstateAgentState) -> Dict[str, str]:
        """
        Get default email content
        """
        lead_name = state["lead_name"]
        property_address = state["property_address"]
        
        return {
            "subject": f"Re: Your Property at {property_address}",
            "body": f"""Hi {lead_name},

I wanted to reach out regarding your property at {property_address}.

We're local real estate investors who can provide a quick, no-obligation cash offer. If you're interested in learning more, I'd be happy to schedule a brief call to discuss your situation.

Best regards,
Derek
Real Estate Solutions Team"""
        }
    
    def _format_user_message_as_email(self, state: RealEstateAgentState, message: str) -> Dict[str, str]:
        """
        Format a user-provided message as an email
        """
        property_address = state["property_address"]
        
        return {
            "subject": f"Re: Your Property Inquiry - {property_address}",
            "body": message
        }
    
    def _send_email(
        self, 
        to_email: str, 
        subject: str, 
        message: str, 
        state: RealEstateAgentState,
        threading_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Send email with proper threading
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.gmail_address
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add threading headers if available
            if threading_info:
                if threading_info.get('in_reply_to'):
                    msg['In-Reply-To'] = threading_info['in_reply_to']
                
                if threading_info.get('references'):
                    msg['References'] = threading_info['references']
            
            # Generate unique message ID
            message_id = make_msgid()
            msg['Message-ID'] = message_id
            
            # Add body
            msg.attach(MIMEText(message, 'plain'))
            
            # Send via Gmail SMTP
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.gmail_address, self.gmail_password)
            
            text = msg.as_string()
            server.sendmail(self.gmail_address, to_email, text)
            server.quit()
            
            # Log successful send
            add_communication_attempt(
                state,
                method="email",
                message=f"Subject: {subject}\n\n{message}",
                success=True,
                message_id=message_id
            )
            
            return {
                "success": True,
                "message_id": message_id,
                "to_email": to_email,
                "subject": subject
            }
            
        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            self.logger.error(error_msg)
            
            # Log failed attempt
            add_communication_attempt(
                state,
                method="email",
                message=f"Subject: {subject}\n\n{message}",
                success=False,
                error=error_msg
            )
            
            return {
                "success": False,
                "error": error_msg
            }
    
    def _get_threading_info(self, state: RealEstateAgentState) -> Dict[str, Any]:
        """
        Get email threading information for conversation continuity
        """
        conversation_id = state.get("conversation_id")
        if conversation_id and conversation_id in self.thread_info:
            return self.thread_info[conversation_id]
        
        return {}
    
    def _store_threading_info(self, state: RealEstateAgentState, message_id: str):
        """
        Store threading information for future emails
        """
        conversation_id = state.get("conversation_id")
        if conversation_id and message_id:
            if conversation_id not in self.thread_info:
                self.thread_info[conversation_id] = {
                    "references": [],
                    "in_reply_to": None
                }
            
            # Update threading info
            self.thread_info[conversation_id]["in_reply_to"] = message_id
            if message_id not in self.thread_info[conversation_id]["references"]:
                self.thread_info[conversation_id]["references"].append(message_id)
    
    def _handle_email_failure(self, state: RealEstateAgentState, reason: str) -> Dict[str, Any]:
        """
        Handle email sending failure
        """
        self.log_agent_action(state, "email_failed", {"reason": reason})
        
        # Mark email as failed
        state["email_failed"] = True
        state["last_error"] = f"Email failed: {reason}"
        
        return {
            "success": False,
            "action": "email_failed",
            "reason": reason,
            "next_agent": "supervisor",  # Let supervisor decide next steps
            "state_updates": {
                "email_failed": True,
                "last_error": f"Email failed: {reason}"
            }
        }
    
    def get_system_prompt(self, state: RealEstateAgentState) -> str:
        """
        System prompt for email agent
        """
        return f"""
        You are the Email Agent for a real estate outreach system.
        
        Lead: {state['lead_name']}
        Email: {state.get('lead_email', 'N/A')}
        Property: {state['property_address']}
        Property Type: {state['property_type']}
        Stage: {state['conversation_stage']}
        
        Your responsibilities:
        1. Send professional emails via Gmail
        2. Maintain email threading for conversation continuity
        3. Generate property-specific email content
        4. Handle email failures gracefully
        5. Serve as fallback when SMS fails
        
        Email Guidelines:
        - Professional but friendly tone
        - Clear subject lines
        - Proper email threading
        - Include opt-out options
        - Property-specific messaging
        
        Property-specific focus:
        - Fix & Flip: Cash offers, quick closing, any condition
        - Vacant Land: Simple process, hassle-free, consultation calls
        - Rentals: Work with existing leases, tenant handling
        """


def email_agent_node(state: RealEstateAgentState) -> Dict[str, Any]:
    """
    Node function for email agent in LangGraph
    """
    agent = EmailAgent()
    return agent.process_message(state)


def route_email_result(state: RealEstateAgentState) -> str:
    """
    Routing function for email agent results
    """
    last_action = state.get("next_action")
    
    if last_action in ["email_sent", "email_failed"]:
        return "supervisor"
    else:
        return "supervisor"


# Utility functions for email management
def get_email_stats(lead_id: str) -> Dict[str, Any]:
    """
    Get email statistics for a lead
    """
    import sqlite3
    
    conn = sqlite3.connect("agent_estate.db")
    try:
        # Get email message counts
        stats = conn.execute("""
            SELECT 
                COUNT(*) as total_emails,
                SUM(CASE WHEN ai_generated = 1 THEN 1 ELSE 0 END) as ai_emails,
                MAX(timestamp) as last_email
            FROM messages m
            JOIN conversations c ON m.conversation_id = c.id
            WHERE c.lead_id = ? AND m.method = 'email'
        """, (lead_id,)).fetchone()
        
        return {
            "total_emails": stats["total_emails"] or 0,
            "ai_generated": stats["ai_emails"] or 0,
            "last_email": stats["last_email"]
        }
        
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()


def validate_email_address(email: str) -> Dict[str, Any]:
    """
    Validate email address format
    """
    import re
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if re.match(pattern, email):
        return {
            "valid": True,
            "email": email.lower()
        }
    else:
        return {
            "valid": False,
            "reason": "Invalid email format",
            "email": email
        }
