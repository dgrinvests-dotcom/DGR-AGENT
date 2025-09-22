from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import uuid
from datetime import datetime
import pandas as pd
import io
from ..leads.lead_processor import LeadProcessor
from ..models import Lead, LeadStatus, PropertyType

router = APIRouter(prefix="/api/leads", tags=["leads"])

class LeadCreate(BaseModel):
    first_name: str
    last_name: str
    phone: str
    email: Optional[str] = None
    property_address: str
    property_type: PropertyType
    campaign_id: Optional[str] = None
    property_value: Optional[float] = None
    condition: Optional[str] = None
    notes: Optional[str] = None

class LeadUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    property_address: Optional[str] = None
    property_type: Optional[PropertyType] = None
    status: Optional[LeadStatus] = None
    campaign_id: Optional[str] = None
    property_value: Optional[float] = None
    condition: Optional[str] = None
    notes: Optional[str] = None

# Mock data storage (replace with actual database)
leads_db = {}

@router.get("/")
async def get_leads(
    campaign_id: Optional[str] = None,
    status: Optional[str] = None,
    property_type: Optional[str] = None,
    page: int = 1,
    limit: int = 25
):
    """Get leads with optional filtering and pagination"""
    try:
        # TODO: Replace with actual database query
        mock_leads = [
            {
                "id": "1",
                "first_name": "John",
                "last_name": "Smith",
                "phone": "+1234567890",
                "email": "john.smith@email.com",
                "property_address": "123 Main St, Anytown, ST 12345",
                "property_type": "fix_flip",
                "status": "contacted",
                "campaign_id": "1",
                "created_at": "2024-01-15T10:30:00Z",
                "last_contact_date": "2024-01-15T10:30:00Z",
                "next_follow_up_date": "2024-01-18T10:30:00Z",
                "property_value": 150000,
                "condition": "Needs renovation",
                "notes": "Interested in quick sale"
            },
            {
                "id": "2",
                "first_name": "Sarah",
                "last_name": "Johnson",
                "phone": "+1234567891",
                "email": "sarah.j@email.com",
                "property_address": "456 Oak Ave, Somewhere, ST 12346",
                "property_type": "vacant_land",
                "status": "responded",
                "campaign_id": "2",
                "created_at": "2024-01-16T14:20:00Z",
                "last_contact_date": "2024-01-16T14:20:00Z",
                "next_follow_up_date": None,
                "property_value": 75000,
                "condition": "Vacant lot",
                "notes": "Wants to sell within 3 months"
            },
            {
                "id": "3",
                "first_name": "Mike",
                "last_name": "Davis",
                "phone": "+1234567892",
                "email": None,
                "property_address": "789 Pine St, Elsewhere, ST 12347",
                "property_type": "rental",
                "status": "new",
                "campaign_id": "3",
                "created_at": "2024-01-17T09:15:00Z",
                "last_contact_date": None,
                "next_follow_up_date": "2024-01-17T09:15:00Z",
                "property_value": 200000,
                "condition": "Good condition",
                "notes": "Inherited property"
            }
        ]
        
        # Apply filters
        filtered_leads = mock_leads
        if campaign_id:
            filtered_leads = [l for l in filtered_leads if l.get("campaign_id") == campaign_id]
        if status:
            filtered_leads = [l for l in filtered_leads if l.get("status") == status]
        if property_type:
            filtered_leads = [l for l in filtered_leads if l.get("property_type") == property_type]
        
        # Apply pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_leads = filtered_leads[start_idx:end_idx]
        
        return {
            "leads": paginated_leads,
            "total": len(filtered_leads)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{lead_id}")
async def get_lead(lead_id: str):
    """Get a specific lead"""
    try:
        # TODO: Replace with actual database query
        leads_response = await get_leads()
        lead = next((l for l in leads_response["leads"] if l["id"] == lead_id), None)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        return lead
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def create_lead(lead: LeadCreate):
    """Create a new lead"""
    try:
        lead_id = str(uuid.uuid4())
        new_lead = {
            "id": lead_id,
            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "phone": lead.phone,
            "email": lead.email,
            "property_address": lead.property_address,
            "property_type": lead.property_type,
            "status": "new",
            "campaign_id": lead.campaign_id,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "last_contact_date": None,
            "next_follow_up_date": datetime.utcnow().isoformat() + "Z",
            "property_value": lead.property_value,
            "condition": lead.condition,
            "notes": lead.notes
        }
        
        # TODO: Save to actual database
        leads_db[lead_id] = new_lead
        
        return new_lead
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{lead_id}")
async def update_lead(lead_id: str, lead_update: LeadUpdate):
    """Update a lead"""
    try:
        # TODO: Replace with actual database query and update
        lead = await get_lead(lead_id)
        
        update_data = lead_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                lead[key] = value
        
        return lead
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{lead_id}")
async def delete_lead(lead_id: str):
    """Delete a lead"""
    try:
        # TODO: Replace with actual database deletion
        lead = await get_lead(lead_id)
        return {"message": "Lead deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import")
async def import_leads(
    file: UploadFile = File(...),
    campaign_id: str = Form(...)
):
    """Import leads from CSV or Excel file"""
    try:
        if not file.filename.endswith(('.csv', '.xlsx')):
            raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")
        
        # Read file content
        content = await file.read()
        
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(content.decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(content))
        
        # TODO: Implement actual lead import logic using LeadProcessor
        imported = 0
        skipped = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # Basic validation and import logic
                if pd.isna(row.get('first_name')) or pd.isna(row.get('phone')):
                    skipped += 1
                    continue
                
                # Create lead from row data
                lead_data = {
                    "first_name": str(row.get('first_name', '')),
                    "last_name": str(row.get('last_name', '')),
                    "phone": str(row.get('phone', '')),
                    "email": str(row.get('email', '')) if not pd.isna(row.get('email')) else None,
                    "property_address": str(row.get('property_address', '')),
                    "property_type": row.get('property_type', 'fix_flip'),
                    "campaign_id": campaign_id,
                    "property_value": float(row.get('property_value', 0)) if not pd.isna(row.get('property_value')) else None,
                    "condition": str(row.get('condition', '')) if not pd.isna(row.get('condition')) else None,
                    "notes": str(row.get('notes', '')) if not pd.isna(row.get('notes')) else None
                }
                
                # TODO: Save to database
                imported += 1
                
            except Exception as e:
                errors.append(f"Row {index + 1}: {str(e)}")
                skipped += 1
        
        return {
            "imported": imported,
            "skipped": skipped,
            "errors": errors
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/{campaign_id}")
async def export_leads(campaign_id: str, format: str = "csv"):
    """Export leads for a campaign"""
    try:
        # TODO: Implement actual export logic
        # For now, return a simple response
        return {"message": f"Export functionality will be implemented for campaign {campaign_id} in {format} format"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
