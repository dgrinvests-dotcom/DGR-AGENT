#!/usr/bin/env python3
"""
Test script for AI Real Estate Outreach Agent

This script tests core functionality without requiring external API keys.
"""

import asyncio
import os
import sys
import tempfile
from datetime import datetime

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.lead import Lead, PropertyType, LeadStatus
from utils.database import DatabaseManager
from compliance.compliance_checker import ComplianceChecker

async def test_database():
    """Test database operations"""
    print("\n🗄️  Testing Database Operations...")
    
    # Use temporary database for testing
    test_db_path = os.path.join(tempfile.gettempdir(), "test_leads.db")
    os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path}"
    
    db = DatabaseManager()
    
    # Test lead creation
    test_lead = Lead(
        first_name="Test",
        last_name="User",
        phone="+15551234567",
        property_address="123 Test St, Test City, TS 12345",
        property_type=PropertyType.FIX_FLIP,
        source="test",
        campaign_id="test-campaign-123"
    )
    
    # Create lead
    lead_id = await db.create_lead(test_lead)
    print(f"✅ Created test lead: {lead_id}")
    
    # Retrieve lead
    retrieved_lead = await db.get_lead_by_id(lead_id)
    assert retrieved_lead is not None
    assert retrieved_lead.phone == test_lead.phone
    print(f"✅ Retrieved lead by ID")
    
    # Retrieve by phone
    phone_lead = await db.get_lead_by_phone(test_lead.phone)
    assert phone_lead is not None
    assert phone_lead.id == lead_id
    print(f"✅ Retrieved lead by phone")
    
    # Update lead
    retrieved_lead.status = LeadStatus.INTERESTED
    updated = await db.update_lead(retrieved_lead)
    assert updated
    print(f"✅ Updated lead status")
    
    # Get campaign stats
    stats = await db.get_campaign_stats("test-campaign-123")
    assert stats["total_leads"] == 1
    print(f"✅ Campaign stats: {stats}")
    
    # Cleanup
    os.remove(test_db_path)
    print(f"✅ Database tests passed!")

def test_compliance():
    """Test compliance checker"""
    print("\n⚖️  Testing Compliance Checker...")
    
    compliance = ComplianceChecker()
    
    # Test phone number normalization
    test_numbers = [
        "555-123-4567",
        "(555) 123-4567", 
        "5551234567",
        "+15551234567"
    ]
    
    for number in test_numbers:
        normalized = compliance._normalize_phone(number)
        assert normalized == "+15551234567"
    
    print(f"✅ Phone normalization works")
    
    # Test opt-out functionality
    test_phone = "+15551234567"
    
    # Should be able to contact initially
    can_contact_before = compliance.can_contact(test_phone)
    
    # Add to opt-out
    compliance.add_to_opt_out(test_phone)
    
    # Should not be able to contact after opt-out
    can_contact_after = compliance.can_contact(test_phone)
    assert not can_contact_after
    
    print(f"✅ Opt-out functionality works")
    
    # Test compliance report
    report = compliance.get_compliance_report()
    assert "opt_out_count" in report
    assert report["opt_out_count"] >= 1
    
    print(f"✅ Compliance report: {report}")
    print(f"✅ Compliance tests passed!")

def test_lead_models():
    """Test lead data models"""
    print("\n📋 Testing Lead Models...")
    
    # Test Lead creation
    lead = Lead(
        first_name="John",
        last_name="Doe",
        phone="+15551234567",
        property_address="123 Main St, City, ST 12345",
        property_type=PropertyType.FIX_FLIP,
        source="test",
        campaign_id="test-123"
    )
    
    assert lead.status == LeadStatus.NEW
    assert lead.property_type == PropertyType.FIX_FLIP
    assert lead.opted_out == False
    
    print(f"✅ Lead model creation works")
    
    # Test serialization
    lead_dict = lead.dict()
    assert "phone" in lead_dict
    assert "property_type" in lead_dict
    
    print(f"✅ Lead serialization works")
    
    # Test property types
    property_types = [PropertyType.FIX_FLIP, PropertyType.RENTAL, PropertyType.VACANT_LAND]
    for pt in property_types:
        test_lead = Lead(
            phone="+15551234567",
            property_address="Test Address",
            property_type=pt,
            source="test",
            campaign_id="test"
        )
        assert test_lead.property_type == pt
    
    print(f"✅ All property types work")
    print(f"✅ Lead model tests passed!")

