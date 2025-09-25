"""
Real Estate Agent State Schema for LangGraph
Defines the state structure for stateful conversations
"""

from typing import TypedDict, List, Optional, Literal, Dict, Any
from datetime import datetime
from langgraph.graph import MessagesState


class CommunicationAttempt(TypedDict):
    """Individual communication attempt record"""
    method: Literal["sms", "email"]
    timestamp: str
    message: str
    success: bool
    message_id: Optional[str]
    error: Optional[str]
    delivery_status: Optional[str]


class QualificationData(TypedDict):
    """Property qualification information"""
    # Fix & Flip specific
    occupancy_status: Optional[Literal["vacant", "rented", "owner_occupied"]]
    condition: Optional[str]
    repairs_needed: Optional[str]
    timeline: Optional[str]
    motivation: Optional[str]
    
    # Vacant Land specific
    acreage: Optional[str]
    road_access: Optional[bool]
    utilities: Optional[str]
    liens: Optional[str]
    price_expectation: Optional[str]
    
    # Long-Term Rental specific
    rental_status: Optional[Literal["rented", "vacant"]]
    rental_income: Optional[str]
    tenant_situation: Optional[str]
    lease_terms: Optional[str]
    
    # Common fields
    property_value: Optional[str]
    seller_motivation: Optional[str]
    urgency_level: Optional[Literal["low", "medium", "high"]]


class BookingDetails(TypedDict):
    """Appointment booking information"""
    appointment_id: Optional[str]
    scheduled_time: Optional[str]
    calendar_event_id: Optional[str]
    calendly_link: Optional[str]
    meeting_link: Optional[str]
    confirmation_sent: bool
    reminder_sent: bool


class ComplianceInfo(TypedDict):
    """Compliance tracking information"""
    dnc_checked: bool
    dnc_status: Optional[Literal["clean", "on_list"]]
    tcpa_compliant: bool
    quiet_hours_respected: bool
    opt_out_requested: bool
    consent_status: Optional[Literal["explicit", "implied", "none"]]
    last_compliance_check: Optional[str]


class RealEstateAgentState(MessagesState):
    """
    Complete state schema for Real Estate Agent conversations
    Extends MessagesState to include conversation history
    """
    
    # Lead Information
    lead_id: str
    lead_name: str
    lead_phone: Optional[str]
    lead_email: Optional[str]
    property_address: str
    property_type: Literal["fix_flip", "vacant_land", "long_term_rental"]
    property_county: Optional[str]
    property_city: Optional[str]
    property_state: Optional[str]
    
    # Communication State
    preferred_channel: Optional[Literal["sms", "email"]]
    communication_attempts: List[CommunicationAttempt]
    last_contact_method: Optional[str]
    last_contact_time: Optional[str]
    sms_failed: bool
    email_failed: bool
    total_messages_sent: int
    
    # Conversation Mode / Inbound Context
    conversation_mode: Optional[Literal["inbound_response", "outbound_campaign"]]
    incoming_message: Optional[str]
    
    # Conversation State
    conversation_stage: Literal[
        "initial", 
        "qualifying", 
        "interested", 
        "booking", 
        "completed", 
        "not_interested",
        "follow_up",
        "dormant"
    ]
    qualification_data: QualificationData
    booking_attempts: int
    objections_handled: List[str]
    user_communication_style: Optional[Literal["formal", "casual", "neutral"]]
    conversation_sentiment: Optional[Literal["positive", "neutral", "negative"]]
    
    # Campaign Context
    campaign_id: str
    campaign_name: Optional[str]
    agent_name: str  # Derek, etc.
    company_name: Optional[str]
    
    # Compliance Information
    compliance_info: ComplianceInfo
    
    # Booking Information
    calendly_link_sent: bool
    appointment_scheduled: bool
    booking_details: Optional[BookingDetails]
    follow_up_scheduled: bool
    no_show_count: int
    
    # Analytics & Tracking
    conversation_started_at: str
    last_updated_at: str
    total_conversation_time: Optional[int]  # in minutes
    response_time_avg: Optional[float]  # in seconds
    
    # Agent Routing
    current_agent: Optional[str]
    agent_history: List[str]
    next_action: Optional[str]
    
    # Error Handling
    last_error: Optional[str]
    retry_count: int
    
    # Custom Fields
    custom_data: Dict[str, Any]

    # UI Pass-through
    ui_message: Optional[str]


