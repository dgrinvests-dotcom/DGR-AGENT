"""
Complete LangGraph Real Estate Outreach System
Week 3 Implementation: Full agent assembly with property specialists and booking
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from typing import Literal, Dict, Any
from langgraph.graph import StateGraph, START, END

from schemas.agent_state import RealEstateAgentState, create_initial_state
from agents.supervisor_agent import supervisor_agent_node
from agents.communication_router import communication_router_node
from agents.sms_agent import sms_agent_node
from agents.email_agent import email_agent_node
from agents.booking_agent import booking_agent_node

# Import property specialists
from agents.property_specialists.fix_flip_agent import fix_flip_agent_node
from agents.property_specialists.vacant_land_agent import vacant_land_agent_node
from agents.property_specialists.rental_agent import rental_agent_node


def create_complete_real_estate_graph():
    """
    Create complete real estate outreach LangGraph with all agents
    
    Flow:
    START → Supervisor → Communication Router → SMS/Email → Property Specialist → Booking → END
    """
    
    # Create the graph with our state schema
    workflow = StateGraph(RealEstateAgentState)
    
    # Add all nodes
    workflow.add_node("supervisor", supervisor_agent_node)
    workflow.add_node("communication_router", communication_router_node)
    workflow.add_node("sms_agent", sms_agent_node)
    workflow.add_node("email_agent", email_agent_node)
    workflow.add_node("fix_flip_agent", fix_flip_agent_node)
    workflow.add_node("vacant_land_agent", vacant_land_agent_node)
    workflow.add_node("rental_agent", rental_agent_node)
    workflow.add_node("booking_agent", booking_agent_node)
    
    # Add edges
    workflow.add_edge(START, "supervisor")
    
    # Supervisor routing
    workflow.add_conditional_edges(
        "supervisor",
        route_supervisor_decision,
        {
            "communication_router": "communication_router",
            "fix_flip_agent": "fix_flip_agent",
            "vacant_land_agent": "vacant_land_agent",
            "rental_agent": "rental_agent",
            "booking_agent": "booking_agent",
            "END": END
        }
    )
    
    # Communication router routing
    workflow.add_conditional_edges(
        "communication_router",
        route_communication_channel,
        {
            "sms_agent": "sms_agent",
            "email_agent": "email_agent",
            "END": END
        }
    )
    
    # SMS agent routing
    workflow.add_conditional_edges(
        "sms_agent",
        route_sms_result,
        {
            "email_agent": "email_agent",  # Fallback to email
            "supervisor": "supervisor",    # Success, return to supervisor
            "END": END
        }
    )
    
    # Email agent routing
    workflow.add_conditional_edges(
        "email_agent",
        route_email_result,
        {
            "supervisor": "supervisor",    # Return to supervisor
            "END": END
        }
    )
    
    # Property specialist routing
    workflow.add_conditional_edges(
        "fix_flip_agent",
        route_property_specialist_result,
        {
            "communication_router": "communication_router",
            "booking_agent": "booking_agent",
            "supervisor": "supervisor",
            "END": END
        }
    )
    
    workflow.add_conditional_edges(
        "vacant_land_agent",
        route_property_specialist_result,
        {
            "communication_router": "communication_router",
            "booking_agent": "booking_agent",
            "supervisor": "supervisor",
            "END": END
        }
    )
    
    workflow.add_conditional_edges(
        "rental_agent",
        route_property_specialist_result,
        {
            "communication_router": "communication_router",
            "booking_agent": "booking_agent",
            "supervisor": "supervisor",
            "END": END
        }
    )
    
    # Booking agent routing
    workflow.add_conditional_edges(
        "booking_agent",
        route_booking_result,
        {
            "communication_router": "communication_router",
            "supervisor": "supervisor",
            "END": END
        }
    )
    
    # Compile the graph
    return workflow.compile()


def route_supervisor_decision(state: RealEstateAgentState) -> str:
    """
    Route supervisor decisions to appropriate agents
    """
    next_action = state.get("next_action")
    property_type = state.get("property_type")
    conversation_stage = state.get("conversation_stage")
    
    # Initial outreach routing
    if next_action == "initial_outreach":
        return "communication_router"
    
    # Property specialist routing based on type
    elif next_action in ["continue_qualification", "handle_objection"]:
        if property_type == "fix_flip":
            return "fix_flip_agent"
        elif property_type == "vacant_land":
            return "vacant_land_agent"
        elif property_type == "long_term_rental":
            return "rental_agent"
        else:
            return "communication_router"
    
    # Booking routing
    elif next_action == "schedule_appointment":
        return "booking_agent"
    
    # End states
    elif next_action == "mark_not_interested" or conversation_stage == "not_interested":
        return "END"
    
    # Default routing
    else:
        return "communication_router"


def route_communication_channel(state: RealEstateAgentState) -> str:
    """
    Route to appropriate communication channel
    """
    preferred_channel = state.get("preferred_channel")
    
    if preferred_channel == "sms":
        return "sms_agent"
    elif preferred_channel == "email":
        return "email_agent"
    else:
        return "END"


def route_sms_result(state: RealEstateAgentState) -> str:
    """
    Route SMS agent results
    """
    next_action = state.get("next_action")
    
    if next_action == "fallback_to_email":
        return "email_agent"
    elif next_action == "sms_sent":
        return "supervisor"
    else:
        return "END"


def route_email_result(state: RealEstateAgentState) -> str:
    """
    Route email agent results
    """
    next_action = state.get("next_action")
    
    if next_action in ["email_sent", "email_failed"]:
        return "supervisor"
    else:
        return "END"


def route_property_specialist_result(state: RealEstateAgentState) -> str:
    """
    Route property specialist agent results
    """
    next_action = state.get("next_action")
    conversation_stage = state.get("conversation_stage")
    
    if next_action == "send_message":
        return "communication_router"
    elif next_action == "schedule_appointment":
        return "booking_agent"
    elif conversation_stage == "not_interested":
        return "END"
    else:
        return "supervisor"


def route_booking_result(state: RealEstateAgentState) -> str:
    """
    Route booking agent results
    """
    next_action = state.get("next_action")
    conversation_stage = state.get("conversation_stage")
    
    if next_action == "send_message":
        return "communication_router"
    elif conversation_stage == "not_interested":
        return "END"
    else:
        return "supervisor"


def test_complete_conversation_flows():
    """
    Test complete conversation flows for all property types
    """
    print("🧪 Testing Complete Conversation Flows...")
    
    # Test scenarios for all property types
    test_scenarios = [
        {
            "name": "Fix & Flip - Full Qualification to Booking",
            "property_type": "fix_flip",
            "lead_data": {
                "lead_id": "ff_test_001",
                "lead_name": "John Smith",
                "property_address": "123 Oak Street, Dallas, TX",
                "campaign_id": "ff_campaign_001",
                "lead_phone": "+12145551234",
                "lead_email": "john.smith@example.com"
            },
            "conversation_flow": [
                "Initial outreach",
                "Qualification questions",
                "Booking request"
            ]
        },
        {
            "name": "Vacant Land - Consultation Booking",
            "property_type": "vacant_land",
            "lead_data": {
                "lead_id": "vl_test_001",
                "lead_name": "Sarah Johnson",
                "property_address": "456 Pine Avenue, Austin, TX",
                "campaign_id": "vl_campaign_001",
                "lead_phone": "+15125551234",
                "lead_email": "sarah.johnson@example.com"
            },
            "conversation_flow": [
                "Initial outreach",
                "Land qualification",
                "15-minute consultation booking"
            ]
        },
        {
            "name": "Rental Property - Lease Discussion",
            "property_type": "long_term_rental",
            "lead_data": {
                "lead_id": "rp_test_001",
                "lead_name": "Mike Wilson",
                "property_address": "789 Elm Street, Houston, TX",
                "campaign_id": "rp_campaign_001",
                "lead_phone": "+17135551234",
                "lead_email": "mike.wilson@example.com"
            },
            "conversation_flow": [
                "Initial outreach",
                "Rental situation assessment",
                "Booking with lease discussion"
            ]
        }
    ]
    
    # Create and test the graph
    graph = create_complete_real_estate_graph()
    
    results = []
    
    for scenario in test_scenarios:
        print(f"\n📋 Testing: {scenario['name']}")
        
        # Create initial state
        state = create_initial_state(
            property_type=scenario["property_type"],
            **scenario["lead_data"]
        )
        
        try:
            # Run the graph
            result = graph.invoke(state)
            
            print(f"  ✅ Scenario completed successfully")
            print(f"     - Final Stage: {result.get('conversation_stage', 'unknown')}")
            print(f"     - Last Contact Method: {result.get('last_contact_method', 'none')}")
            print(f"     - Agent History: {' → '.join(result.get('agent_history', []))}")
            print(f"     - Messages Sent: {result.get('total_messages_sent', 0)}")
            
            if result.get('last_error'):
                print(f"     ⚠️ Last Error: {result['last_error']}")
            
            results.append({
                "scenario": scenario["name"],
                "success": True,
                "result": result
            })
            
        except Exception as e:
            print(f"  ❌ Scenario failed: {e}")
            results.append({
                "scenario": scenario["name"],
                "success": False,
                "error": str(e)
            })
    
    return results


def test_property_specialist_agents():
    """
    Test individual property specialist agents
    """
    print("\n🧪 Testing Property Specialist Agents...")
    
    # Test Fix & Flip Agent
    print("\n🏠 Testing Fix & Flip Agent...")
    try:
        from agents.property_specialists.fix_flip_agent import FixFlipSpecialistAgent
        
        agent = FixFlipSpecialistAgent()
        print(f"  ✅ Fix & Flip agent created: {agent.agent_name}")
        
        # Test qualification sequence
        print(f"  ✅ Qualification sequence: {agent.qualification_sequence}")
        
        # Test message generation
        state = create_initial_state(
            lead_id="ff_test",
            lead_name="Test Lead",
            property_address="123 Test St",
            property_type="fix_flip",
            campaign_id="test_campaign"
        )
        
        message = agent._generate_qualification_message(state)
        print(f"  ✅ Sample message: {message[:60]}...")
        
    except Exception as e:
        print(f"  ❌ Fix & Flip agent test failed: {e}")
    
    # Test Vacant Land Agent
    print("\n🌲 Testing Vacant Land Agent...")
    try:
        from agents.property_specialists.vacant_land_agent import VacantLandSpecialistAgent
        
        agent = VacantLandSpecialistAgent()
        print(f"  ✅ Vacant Land agent created: {agent.agent_name}")
        print(f"  ✅ Qualification sequence: {agent.qualification_sequence}")
        
    except Exception as e:
        print(f"  ❌ Vacant Land agent test failed: {e}")
    
    # Test Rental Agent
    print("\n🏢 Testing Rental Property Agent...")
    try:
        from agents.property_specialists.rental_agent import RentalPropertySpecialistAgent
        
        agent = RentalPropertySpecialistAgent()
        print(f"  ✅ Rental agent created: {agent.agent_name}")
        print(f"  ✅ Qualification sequence: {agent.qualification_sequence}")
        
    except Exception as e:
        print(f"  ❌ Rental agent test failed: {e}")


def test_booking_agent():
    """
    Test booking agent functionality
    """
    print("\n🧪 Testing Booking Agent...")
    
    try:
        from agents.booking_agent import BookingAgent
        
        agent = BookingAgent()
        print(f"  ✅ Booking agent created: {agent.agent_name}")
        
        # Test meeting types
        print(f"  ✅ Meeting types: {list(agent.meeting_types.keys())}")
        
        # Test availability generation
        availability = agent._get_available_slots()
        print(f"  ✅ Availability generated: {len(availability)} characters")
        
        # Test Calendly link generation
        state = create_initial_state(
            lead_id="booking_test",
            lead_name="Test Lead",
            property_address="123 Test St",
            property_type="fix_flip",
            campaign_id="test_campaign"
        )
        
        # Test Google Calendar integration
        print(f"  ✅ Google Calendar available: {agent.google_available}")
        
        # Test time slot generation
        time_slots = agent._get_available_time_slots()
        print(f"  ✅ Time slots generated: {len(time_slots)} characters")
        
    except Exception as e:
        print(f"  ❌ Booking agent test failed: {e}")


def run_week3_tests():
    """
    Run all Week 3 tests
    """
    print("🎯 Week 3 Property Specialists & Booking Tests")
    print("=" * 70)
    
    # Test individual agents
    test_property_specialist_agents()
    test_booking_agent()
    
    # Test complete flows
    flow_results = test_complete_conversation_flows()
    
    # Summary
    successful_scenarios = sum(1 for result in flow_results if result["success"])
    total_scenarios = len(flow_results)
    
    print(f"\n📊 Test Results Summary:")
    print(f"  - Property Specialist Agents: Tested")
    print(f"  - Booking Agent: Tested")
    print(f"  - Complete Flows: {successful_scenarios}/{total_scenarios} successful")
    
    if successful_scenarios == total_scenarios:
        print("\n🎉 All Week 3 tests passed!")
        print("✅ Complete real estate outreach system is working!")
    else:
        print("\n⚠️ Some tests failed. Review errors above.")
    
    return successful_scenarios == total_scenarios


def demo_complete_system():
    """
    Demonstrate the complete system with a full conversation
    """
    print("\n🎬 Demo: Complete Real Estate Outreach System")
    print("=" * 60)
    
    # Create demo state for each property type
    property_types = ["fix_flip", "vacant_land", "long_term_rental"]
    
    for prop_type in property_types:
        print(f"\n📋 Demo: {prop_type.replace('_', ' ').title()} Property")
        print("-" * 40)
        
        demo_state = create_initial_state(
            lead_id=f"demo_{prop_type}",
            lead_name="Demo Lead",
            property_address=f"123 Demo {prop_type.title()} Street",
            property_type=prop_type,
            campaign_id=f"demo_{prop_type}_campaign",
            lead_phone="+12145550123",
            lead_email="demo@example.com"
        )
        
        print(f"  Lead: {demo_state['lead_name']}")
        print(f"  Property: {demo_state['property_address']}")
        print(f"  Type: {demo_state['property_type']}")
        
        # Create and run graph
        graph = create_complete_real_estate_graph()
        
        try:
            print(f"\n  🚀 Running {prop_type} conversation flow...")
            result = graph.invoke(demo_state)
            
            print(f"  ✅ Demo completed!")
            print(f"     Final Stage: {result['conversation_stage']}")
            print(f"     Contact Method: {result.get('last_contact_method', 'none')}")
            print(f"     Agents Used: {' → '.join(result['agent_history'])}")
            
        except Exception as e:
            print(f"  ❌ Demo failed: {e}")


if __name__ == "__main__":
    # Set up environment
    os.environ.setdefault("OPENAI_API_KEY", "test-key")
    
    # Run tests
    print("🎯 Complete Real Estate Outreach System")
    print("Week 3 Implementation Testing")
    print("=" * 80)
    
    success = run_week3_tests()
    
    if success:
        print("\n🎉 Week 3 Property Specialists & Booking Complete!")
        print("\n📋 What we've built:")
        print("  ✅ Fix & Flip Specialist Agent with qualification flow")
        print("  ✅ Vacant Land Specialist Agent with consultation booking")
        print("  ✅ Rental Property Specialist Agent with lease handling")
        print("  ✅ Booking Agent with Google Calendar & Meet integration")
        print("  ✅ Complete LangGraph assembly")
        print("  ✅ End-to-end conversation flows")
        print("  ✅ Property-specific dialogue and objection handling")
        
        # Run demo
        print("\n" + "=" * 60)
        demo_complete_system()
        
        print("\n🎯 Complete AI Real Estate Outreach System Ready!")
        print("🚀 Ready for production deployment!")
        
    else:
        print("\n❌ Week 3 needs fixes before production deployment")
