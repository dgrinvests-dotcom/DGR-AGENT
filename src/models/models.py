from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime

class PropertyType(str, Enum):
    FIX_FLIP = "fix_flip"
    RENTAL = "rental"
    VACANT_LAND = "vacant_land"

class LeadStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    RESPONDED = "responded"
    QUALIFIED = "qualified"
    APPOINTMENT_SET = "appointment_set"
    NO_SHOW = "no_show"
    NOT_INTERESTED = "not_interested"
    OPTED_OUT = "opted_out"

class CampaignStatus(str, Enum):
    CREATED = "created"
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"

class ConversationStatus(str, Enum):
    ACTIVE = "active"
    WAITING_RESPONSE = "waiting_response"
    QUALIFIED = "qualified"
    APPOINTMENT_SET = "appointment_set"
    CLOSED = "closed"

class ContactMethod(str, Enum):
    SMS = "sms"
    EMAIL = "email"
    PHONE = "phone"

# Export all classes for easy importing
__all__ = [
    'PropertyType', 'LeadStatus', 'CampaignStatus', 'ConversationStatus', 
    'ContactMethod', 'Lead', 'Campaign', 'Conversation', 'ConversationMessage',
    'CampaignConfig', 'CampaignStats'
]

class Lead(BaseModel):
    id: Optional[str] = None
    first_name: str
    last_name: str
    phone: str
    email: Optional[str] = None
    property_address: str
    property_type: PropertyType
    status: LeadStatus = LeadStatus.NEW
    campaign_id: Optional[str] = None
    created_at: Optional[datetime] = None
    last_contact_date: Optional[datetime] = None
    next_follow_up_date: Optional[datetime] = None
    property_value: Optional[float] = None
    condition: Optional[str] = None
    notes: Optional[str] = None

class CampaignConfig(BaseModel):
    max_daily_contacts: int = 50
    follow_up_days: List[int] = [1, 3, 7, 14]
    target_response_rate: float = 15.0
    quiet_hours_start: str = "21:00"
    quiet_hours_end: str = "08:00"

class CampaignStats(BaseModel):
    total_leads: int = 0
    contacted_leads: int = 0
    responded_leads: int = 0
    appointments_set: int = 0
    response_rate: float = 0.0
    conversion_rate: float = 0.0

class Campaign(BaseModel):
    id: Optional[str] = None
    name: str
    property_type: PropertyType
    status: CampaignStatus = CampaignStatus.CREATED
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    config: CampaignConfig
    stats: Optional[CampaignStats] = None

class ConversationMessage(BaseModel):
    id: Optional[str] = None
    direction: str  # 'inbound' or 'outbound'
    content: str
    timestamp: datetime
    method: ContactMethod
    ai_generated: bool = False

class Conversation(BaseModel):
    id: Optional[str] = None
    lead_id: str
    messages: List[ConversationMessage] = []
    status: ConversationStatus = ConversationStatus.ACTIVE
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
