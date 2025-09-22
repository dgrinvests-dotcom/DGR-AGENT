#!/usr/bin/env python3
"""
Example usage of the AI Real Estate Outreach Agent

This script demonstrates how to:
1. Create campaigns for different property types
2. Import leads from various sources
3. Start outreach campaigns
4. Monitor campaign performance
"""

import asyncio
import os
import sys
from datetime import datetime

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.lead import Lead, PropertyType, LeadStatus
from campaigns.campaign_manager import CampaignManager
from integrations.google_meet_integration import GoogleMeetIntegration
from integrations.telnyx_integration import TelnyxIntegration
from integrations.gmail_integration import GmailIntegration
from leads.lead_processor import LeadProcessor
from agents.conversation_agent import ConversationAgent

async def main():
    """Main example function"""
    
    print("🏠 AI Real Estate Outreach Agent - Example Usage")
    print("=" * 50)
    
    # Initialize components
    campaign_manager = CampaignManager()
    lead_processor = LeadProcessor()
    conversation_agent = ConversationAgent()
    
    # Example 1: Create a Fix & Flip Campaign
    print("\n📋 Creating Fix & Flip Campaign...")
    
    flip_campaign_id = await campaign_manager.create_campaign(
        name="Q4 Fix & Flip Outreach",
        property_type=PropertyType.FIX_FLIP,
        config={
            "max_daily_contacts": 50,
            "follow_up_days": [3, 7, 14],
            "target_response_rate": 15
        }
    )
    
    print(f"✅ Created campaign: {flip_campaign_id}")
    
    # Example 2: Import sample leads
    print("\n📥 Importing sample leads...")
    
    sample_leads = [
        {
            "first_name": "John",
            "last_name": "Smith", 
            "phone": "+15551234567",
            "email": "john.smith@email.com",
            "address": "123 Main St, Anytown, ST 12345",
            "property_value": 150000,
            "condition": "Needs repairs"
        },
        {
            "first_name": "Sarah",
            "last_name": "Johnson",
            "phone": "+15559876543", 
            "email": "sarah.j@email.com",
            "address": "456 Oak Ave, Somewhere, ST 67890",
            "property_value": 200000,
            "condition": "Good condition"
        }
    ]
    
    import_result = await lead_processor.import_leads({
        "source": "manual",
        "campaign_id": flip_campaign_id,
        "property_type": "fix_flip",
        "leads": sample_leads
    })
    
    print(f"✅ Imported {import_result['imported']} leads")
    if import_result['errors']:
        print(f"⚠️  Errors: {import_result['errors']}")
    
    # Example 3: Create Vacant Land Campaign
    print("\n🏞️  Creating Vacant Land Campaign...")
    
    land_campaign_id = await campaign_manager.create_campaign(
        name="Land Investment Opportunities",
        property_type=PropertyType.VACANT_LAND,
        config={
            "max_daily_contacts": 25,
            "follow_up_days": [5, 10, 21]
        }
    )
    
    print(f"✅ Created land campaign: {land_campaign_id}")
    
    # Example 4: Start the Fix & Flip campaign
    print(f"\n🚀 Starting Fix & Flip campaign...")
    
    # Note: In a real scenario, you'd have proper API keys configured
    # This will show the structure even if APIs aren't configured
    try:
        start_result = await campaign_manager.start_campaign(flip_campaign_id)
        print(f"✅ Campaign started: {start_result}")
    except Exception as e:
        print(f"⚠️  Campaign start simulation (API keys needed): {e}")
    
    # Example 5: Check campaign status
    print(f"\n📊 Checking campaign status...")
    
    status = await campaign_manager.get_campaign_status(flip_campaign_id)
    print(f"Campaign Status:")
    print(f"  - Total leads: {status.get('total_leads', 0)}")
    print(f"  - Response rate: {status.get('response_rate', 0):.1f}%")
    print(f"  - Appointments set: {status.get('appointments_set', 0)}")
    
    # Example 6: Simulate incoming message processing
    print(f"\n💬 Simulating conversation...")
    
    # This would normally be triggered by Twilio webhook
    sample_phone = "+15551234567"
    sample_message = "Yes, I'm interested in selling my house"
    
    try:
        ai_response = await conversation_agent.process_message(sample_phone, sample_message)
        print(f"Lead message: '{sample_message}'")
        print(f"AI response: '{ai_response}'")
    except Exception as e:
        print(f"⚠️  Conversation simulation (requires OpenAI API): {e}")
    
    # Example 7: Export leads
    print(f"\n📤 Exporting leads...")
    
    try:
        export_path = await lead_processor.export_leads(flip_campaign_id, format="csv")
        print(f"✅ Leads exported to: {export_path}")
    except Exception as e:
        print(f"⚠️  Export simulation: {e}")
    
    print(f"\n🎉 Example completed! Check the database for created campaigns and leads.")
    print(f"\n📝 Next steps:")
    print(f"  1. Configure your API keys in .env file")
    print(f"  2. Set up Telnyx webhook: POST /webhook/sms")
    print(f"  3. Configure Google Meet integration")
    print(f"  4. Import your real leads from CSV/Excel sheets")
    print(f"  5. Start your campaigns!")

