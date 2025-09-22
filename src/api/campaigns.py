from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid
from ..campaigns.campaign_manager import CampaignManager
from ..models import Campaign, CampaignStatus, PropertyType

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])

class CampaignCreate(BaseModel):
    name: str
    property_type: PropertyType
    config: Dict[str, Any]

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    property_type: Optional[PropertyType] = None
    config: Optional[Dict[str, Any]] = None

# Mock data storage (replace with actual database)
campaigns_db = {}

@router.get("/", response_model=List[Dict[str, Any]])
async def get_campaigns():
    """Get all campaigns"""
    try:
        # TODO: Replace with actual database query
        return [
            {
                "id": "1",
                "name": "Fix & Flip Q1 2024",
                "property_type": "fix_flip",
                "status": "active",
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z",
                "config": {
                    "max_daily_contacts": 50,
                    "follow_up_days": [1, 3, 7, 14],
                    "target_response_rate": 15.0,
                    "quiet_hours_start": "21:00",
                    "quiet_hours_end": "08:00"
                },
                "stats": {
                    "total_leads": 75,
                    "contacted_leads": 60,
                    "responded_leads": 12,
                    "appointments_set": 3,
                    "response_rate": 20.0,
                    "conversion_rate": 5.0
                }
            },
            {
                "id": "2",
                "name": "Vacant Land Outreach",
                "property_type": "vacant_land",
                "status": "paused",
                "created_at": "2024-01-10T14:30:00Z",
                "updated_at": "2024-01-20T09:15:00Z",
                "config": {
                    "max_daily_contacts": 30,
                    "follow_up_days": [1, 3, 7],
                    "target_response_rate": 12.0,
                    "quiet_hours_start": "21:00",
                    "quiet_hours_end": "08:00"
                },
                "stats": {
                    "total_leads": 45,
                    "contacted_leads": 35,
                    "responded_leads": 8,
                    "appointments_set": 2,
                    "response_rate": 22.9,
                    "conversion_rate": 5.7
                }
            },
            {
                "id": "3",
                "name": "Rental Properties",
                "property_type": "rental",
                "status": "created",
                "created_at": "2024-01-25T16:45:00Z",
                "updated_at": "2024-01-25T16:45:00Z",
                "config": {
                    "max_daily_contacts": 40,
                    "follow_up_days": [1, 3, 7, 14, 30],
                    "target_response_rate": 18.0,
                    "quiet_hours_start": "21:00",
                    "quiet_hours_end": "08:00"
                },
                "stats": {
                    "total_leads": 30,
                    "contacted_leads": 0,
                    "responded_leads": 0,
                    "appointments_set": 0,
                    "response_rate": 0.0,
                    "conversion_rate": 0.0
                }
            }
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{campaign_id}")
async def get_campaign(campaign_id: str):
    """Get a specific campaign"""
    try:
        # TODO: Replace with actual database query
        campaigns = await get_campaigns()
        campaign = next((c for c in campaigns if c["id"] == campaign_id), None)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return campaign
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def create_campaign(campaign: CampaignCreate):
    """Create a new campaign"""
    try:
        campaign_id = str(uuid.uuid4())
        new_campaign = {
            "id": campaign_id,
            "name": campaign.name,
            "property_type": campaign.property_type,
            "status": "created",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "config": campaign.config,
            "stats": {
                "total_leads": 0,
                "contacted_leads": 0,
                "responded_leads": 0,
                "appointments_set": 0,
                "response_rate": 0.0,
                "conversion_rate": 0.0
            }
        }
        
        # TODO: Save to actual database
        campaigns_db[campaign_id] = new_campaign
        
        return new_campaign
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{campaign_id}")
async def update_campaign(campaign_id: str, campaign_update: CampaignUpdate):
    """Update a campaign"""
    try:
        # TODO: Replace with actual database query and update
        campaign = await get_campaign(campaign_id)
        
        if campaign_update.name is not None:
            campaign["name"] = campaign_update.name
        if campaign_update.property_type is not None:
            campaign["property_type"] = campaign_update.property_type
        if campaign_update.config is not None:
            campaign["config"].update(campaign_update.config)
        
        campaign["updated_at"] = datetime.utcnow().isoformat() + "Z"
        
        return campaign
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: str):
    """Delete a campaign"""
    try:
        # TODO: Replace with actual database deletion
        campaign = await get_campaign(campaign_id)
        # In real implementation, also delete associated leads and conversations
        return {"message": "Campaign deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{campaign_id}/start")
async def start_campaign(campaign_id: str):
    """Start a campaign"""
    try:
        campaign = await get_campaign(campaign_id)
        if campaign["status"] not in ["created", "paused"]:
            raise HTTPException(status_code=400, detail="Campaign cannot be started from current status")
        
        # TODO: Implement actual campaign start logic
        campaign["status"] = "active"
        campaign["updated_at"] = datetime.utcnow().isoformat() + "Z"
        
        return {"success": True, "message": "Campaign started successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{campaign_id}/pause")
async def pause_campaign(campaign_id: str):
    """Pause a campaign"""
    try:
        campaign = await get_campaign(campaign_id)
        if campaign["status"] != "active":
            raise HTTPException(status_code=400, detail="Only active campaigns can be paused")
        
        # TODO: Implement actual campaign pause logic
        campaign["status"] = "paused"
        campaign["updated_at"] = datetime.utcnow().isoformat() + "Z"
        
        return {"success": True, "message": "Campaign paused successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{campaign_id}/stop")
async def stop_campaign(campaign_id: str):
    """Stop a campaign"""
    try:
        campaign = await get_campaign(campaign_id)
        if campaign["status"] in ["stopped", "completed"]:
            raise HTTPException(status_code=400, detail="Campaign is already stopped")
        
        # TODO: Implement actual campaign stop logic
        campaign["status"] = "stopped"
        campaign["updated_at"] = datetime.utcnow().isoformat() + "Z"
        
        return {"success": True, "message": "Campaign stopped successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