def test_campaign_templates():
    """Test campaign template structure"""
    print("\n📝 Testing Campaign Templates...")
    
    # Import here to avoid circular imports during testing
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
    from campaigns.campaign_manager import CampaignManager
    
    campaign_manager = CampaignManager()
    templates = campaign_manager._load_campaign_templates()
    
    # Check that templates exist for all property types
    required_types = [PropertyType.FIX_FLIP, PropertyType.RENTAL, PropertyType.VACANT_LAND]
    
    for prop_type in required_types:
        assert prop_type in templates
        template = templates[prop_type]
        assert "initial_message" in template
        assert "follow_up_sequences" in template
    
    print(f"✅ All property type templates exist")
    
    # Test message formatting
    flip_template = templates[PropertyType.FIX_FLIP]
    initial_msg = flip_template["initial_message"]
    
    # Should contain placeholders
    assert "{name}" in initial_msg or "{address}" in initial_msg
    
    print(f"✅ Message templates have placeholders")
    print(f"✅ Campaign template tests passed!")

async def run_all_tests():
    """Run all tests"""
    print("🧪 AI Real Estate Outreach Agent - System Tests")
    print("=" * 50)
    
    try:
        # Test models
        test_lead_models()
        
        # Test compliance
        test_compliance()
        
        # Test database
        await test_database()
        
        # Test campaign templates
        test_campaign_templates()
        
        print(f"\n🎉 All tests passed!")
        print(f"✅ System is ready for use")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_environment():
    """Check if environment is properly configured"""
    print("\n🔍 Checking Environment Configuration...")
    
    required_for_full_functionality = [
        "OPENAI_API_KEY",
        "TWILIO_ACCOUNT_SID", 
        "TWILIO_AUTH_TOKEN",
        "TWILIO_PHONE_NUMBER",
        "CALENDLY_API_TOKEN",
        "CALENDLY_USER_URI"
    ]
    
    optional_vars = [
        "PROPWIRE_API_KEY",
        "SKIPTRACE_API_KEY", 
        "DNC_API_KEY"
    ]
    
    configured_required = []
    configured_optional = []
    
    for var in required_for_full_functionality:
        if os.getenv(var):
            configured_required.append(var)
    
    for var in optional_vars:
        if os.getenv(var):
            configured_optional.append(var)
    
    print(f"Required APIs configured: {len(configured_required)}/{len(required_for_full_functionality)}")
    for var in configured_required:
        print(f"  ✅ {var}")
    
    for var in required_for_full_functionality:
        if var not in configured_required:
            print(f"  ❌ {var} (missing)")
    
    if configured_optional:
        print(f"\nOptional APIs configured:")
        for var in configured_optional:
            print(f"  ✅ {var}")
    
    if len(configured_required) == len(required_for_full_functionality):
        print(f"\n🎉 All required APIs configured! System ready for production.")
    else:
        print(f"\n⚠️  Some APIs missing. System will work in limited mode.")
        print(f"   Create .env file with missing API keys for full functionality.")

if __name__ == "__main__":
    print("🧪 Running AI Real Estate Outreach Agent Tests")
    print("=" * 50)
    
    # Check environment first
    check_environment()
    
    # Run system tests
    print(f"\n🚀 Starting system tests...")
    
    try:
        success = asyncio.run(run_all_tests())
        
        if success:
            print(f"\n✅ System validation complete!")
            print(f"📋 Next steps:")
            print(f"  1. Configure missing API keys in .env")
            print(f"  2. Run: python examples/example_usage.py")
            print(f"  3. Start the server: python src/main.py")
        else:
            print(f"\n❌ System validation failed!")
            print(f"   Check the errors above and fix before proceeding.")
            
    except KeyboardInterrupt:
        print(f"\n👋 Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test runner error: {e}")
        import traceback
        traceback.print_exc()