def create_initial_state(
    lead_id: str,
    lead_name: str,
    property_address: str,
    property_type: Literal["fix_flip", "vacant_land", "long_term_rental"],
    campaign_id: str,
    lead_phone: Optional[str] = None,
    lead_email: Optional[str] = None,
    agent_name: str = "Derek"
) -> RealEstateAgentState:
    """
    Create initial state for a new conversation
    """
    now = datetime.now().isoformat()
    
    return RealEstateAgentState(
        # Messages (from MessagesState)
        messages=[],
        
        # Lead Information
        lead_id=lead_id,
        lead_name=lead_name,
        lead_phone=lead_phone,
        lead_email=lead_email,
        property_address=property_address,
        property_type=property_type,
        property_county=None,
        property_city=None,
        property_state=None,
        
        # Communication State
        preferred_channel=None,
        communication_attempts=[],
        last_contact_method=None,
        last_contact_time=None,
        sms_failed=False,
        email_failed=False,
        total_messages_sent=0,
        
        # Conversation Mode / Inbound Context
        conversation_mode=None,
        incoming_message=None,
        
        # Conversation State
        conversation_stage="initial",
        qualification_data=QualificationData(
            occupancy_status=None,
            condition=None,
            repairs_needed=None,
            timeline=None,
            motivation=None,
            acreage=None,
            road_access=None,
            utilities=None,
            liens=None,
            price_expectation=None,
            rental_status=None,
            rental_income=None,
            tenant_situation=None,
            lease_terms=None,
            property_value=None,
            seller_motivation=None,
            urgency_level=None
        ),
        booking_attempts=0,
        objections_handled=[],
        user_communication_style=None,
        conversation_sentiment=None,
        
        # Campaign Context
        campaign_id=campaign_id,
        campaign_name=None,
        agent_name=agent_name,
        company_name="Real Estate Solutions Team",
        
        # Compliance Information
        compliance_info=ComplianceInfo(
            dnc_checked=False,
            dnc_status=None,
            tcpa_compliant=False,
            quiet_hours_respected=False,
            opt_out_requested=False,
            consent_status=None,
            last_compliance_check=None
        ),
        
        # Booking Information
        calendly_link_sent=False,
        appointment_scheduled=False,
        booking_details=None,
        follow_up_scheduled=False,
        no_show_count=0,
        
        # Analytics & Tracking
        conversation_started_at=now,
        last_updated_at=now,
        total_conversation_time=None,
        response_time_avg=None,
        
        # Agent Routing
        current_agent=None,
        agent_history=[],
        next_action=None,
        
        # Error Handling
        last_error=None,
        retry_count=0,
        
        # Custom Fields
        custom_data={},
        
        # UI Pass-through
        ui_message=None
    )


def update_state_timestamp(state: RealEstateAgentState) -> RealEstateAgentState:
    """Update the last_updated_at timestamp"""
    state["last_updated_at"] = datetime.now().isoformat()
    return state


def add_communication_attempt(
    state: RealEstateAgentState,
    method: Literal["sms", "email"],
    message: str,
    success: bool,
    message_id: Optional[str] = None,
    error: Optional[str] = None
) -> RealEstateAgentState:
    """Add a communication attempt to the state"""
    
    attempt = CommunicationAttempt(
        method=method,
        timestamp=datetime.now().isoformat(),
        message=message,
        success=success,
        message_id=message_id,
        error=error,
        delivery_status=None
    )
    
    state["communication_attempts"].append(attempt)
    state["last_contact_method"] = method
    state["last_contact_time"] = attempt["timestamp"]
    state["total_messages_sent"] += 1
    
    if not success:
        if method == "sms":
            state["sms_failed"] = True
        else:
            state["email_failed"] = True
    
    return update_state_timestamp(state)


def update_qualification_data(
    state: RealEstateAgentState,
    field: str,
    value: Any
) -> RealEstateAgentState:
    """Update qualification data field"""
    state["qualification_data"][field] = value
    return update_state_timestamp(state)


def advance_conversation_stage(
    state: RealEstateAgentState,
    new_stage: Literal[
        "initial", "qualifying", "interested", "booking", 
        "completed", "not_interested", "follow_up", "dormant"
    ]
) -> RealEstateAgentState:
    """Advance the conversation to a new stage"""
    state["conversation_stage"] = new_stage
    return update_state_timestamp(state)
