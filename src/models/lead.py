from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class PropertyType(str, Enum):
    FIX_FLIP = "fix_flip"
    RENTAL = "rental"
    VACANT_LAND = "vacant_land"

class LeadStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    INTERESTED = "interested"
    APPOINTMENT_SET = "appointment_set"
    NO_SHOW = "no_show"
    NOT_INTERESTED = "not_interested"
    DNC = "do_not_call"

class ContactMethod(str, Enum):
    SMS = "sms"
    EMAIL = "email"
    PHONE = "phone"

class Lead(BaseModel):
    id: Optional[str] = None
    
    # Contact Information
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: str
    email: Optional[str] = None
    
    # Property Information
    property_address: str
    property_type: PropertyType
    property_value: Optional[float] = None
    property_condition: Optional[str] = None
    
    # Lead Source
    source: str  # propwire, skiptrace, etc.
    source_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Campaign Information
    campaign_id: str
    status: LeadStatus = LeadStatus.NEW
    
    # Conversation History
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    last_contact_date: Optional[datetime] = None
    next_follow_up_date: Optional[datetime] = None
    
    # Qualification Data
    qualification_data: Dict[str, Any] = Field(default_factory=dict)
    interest_level: Optional[int] = Field(None, ge=1, le=10)
    
    # Compliance
    opted_out: bool = False
    dnc_checked: bool = False
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True

class ConversationMessage(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    direction: str  # "inbound" or "outbound"
    method: ContactMethod
    content: str
    ai_response: Optional[str] = None
    intent_detected: Optional[str] = None
    
class QualificationQuestion(BaseModel):
    question_id: str
    question_text: str
    property_type: PropertyType
    required: bool = True
    answer_type: str  # "text", "number", "boolean", "choice"
    choices: Optional[List[str]] = None

class CampaignTemplate(BaseModel):
    id: str
    name: str
    property_type: PropertyType
    initial_message: str
    qualification_questions: List[QualificationQuestion]
    follow_up_sequences: Dict[str, List[str]]  # status -> messages
    compliance_settings: Dict[str, Any]
