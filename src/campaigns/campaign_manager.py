import os
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid
import json

from models.lead import Lead, LeadStatus, PropertyType, CampaignTemplate
from utils.database import DatabaseManager
from compliance.compliance_checker import ComplianceChecker
from integrations.telnyx_integration import TelnyxIntegration
from integrations.google_meet_integration import GoogleMeetIntegration
from integrations.gmail_integration import GmailIntegration
from agents.conversation_agent import ConversationAgent

class CampaignManager:
    def __init__(self):
        self.db = DatabaseManager()
        self.compliance = ComplianceChecker()
        self.telnyx = TelnyxIntegration()
        self.google_meet = GoogleMeetIntegration()
        self.gmail = GmailIntegration()
        self.conversation_agent = ConversationAgent()
        
        # Load campaign templates
        self.templates = self._load_campaign_templates()
        
        # Active campaigns tracking
        self.active_campaigns: Dict[str, Dict[str, Any]] = {}
    
    async def create_campaign(self, name: str, property_type: PropertyType, config: Dict[str, Any] = None) -> str:
        """Create a new campaign"""
        campaign_id = str(uuid.uuid4())
        
        campaign_data = {
            "id": campaign_id,
            "name": name,
            "property_type": property_type.value,
            "status": "created",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "config": json.dumps(config or {})
        }
        
        # Save to database
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO campaigns (id, name, property_type, status, created_at, updated_at, config)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                campaign_id, name, property_type.value, "created",
                campaign_data["created_at"], campaign_data["updated_at"], campaign_data["config"]
            ))
            conn.commit()
        
        return campaign_id
    
    async def start_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Start a campaign and begin outreach"""
        
        # Get campaign leads
        leads = await self.db.get_leads_by_campaign(campaign_id)
        
        if not leads:
            return {"error": "No leads found for campaign"}
        
        # Update campaign status
        await self._update_campaign_status(campaign_id, "active")
        
        # Start outreach process
        self.active_campaigns[campaign_id] = {
            "status": "active",
            "started_at": datetime.utcnow(),
            "leads_processed": 0,
            "leads_total": len(leads)
        }
        
        # Process leads in batches to respect rate limits
        results = await self._process_campaign_leads(campaign_id, leads)
        
        return {
            "campaign_id": campaign_id,
            "status": "started",
            "leads_processed": results["processed"],
            "leads_total": len(leads),
            "errors": results["errors"]
        }
    
    async def _process_campaign_leads(self, campaign_id: str, leads: List[Lead]) -> Dict[str, Any]:
        """Process leads for a campaign with rate limiting and compliance"""
        processed = 0
        errors = []
        
        max_daily_contacts = int(os.getenv("MAX_DAILY_CONTACTS", "100"))
        delay_between_messages = 30  # seconds
        
        for lead in leads:
            try:
                # Check if we've hit daily limit
                if processed >= max_daily_contacts:
                    break
                
                # Check compliance
                if not self.compliance.can_contact(lead.phone):
                    self.compliance.log_contact_attempt(
                        lead.phone, "sms", False, "compliance_blocked"
                    )
                    continue
                
                # Generate initial message
                initial_message = await self.conversation_agent.send_initial_message(lead)
                
                # Send message via Telnyx
                success = await self.telnyx.send_sms(lead.phone, initial_message)
                
                if success:
                    # Update lead status
                    lead.status = LeadStatus.CONTACTED
                    lead.last_contact_date = datetime.utcnow()
                    await self.db.update_lead(lead)
                    
                    processed += 1
                    
                    # Log compliance
                    self.compliance.log_contact_attempt(
                        lead.phone, "sms", True, "initial_outreach"
                    )
                else:
                    errors.append(f"Failed to send message to {lead.phone}")
                
                # Rate limiting delay
                await asyncio.sleep(delay_between_messages)
                
            except Exception as e:
                errors.append(f"Error processing lead {lead.id}: {str(e)}")
        
        # Update campaign tracking
        if campaign_id in self.active_campaigns:
            self.active_campaigns[campaign_id]["leads_processed"] = processed
        
        return {"processed": processed, "errors": errors}
    
    async def get_campaign_status(self, campaign_id: str) -> Dict[str, Any]:
        """Get detailed campaign status"""
        
        # Get campaign stats from database
        stats = await self.db.get_campaign_stats(campaign_id)
        
        # Add real-time tracking if campaign is active
        if campaign_id in self.active_campaigns:
            active_data = self.active_campaigns[campaign_id]
            stats.update({
                "active_status": active_data["status"],
                "started_at": active_data["started_at"].isoformat(),
                "leads_processed_today": active_data["leads_processed"]
            })
        
        return stats
    
    async def pause_campaign(self, campaign_id: str) -> bool:
        """Pause an active campaign"""
        if campaign_id in self.active_campaigns:
            self.active_campaigns[campaign_id]["status"] = "paused"
        
        return await self._update_campaign_status(campaign_id, "paused")
    
    async def resume_campaign(self, campaign_id: str) -> bool:
        """Resume a paused campaign"""
        if campaign_id in self.active_campaigns:
            self.active_campaigns[campaign_id]["status"] = "active"
        
        return await self._update_campaign_status(campaign_id, "active")
    
    async def stop_campaign(self, campaign_id: str) -> bool:
        """Stop a campaign completely"""
        if campaign_id in self.active_campaigns:
            del self.active_campaigns[campaign_id]
        
        return await self._update_campaign_status(campaign_id, "stopped")
    
    async def schedule_follow_ups(self) -> Dict[str, Any]:
        """Process scheduled follow-ups"""
        leads_for_follow_up = await self.db.get_leads_for_follow_up()
        
        processed = 0
        errors = []
        
        for lead in leads_for_follow_up:
            try:
                # Check compliance
                if not self.compliance.can_contact(lead.phone):
                    continue
                
                # Generate follow-up message based on lead status and history
                follow_up_message = await self._generate_follow_up_message(lead)
                
                # Send message
                success = await self.telnyx.send_sms(lead.phone, follow_up_message)
                
                if success:
                    # Update lead with new follow-up date
                    lead.last_contact_date = datetime.utcnow()
                    lead.next_follow_up_date = self._calculate_next_follow_up(lead)
                    await self.db.update_lead(lead)
                    
                    processed += 1
                else:
                    errors.append(f"Failed to send follow-up to {lead.phone}")
                
            except Exception as e:
                errors.append(f"Error processing follow-up for lead {lead.id}: {str(e)}")
        
        return {"processed": processed, "errors": errors}
    
    async def _generate_follow_up_message(self, lead: Lead) -> str:
        """Generate appropriate follow-up message based on lead status"""
        
        template = self.templates.get(lead.property_type, {})
        follow_up_sequences = template.get("follow_up_sequences", {})
        
        # Get appropriate follow-up sequence based on lead status
        if lead.status == LeadStatus.NO_SHOW:
            messages = follow_up_sequences.get("no_show", [
                "Hi {name}, I noticed we missed our scheduled call. Are you still interested in discussing your property? Reply YES to reschedule."
            ])
        elif lead.status == LeadStatus.INTERESTED:
            messages = follow_up_sequences.get("interested", [
                "Hi {name}, following up on your property at {address}. When would be a good time for a quick call to discuss your options?"
            ])
        else:
            messages = follow_up_sequences.get("general", [
                "Hi {name}, just checking back about your property. Any updates on your timeline for selling?"
            ])
        
        # Select message based on follow-up count
        follow_up_count = len([msg for msg in lead.conversation_history if msg.get("direction") == "outbound"])
        message_index = min(follow_up_count - 1, len(messages) - 1)
        
        message = messages[message_index]
        
        # Personalize message
        return message.format(
            name=lead.first_name or "there",
            address=lead.property_address
        )
    
    def _calculate_next_follow_up(self, lead: Lead) -> datetime:
        """Calculate next follow-up date based on lead status and history"""
        
        follow_up_intervals = {
            LeadStatus.CONTACTED: 3,      # 3 days
            LeadStatus.INTERESTED: 7,     # 1 week
            LeadStatus.NO_SHOW: 1,        # 1 day
            LeadStatus.QUALIFIED: 14      # 2 weeks
        }
        
        days = follow_up_intervals.get(lead.status, 7)
        return datetime.utcnow() + timedelta(days=days)
    
    async def _update_campaign_status(self, campaign_id: str, status: str) -> bool:
        """Update campaign status in database"""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE campaigns 
                SET status = ?, updated_at = ?
                WHERE id = ?
            """, (status, datetime.utcnow().isoformat(), campaign_id))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def _load_campaign_templates(self) -> Dict[PropertyType, CampaignTemplate]:
        """Load campaign templates for different property types"""
        
        # These would be loaded from your Google Docs content
        # For now, providing basic templates
        
        templates = {
            PropertyType.FIX_FLIP: {
                "initial_message": "Hi {name}! I saw your property at {address}. I buy houses for cash and can close quickly. Are you interested in a no-obligation offer? Text STOP to opt out.",
                "follow_up_sequences": {
                    "interested": [
                        "Great! What condition is the property in? Any major repairs needed?",
                        "Thanks for the info. What's your timeline for selling?",
                        "Perfect. I'd like to schedule a quick call to discuss your options. When works best for you?"
                    ],
                    "no_show": [
                        "Hi {name}, we missed our call. Still interested in getting an offer? Reply YES to reschedule."
                    ],
                    "general": [
                        "Hi {name}, following up about your property. Any updates on your selling timeline?",
                        "Just checking in one more time about {address}. Let me know if you'd like to discuss options."
                    ]
                }
            },
            PropertyType.RENTAL: {
                "initial_message": "Hi {name}! I'm interested in your rental property at {address}. I buy investment properties for cash. Would you consider an offer? Text STOP to opt out.",
                "follow_up_sequences": {
                    "interested": [
                        "Excellent! Is the property currently rented? What's the monthly income?",
                        "Thanks. Are you dealing with any tenant or management issues?",
                        "I'd love to discuss how I can help. When's a good time for a brief call?"
                    ]
                }
            },
            PropertyType.VACANT_LAND: {
                "initial_message": "Hi {name}! I buy vacant land for cash and can close quickly. Interested in an offer for your property at {address}? Text STOP to opt out.",
                "follow_up_sequences": {
                    "interested": [
                        "Great! How many acres is the land?",
                        "What's the zoning designation? Any development restrictions?",
                        "Perfect. Let's schedule a call to discuss your options. When works for you?"
                    ]
                }
            }
        }
        
        return templates
    
    async def handle_no_shows(self) -> Dict[str, Any]:
        """Check for no-shows and update lead status"""
        from integrations.calendly_integration import CalendlyIntegration
        
        calendly = CalendlyIntegration()
        no_shows = await calendly.check_no_shows()
        
        updated_leads = 0
        
        for no_show in no_shows:
            phone = no_show.get("phone")
            if phone:
                lead = await self.db.get_lead_by_phone(phone)
                if lead:
                    lead.status = LeadStatus.NO_SHOW
                    lead.next_follow_up_date = datetime.utcnow() + timedelta(hours=24)
                    await self.db.update_lead(lead)
                    updated_leads += 1
        
        return {"no_shows_processed": len(no_shows), "leads_updated": updated_leads}
