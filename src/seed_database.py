import sqlite3
import json
import uuid
from datetime import datetime

def seed_database():
    """Add sample campaigns to the database"""
    conn = sqlite3.connect("agent_estate.db")
    cursor = conn.cursor()
    
    # Sample campaigns
    campaigns = [
        {
            "id": str(uuid.uuid4()),
            "name": "Fix & Flip Q1 2024",
            "property_type": "fix_flip",
            "status": "active",
            "config": json.dumps({
                "max_daily_contacts": 50,
                "follow_up_days": [1, 3, 7, 14],
                "target_response_rate": 15.0,
                "quiet_hours_start": "21:00",
                "quiet_hours_end": "08:00"
            }),
            "description": "Targeting distressed properties for fix and flip opportunities"
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Vacant Land Outreach",
            "property_type": "vacant_land",
            "status": "active",
            "config": json.dumps({
                "max_daily_contacts": 30,
                "follow_up_days": [1, 3, 7],
                "target_response_rate": 12.0,
                "quiet_hours_start": "21:00",
                "quiet_hours_end": "08:00"
            }),
            "description": "Acquiring vacant land parcels for development"
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Long-Term Rental Properties",
            "property_type": "long_term_rental",
            "status": "created",
            "config": json.dumps({
                "max_daily_contacts": 40,
                "follow_up_days": [1, 3, 7, 14, 30],
                "target_response_rate": 18.0,
                "quiet_hours_start": "21:00",
                "quiet_hours_end": "08:00"
            }),
            "description": "Building portfolio of rental properties"
        }
    ]
    
    # Insert campaigns
    for campaign in campaigns:
        cursor.execute("""
            INSERT OR REPLACE INTO campaigns (id, name, property_type, status, config, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            campaign["id"],
            campaign["name"],
            campaign["property_type"],
            campaign["status"],
            campaign["config"],
            campaign["description"]
        ))
    
    # Update existing leads to link to campaigns
    cursor.execute("SELECT id FROM campaigns WHERE property_type = 'fix_flip' LIMIT 1")
    fix_flip_campaign = cursor.fetchone()
    
    cursor.execute("SELECT id FROM campaigns WHERE property_type = 'vacant_land' LIMIT 1")
    vacant_land_campaign = cursor.fetchone()
    
    if fix_flip_campaign:
        cursor.execute("""
            UPDATE leads SET campaign_id = ? WHERE property_type = 'fix_flip'
        """, (fix_flip_campaign[0],))
    
    if vacant_land_campaign:
        cursor.execute("""
            UPDATE leads SET campaign_id = ? WHERE property_type = 'vacant_land'
        """, (vacant_land_campaign[0],))
    
    conn.commit()
    conn.close()
    
    print("✅ Database seeded with sample campaigns!")
    print("✅ Existing leads linked to appropriate campaigns!")

if __name__ == "__main__":
    seed_database()
