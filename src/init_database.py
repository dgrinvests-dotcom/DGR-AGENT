"""
Initialize Complete Database Schema
Create all required tables for the LangGraph system
"""

import sqlite3
import json
import uuid
from datetime import datetime

def init_complete_database():
    """Initialize complete database schema"""
    print("🗄️ Initializing Complete Database Schema...")
    
    conn = sqlite3.connect("agent_estate.db")
    cursor = conn.cursor()
    
    try:
        # Create leads table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id TEXT PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                email TEXT,
                property_address TEXT NOT NULL,
                property_type TEXT NOT NULL,
                property_value REAL,
                property_condition TEXT,
                source TEXT DEFAULT 'manual',
                source_data TEXT DEFAULT '{}',
                campaign_id TEXT,
                status TEXT DEFAULT 'new',
                conversation_history TEXT DEFAULT '[]',
                last_contact_date TEXT,
                next_follow_up_date TEXT,
                qualification_data TEXT DEFAULT '{}',
                interest_level INTEGER DEFAULT 0,
                opted_out BOOLEAN DEFAULT FALSE,
                dnc_checked BOOLEAN DEFAULT FALSE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        print("  ✅ leads table created")
        
        # Create campaigns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS campaigns (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                property_type TEXT NOT NULL,
                status TEXT DEFAULT 'created',
                description TEXT,
                config TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        print("  ✅ campaigns table created")
        
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
        print("  ✅ compliance_logs table created")
        
        # Create opt_outs table (if not exists)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS opt_outs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone_number TEXT UNIQUE NOT NULL,
                opted_out_at TEXT NOT NULL,
                method TEXT NOT NULL,
                reason TEXT
            )
        """)
        print("  ✅ opt_outs table created")
        
        # Create conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                lead_id TEXT NOT NULL,
                campaign_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                agent_history TEXT DEFAULT '[]',
                current_agent TEXT,
                conversation_stage TEXT DEFAULT 'initial',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (lead_id) REFERENCES leads (id)
            )
        """)
        print("  ✅ conversations table created")
        
        # Create messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                direction TEXT NOT NULL,
                content TEXT NOT NULL,
                method TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                ai_generated BOOLEAN DEFAULT FALSE,
                delivery_status TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id)
            )
        """)
        print("  ✅ messages table created")
        
        conn.commit()
        print("  ✅ All tables created successfully!")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Database initialization failed: {e}")
        return False
    finally:
        conn.close()

def seed_sample_data():
    """Add sample campaigns and test lead"""
    print("\n🌱 Seeding Sample Data...")
    
    conn = sqlite3.connect("agent_estate.db")
    cursor = conn.cursor()
    
    try:
        # Sample campaigns
        campaigns = [
            {
                "id": str(uuid.uuid4()),
                "name": "Fix & Flip Q1 2024",
                "property_type": "fix_flip",
                "status": "active",
                "description": "Targeting distressed properties for fix and flip opportunities",
                "config": json.dumps({
                    "max_daily_contacts": 50,
                    "follow_up_days": [1, 3, 7, 14],
                    "target_response_rate": 15.0
                })
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Vacant Land Outreach",
                "property_type": "vacant_land", 
                "status": "active",
                "description": "Acquiring vacant land parcels for development",
                "config": json.dumps({
                    "max_daily_contacts": 30,
                    "follow_up_days": [1, 3, 7],
                    "target_response_rate": 12.0
                })
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Long-Term Rental Properties",
                "property_type": "long_term_rental",
                "status": "active", 
                "description": "Building portfolio of rental properties",
                "config": json.dumps({
                    "max_daily_contacts": 40,
                    "follow_up_days": [1, 3, 7, 14, 30],
                    "target_response_rate": 18.0
                })
            }
        ]
        
        # Insert campaigns
        for campaign in campaigns:
            cursor.execute("""
                INSERT OR REPLACE INTO campaigns 
                (id, name, property_type, status, description, config, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                campaign["id"], campaign["name"], campaign["property_type"], 
                campaign["status"], campaign["description"], campaign["config"],
                datetime.now().isoformat(), datetime.now().isoformat()
            ))
        
        print("  ✅ Sample campaigns created")
        
        # Get fix_flip campaign for test lead
        cursor.execute("SELECT id FROM campaigns WHERE property_type = 'fix_flip' LIMIT 1")
        campaign_id = cursor.fetchone()[0]
        
        # Create test lead for end-to-end testing
        test_lead = {
            "id": str(uuid.uuid4()),
            "first_name": "Umair",
            "last_name": "Shafiq",
            "phone": "+16096236125",  # Real test phone number
            "email": "umairshafiq.cs@gmail.com",  # Real test email
            "property_address": "123 Test Street, Dallas, TX 75201",
            "property_type": "fix_flip",
            "campaign_id": campaign_id,
            "status": "new"
        }
        
        cursor.execute("""
            INSERT OR REPLACE INTO leads 
            (id, first_name, last_name, phone, email, property_address, 
             property_type, campaign_id, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            test_lead["id"], test_lead["first_name"], test_lead["last_name"],
            test_lead["phone"], test_lead["email"], test_lead["property_address"],
            test_lead["property_type"], test_lead["campaign_id"], test_lead["status"],
            datetime.now().isoformat(), datetime.now().isoformat()
        ))
        
        print("  ✅ Test lead created for end-to-end testing")
        print(f"     Phone: {test_lead['phone']}")
        print(f"     Email: {test_lead['email']}")
        print(f"     Property: {test_lead['property_address']}")
        
        conn.commit()
        return test_lead
        
    except Exception as e:
        print(f"  ❌ Sample data seeding failed: {e}")
        return None
    finally:
        conn.close()

def verify_database_schema():
    """Verify all tables exist and have correct structure"""
    print("\n🔍 Verifying Database Schema...")
    
    conn = sqlite3.connect("agent_estate.db")
    cursor = conn.cursor()
    
    try:
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = ["leads", "campaigns", "compliance_logs", "opt_outs", "conversations", "messages"]
        
        all_exist = True
        for table in required_tables:
            if table in tables:
                # Get table info
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [row[1] for row in cursor.fetchall()]
                print(f"  ✅ {table} ({len(columns)} columns)")
            else:
                print(f"  ❌ {table} - Missing!")
                all_exist = False
        
        # Count records
        if all_exist:
            cursor.execute("SELECT COUNT(*) FROM campaigns")
            campaign_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM leads")
            lead_count = cursor.fetchone()[0]
            
            print(f"\n📊 Database Contents:")
            print(f"  📋 Campaigns: {campaign_count}")
            print(f"  👥 Leads: {lead_count}")
        
        return all_exist
        
    except Exception as e:
        print(f"  ❌ Schema verification failed: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 Database Initialization Starting...")
    
    # Initialize database
    init_success = init_complete_database()
    
    if init_success:
        # Seed sample data
        test_lead = seed_sample_data()
        
        # Verify everything
        schema_valid = verify_database_schema()
        
        if schema_valid:
            print(f"\n🎉 Database Initialization Complete!")
            print(f"✅ All tables created and verified")
            print(f"✅ Sample campaigns and test lead added")
            print(f"\n🧪 Ready for end-to-end testing with:")
            if test_lead:
                print(f"  📱 Test Phone: {test_lead['phone']}")
                print(f"  📧 Test Email: {test_lead['email']}")
                print(f"  🏠 Test Property: {test_lead['property_address']}")
        else:
            print(f"\n❌ Database schema verification failed")
    else:
        print(f"\n❌ Database initialization failed")
