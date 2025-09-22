import os
import pandas as pd
from typing import Dict, Any, Optional, List
import uuid
from datetime import datetime
import json
import logging

from models.lead import Lead, LeadStatus, PropertyType
from utils.database import DatabaseManager
from compliance.compliance_checker import ComplianceChecker

class LeadProcessor:
    def __init__(self):
        self.db = DatabaseManager()
        self.compliance = ComplianceChecker()
        self.logger = logging.getLogger(__name__)
    
    async def import_leads(self, leads_data: Dict[str, Any]) -> Dict[str, Any]:
        """Import leads from various sources"""
        source = leads_data.get("source", "manual")
        campaign_id = leads_data.get("campaign_id")
        property_type = PropertyType(leads_data.get("property_type", "fix_flip"))
        
        if not campaign_id:
            return {"error": "Campaign ID is required"}
        
        results = {
            "imported": 0,
            "skipped": 0,
            "errors": []
        }
        
        if source == "csv" or source == "sheet":
            results = await self._import_from_csv(leads_data, campaign_id, property_type)
        elif source == "manual":
            results = await self._import_manual_leads(leads_data, campaign_id, property_type)
        else:
            return {"error": f"Unsupported source: {source}. Use 'csv', 'sheet', or 'manual'."}
        
        return results
    
    
    async def _import_from_csv(self, data: Dict[str, Any], campaign_id: str, property_type: PropertyType) -> Dict[str, Any]:
        """Import leads from CSV/Excel file or direct data"""
        try:
            # Handle direct data (for API calls with lead data)
            if "leads" in data:
                csv_leads = data["leads"]
                self.logger.info(f"Processing {len(csv_leads)} leads from direct data")
                return await self._process_lead_batch(csv_leads, campaign_id, property_type, "sheet")
            
            # Handle file path
            csv_file_path = data.get("file_path")
            if not csv_file_path or not os.path.exists(csv_file_path):
                return {"error": "CSV/Excel file not found or no leads data provided"}
            
            # Read file based on extension
            file_extension = os.path.splitext(csv_file_path)[1].lower()
            
            if file_extension == '.csv':
                df = pd.read_csv(csv_file_path)
            elif file_extension in ['.xlsx', '.xls']:
                df = pd.read_excel(csv_file_path)
            else:
                return {"error": "Unsupported file format. Use CSV or Excel files."}
            
            # Validate required columns
            required_columns = ['phone', 'property_address']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return {"error": f"Missing required columns: {missing_columns}. Required: {required_columns}"}
            
            # Clean and standardize column names
            df.columns = df.columns.str.lower().str.strip()
            
            # Convert DataFrame to list of dictionaries
            csv_leads = df.to_dict('records')
            
            self.logger.info(f"Processing {len(csv_leads)} leads from file: {csv_file_path}")
            return await self._process_lead_batch(csv_leads, campaign_id, property_type, "csv")
            
        except Exception as e:
            self.logger.error(f"CSV/Excel import failed: {str(e)}")
            return {"error": f"File import failed: {str(e)}", "imported": 0, "skipped": 0}
    
    async def _import_manual_leads(self, data: Dict[str, Any], campaign_id: str, property_type: PropertyType) -> Dict[str, Any]:
        """Import manually provided leads"""
        try:
            manual_leads = data.get("leads", [])
            
            if not manual_leads:
                return {"error": "No leads provided"}
            
            return await self._process_lead_batch(manual_leads, campaign_id, property_type, "manual")
            
        except Exception as e:
            return {"error": f"Manual import failed: {str(e)}", "imported": 0, "skipped": 0}
    
    async def _process_lead_batch(self, leads_data: List[Dict[str, Any]], campaign_id: str, property_type: PropertyType, source: str) -> Dict[str, Any]:
        """Process a batch of leads and save to database"""
        imported = 0
        skipped = 0
        errors = []
        
        for lead_data in leads_data:
            try:
                # Normalize lead data
                normalized_lead = self._normalize_lead_data(lead_data, campaign_id, property_type, source)
                
                if not normalized_lead:
                    skipped += 1
                    continue
                
                # Check if lead already exists
                existing_lead = await self.db.get_lead_by_phone(normalized_lead.phone)
                if existing_lead:
                    skipped += 1
                    continue
                
                # Run compliance checks
                if not self._validate_lead_compliance(normalized_lead):
                    skipped += 1
                    continue
                
                # Save lead to database
                lead_id = await self.db.create_lead(normalized_lead)
                
                if lead_id:
                    imported += 1
                else:
                    errors.append(f"Failed to save lead: {normalized_lead.phone}")
                
            except Exception as e:
                errors.append(f"Error processing lead: {str(e)}")
        
        return {
            "imported": imported,
            "skipped": skipped,
            "errors": errors
        }
    
    def _normalize_lead_data(self, raw_data: Dict[str, Any], campaign_id: str, property_type: PropertyType, source: str) -> Optional[Lead]:
        """Normalize raw lead data into Lead model"""
        try:
            # Extract phone number (try different field names)
            phone = (raw_data.get("phone") or 
                    raw_data.get("phone_number") or 
                    raw_data.get("Phone") or 
                    raw_data.get("PhoneNumber"))
            
            if not phone:
                return None
            
            # Normalize phone number
            phone = self.compliance._normalize_phone(phone)
            if not phone:
                return None
            
            # Extract property address
            address = (raw_data.get("address") or 
                      raw_data.get("property_address") or 
                      raw_data.get("Address") or 
                      raw_data.get("PropertyAddress"))
            
            if not address:
                return None
            
            # Create Lead object
            lead = Lead(
                first_name=raw_data.get("first_name") or raw_data.get("FirstName"),
                last_name=raw_data.get("last_name") or raw_data.get("LastName"),
                phone=phone,
                email=raw_data.get("email") or raw_data.get("Email"),
                property_address=address,
                property_type=property_type,
                property_value=self._safe_float(raw_data.get("property_value") or raw_data.get("PropertyValue")),
                property_condition=raw_data.get("condition") or raw_data.get("Condition"),
                source=source,
                source_data=raw_data,
                campaign_id=campaign_id,
                status=LeadStatus.NEW
            )
            
            return lead
            
        except Exception as e:
            print(f"Error normalizing lead data: {e}")
            return None
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _validate_lead_compliance(self, lead: Lead) -> bool:
        """Validate lead for compliance requirements"""
        
        # Check if phone number is valid
        if not lead.phone:
            return False
        
        # Check DNC status (this will be cached for performance)
        if self.compliance._is_on_dnc_registry(lead.phone):
            lead.dnc_checked = True
            return False
        
        # Mark as DNC checked
        lead.dnc_checked = True
        
        return True
    
    async def enrich_lead_data(self, lead_id: str) -> Dict[str, Any]:
        """Enrich lead data with additional information"""
        lead = await self.db.get_lead_by_id(lead_id)
        
        if not lead:
            return {"error": "Lead not found"}
        
        enrichment_data = {}
        
        try:
            # Property value estimation (placeholder)
            property_value = await self._estimate_property_value(lead.property_address)
            if property_value:
                enrichment_data["estimated_value"] = property_value
            
            # Market analysis (placeholder)
            market_data = await self._get_market_analysis(lead.property_address)
            if market_data:
                enrichment_data["market_analysis"] = market_data
            
            # Update lead with enriched data
            lead.source_data.update(enrichment_data)
            await self.db.update_lead(lead)
            
            return {"success": True, "enrichment_data": enrichment_data}
            
        except Exception as e:
            return {"error": f"Enrichment failed: {str(e)}"}
    
    async def _estimate_property_value(self, address: str) -> Optional[float]:
        """Estimate property value using external APIs"""
        # This would integrate with services like Zillow API, RentSpree, etc.
        # Placeholder implementation
        return None
    
    async def _get_market_analysis(self, address: str) -> Optional[Dict[str, Any]]:
        """Get market analysis for property location"""
        # This would integrate with real estate market data APIs
        # Placeholder implementation
        return None
    
    async def deduplicate_leads(self, campaign_id: str) -> Dict[str, Any]:
        """Remove duplicate leads from a campaign"""
        leads = await self.db.get_leads_by_campaign(campaign_id)
        
        seen_phones = set()
        duplicates_removed = 0
        
        for lead in leads:
            if lead.phone in seen_phones:
                # Mark as duplicate or remove
                lead.status = LeadStatus.DNC
                await self.db.update_lead(lead)
                duplicates_removed += 1
            else:
                seen_phones.add(lead.phone)
        
        return {
            "duplicates_removed": duplicates_removed,
            "unique_leads": len(seen_phones)
        }
    
    async def export_leads(self, campaign_id: str, format: str = "csv") -> str:
        """Export leads to file"""
        leads = await self.db.get_leads_by_campaign(campaign_id)
        
        if format == "csv":
            return await self._export_to_csv(leads, campaign_id)
        elif format == "json":
            return await self._export_to_json(leads, campaign_id)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    async def _export_to_csv(self, leads: List[Lead], campaign_id: str) -> str:
        """Export leads to CSV file"""
        import csv
        
        filename = f"leads_{campaign_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join("exports", filename)
        
        # Create exports directory if it doesn't exist
        os.makedirs("exports", exist_ok=True)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'id', 'first_name', 'last_name', 'phone', 'email',
                'property_address', 'property_type', 'property_value',
                'status', 'interest_level', 'created_at'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for lead in leads:
                writer.writerow({
                    'id': lead.id,
                    'first_name': lead.first_name,
                    'last_name': lead.last_name,
                    'phone': lead.phone,
                    'email': lead.email,
                    'property_address': lead.property_address,
                    'property_type': lead.property_type.value,
                    'property_value': lead.property_value,
                    'status': lead.status.value,
                    'interest_level': lead.interest_level,
                    'created_at': lead.created_at.isoformat()
                })
        
        return filepath
    
    async def _export_to_json(self, leads: List[Lead], campaign_id: str) -> str:
        """Export leads to JSON file"""
        filename = f"leads_{campaign_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join("exports", filename)
        
        # Create exports directory if it doesn't exist
        os.makedirs("exports", exist_ok=True)
        
        leads_data = []
        for lead in leads:
            lead_dict = lead.dict()
            # Convert datetime objects to strings
            lead_dict['created_at'] = lead.created_at.isoformat()
            lead_dict['updated_at'] = lead.updated_at.isoformat()
            if lead.last_contact_date:
                lead_dict['last_contact_date'] = lead.last_contact_date.isoformat()
            if lead.next_follow_up_date:
                lead_dict['next_follow_up_date'] = lead.next_follow_up_date.isoformat()
            
            leads_data.append(lead_dict)
        
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(leads_data, jsonfile, indent=2, ensure_ascii=False)
        
        return filepath
