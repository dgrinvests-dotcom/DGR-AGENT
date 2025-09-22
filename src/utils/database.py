import os
import sqlite3
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from models.lead import Lead, LeadStatus, PropertyType

class DatabaseManager:
    def __init__(self):
        self.db_path = os.getenv("DATABASE_URL", "sqlite:///./leads.db").replace("sqlite:///", "")
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create leads table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS leads (
                    id TEXT PRIMARY KEY,
                    first_name TEXT,
                    last_name TEXT,
                    phone TEXT UNIQUE NOT NULL,
                    email TEXT,
                    property_address TEXT NOT NULL,
                    property_type TEXT NOT NULL,
                    property_value REAL,
                    property_condition TEXT,
                    source TEXT NOT NULL,
                    source_data TEXT,
                    campaign_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    conversation_history TEXT,
                    last_contact_date TEXT,
                    next_follow_up_date TEXT,
                    qualification_data TEXT,
                    interest_level INTEGER,
                    opted_out BOOLEAN DEFAULT FALSE,
                    dnc_checked BOOLEAN DEFAULT FALSE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Create campaigns table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS campaigns (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    property_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    config TEXT
                )
            """)
            
            # Create compliance_logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS compliance_logs (
                    id TEXT PRIMARY KEY,
                    phone_number TEXT NOT NULL,
                    method TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    reason TEXT,
                    compliance_data TEXT,
                    timestamp TEXT NOT NULL
                )
            """)
            
            conn.commit()
    
    async def create_lead(self, lead: Lead) -> str:
        """Create a new lead"""
        if not lead.id:
            lead.id = str(uuid.uuid4())
        
        lead.created_at = datetime.utcnow()
        lead.updated_at = datetime.utcnow()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO leads (
                    id, first_name, last_name, phone, email,
                    property_address, property_type, property_value, property_condition,
                    source, source_data, campaign_id, status,
                    conversation_history, last_contact_date, next_follow_up_date,
                    qualification_data, interest_level, opted_out, dnc_checked,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                lead.id, lead.first_name, lead.last_name, lead.phone, lead.email,
                lead.property_address, lead.property_type.value, lead.property_value, lead.property_condition,
                lead.source, json.dumps(lead.source_data), lead.campaign_id, lead.status.value,
                json.dumps(lead.conversation_history), 
                lead.last_contact_date.isoformat() if lead.last_contact_date else None,
                lead.next_follow_up_date.isoformat() if lead.next_follow_up_date else None,
                json.dumps(lead.qualification_data), lead.interest_level, lead.opted_out, lead.dnc_checked,
                lead.created_at.isoformat(), lead.updated_at.isoformat()
            ))
            
            conn.commit()
        
        return lead.id
    
    async def get_lead_by_id(self, lead_id: str) -> Optional[Lead]:
        """Get lead by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_lead(row)
        
        return None
    
    async def get_lead_by_phone(self, phone: str) -> Optional[Lead]:
        """Get lead by phone number"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM leads WHERE phone = ?", (phone,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_lead(row)
        
        return None
    
    async def update_lead(self, lead: Lead) -> bool:
        """Update existing lead"""
        lead.updated_at = datetime.utcnow()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE leads SET
                    first_name = ?, last_name = ?, phone = ?, email = ?,
                    property_address = ?, property_type = ?, property_value = ?, property_condition = ?,
                    source = ?, source_data = ?, campaign_id = ?, status = ?,
                    conversation_history = ?, last_contact_date = ?, next_follow_up_date = ?,
                    qualification_data = ?, interest_level = ?, opted_out = ?, dnc_checked = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                lead.first_name, lead.last_name, lead.phone, lead.email,
                lead.property_address, lead.property_type.value, lead.property_value, lead.property_condition,
                lead.source, json.dumps(lead.source_data), lead.campaign_id, lead.status.value,
                json.dumps(lead.conversation_history),
                lead.last_contact_date.isoformat() if lead.last_contact_date else None,
                lead.next_follow_up_date.isoformat() if lead.next_follow_up_date else None,
                json.dumps(lead.qualification_data), lead.interest_level, lead.opted_out, lead.dnc_checked,
                lead.updated_at.isoformat(), lead.id
            ))
            
            conn.commit()
            return cursor.rowcount > 0
    
    async def get_leads_by_campaign(self, campaign_id: str) -> List[Lead]:
        """Get all leads for a campaign"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM leads WHERE campaign_id = ?", (campaign_id,))
            rows = cursor.fetchall()
            
            return [self._row_to_lead(row) for row in rows]
    
    async def get_leads_for_follow_up(self) -> List[Lead]:
        """Get leads that need follow-up"""
        now = datetime.utcnow().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM leads 
                WHERE next_follow_up_date <= ? 
                AND status NOT IN ('appointment_set', 'not_interested', 'do_not_call')
                AND opted_out = FALSE
            """, (now,))
            
            rows = cursor.fetchall()
            return [self._row_to_lead(row) for row in rows]
    
    async def get_campaign_stats(self, campaign_id: str) -> Dict[str, Any]:
        """Get campaign statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total leads
            cursor.execute("SELECT COUNT(*) FROM leads WHERE campaign_id = ?", (campaign_id,))
            total_leads = cursor.fetchone()[0]
            
            # Leads by status
            cursor.execute("""
                SELECT status, COUNT(*) 
                FROM leads 
                WHERE campaign_id = ? 
                GROUP BY status
            """, (campaign_id,))
            
            status_counts = dict(cursor.fetchall())
            
            # Response rate
            cursor.execute("""
                SELECT COUNT(*) FROM leads 
                WHERE campaign_id = ? 
                AND json_array_length(conversation_history) > 0
            """, (campaign_id,))
            
            responded = cursor.fetchone()[0]
            response_rate = (responded / total_leads * 100) if total_leads > 0 else 0
            
            return {
                "total_leads": total_leads,
                "status_breakdown": status_counts,
                "response_rate": response_rate,
                "appointments_set": status_counts.get("appointment_set", 0)
            }
    
    def _row_to_lead(self, row: sqlite3.Row) -> Lead:
        """Convert database row to Lead object"""
        return Lead(
            id=row["id"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            phone=row["phone"],
            email=row["email"],
            property_address=row["property_address"],
            property_type=PropertyType(row["property_type"]),
            property_value=row["property_value"],
            property_condition=row["property_condition"],
            source=row["source"],
            source_data=json.loads(row["source_data"]) if row["source_data"] else {},
            campaign_id=row["campaign_id"],
            status=LeadStatus(row["status"]),
            conversation_history=json.loads(row["conversation_history"]) if row["conversation_history"] else [],
            last_contact_date=datetime.fromisoformat(row["last_contact_date"]) if row["last_contact_date"] else None,
            next_follow_up_date=datetime.fromisoformat(row["next_follow_up_date"]) if row["next_follow_up_date"] else None,
            qualification_data=json.loads(row["qualification_data"]) if row["qualification_data"] else {},
            interest_level=row["interest_level"],
            opted_out=bool(row["opted_out"]),
            dnc_checked=bool(row["dnc_checked"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"])
        )
    
    async def log_compliance_event(self, phone_number: str, method: str, success: bool, reason: str = None, compliance_data: Dict[str, Any] = None):
        """Log compliance event"""
        log_id = str(uuid.uuid4())
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO compliance_logs (id, phone_number, method, success, reason, compliance_data, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id, phone_number, method, success, reason,
                json.dumps(compliance_data) if compliance_data else None,
                datetime.utcnow().isoformat()
            ))
            
            conn.commit()
        
        return log_id