def example_csv_import():
    """Example of how to import leads from CSV"""
    
    print("\n📄 CSV Import Example")
    print("-" * 30)
    
    # Create sample CSV content
    csv_content = """first_name,last_name,phone,email,address,property_value,condition
John,Doe,5551234567,john@email.com,"123 Main St, City, ST 12345",180000,Fair
Jane,Smith,5559876543,jane@email.com,"456 Oak Ave, Town, ST 67890",220000,Good
Bob,Wilson,5555555555,bob@email.com,"789 Pine Rd, Village, ST 11111",150000,Needs work"""
    
    # Save to file
    csv_path = "sample_leads.csv"
    with open(csv_path, 'w') as f:
        f.write(csv_content)
    
    print(f"✅ Created sample CSV: {csv_path}")
    print("To import this CSV:")
    print(f"""
    import_result = await lead_processor.import_leads({{
        "source": "csv",
        "campaign_id": "your_campaign_id",
        "property_type": "fix_flip",
        "file_path": "{csv_path}"
    }})
    """)

def example_api_setup():
    """Show example of API configuration"""
    
    print("\n🔧 API Configuration Example")
    print("-" * 35)
    
    print("Create a .env file with these variables:")
    print("""
# OpenAI (required for AI conversations)
OPENAI_API_KEY=sk-your-openai-key-here

# Telnyx (required for SMS)
TELNYX_API_KEY=your-telnyx-api-key
TELNYX_MESSAGING_PROFILE_ID=your-messaging-profile-id
TELNYX_PHONE_NUMBER=your-telnyx-phone-number
TELNYX_WEBHOOK_SECRET=your-webhook-secret

# Google Meet (required for appointment booking)
GOOGLE_CREDENTIALS_FILE=credentials.json
GOOGLE_TOKEN_FILE=token.json

# Gmail (required for email)
GMAIL_ADDRESS=your-gmail-address@gmail.com
GMAIL_APP_PASSWORD=your-gmail-app-password

# Compliance (recommended)
DNC_API_KEY=your-dnc-service-key
QUIET_HOURS_START=21:00
QUIET_HOURS_END=08:00
TIMEZONE=America/New_York
    """)

if __name__ == "__main__":
    print("🏠 AI Real Estate Outreach Agent Examples")
    print("=" * 45)
    
    # Show configuration examples
    example_api_setup()
    example_csv_import()
    
    # Run main async example
    print("\n🚀 Running main example...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Example interrupted by user")
    except Exception as e:
        print(f"\n❌ Example error: {e}")
        print("This is expected if API keys are not configured.")
