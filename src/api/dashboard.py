from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import asyncio
from ..campaigns.campaign_manager import CampaignManager
from ..leads.lead_processor import LeadProcessor
from ..integrations import TelnyxIntegration, GoogleMeetIntegration, GmailIntegration
import openai
import os

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/stats")
async def get_dashboard_stats() -> Dict[str, Any]:
    """Get dashboard statistics"""
    try:
        # TODO: Implement actual database queries
        # For now, return mock data
        return {
            "active_campaigns": 3,
            "total_leads": 150,
            "active_conversations": 12,
            "appointments_today": 2,
            "response_rate": 18.5,
            "conversion_rate": 12.3
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/integrations")
async def get_integration_status() -> Dict[str, bool]:
    """Check integration status for all services"""
    status = {
        "telnyx": False,
        "google_meet": False,
        "gmail": False,
        "openai": False
    }
    
    try:
        # Check Telnyx
        if os.getenv("TELNYX_API_KEY"):
            try:
                telnyx = TelnyxIntegration()
                # Simple check - if we can initialize without error, consider it connected
                status["telnyx"] = True
            except:
                pass
        
        # Check Google Meet
        if os.getenv("GOOGLE_CREDENTIALS_FILE"):
            try:
                google_meet = GoogleMeetIntegration()
                status["google_meet"] = True
            except:
                pass
        
        # Check Gmail
        if os.getenv("GMAIL_ADDRESS") and os.getenv("GMAIL_APP_PASSWORD"):
            try:
                gmail = GmailIntegration()
                status["gmail"] = True
            except:
                pass
        
        # Check OpenAI
        if os.getenv("OPENAI_API_KEY"):
            try:
                openai.api_key = os.getenv("OPENAI_API_KEY")
                status["openai"] = True
            except:
                pass
                
    except Exception as e:
        # Return partial status even if some checks fail
        pass
    
    return status
