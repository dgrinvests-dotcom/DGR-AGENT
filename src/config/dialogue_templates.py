"""
Dsrc/config/dialogue_templates.py for different property types and conversation scenarios
Based on project documentation and proven dialogue flows
"""

from enum import Enum
from typing import Dict, List, Any

class PropertyType(Enum):
    FIX_FLIP = "fix_flip"
    RENTAL = "rental"
    VACANT_LAND = "vacant_land"

class ConversationType(Enum):
    INITIAL_OUTREACH = "initial_outreach"
    QUALIFICATION = "qualification"
    FOLLOW_UP = "follow_up"
    OBJECTION_HANDLING = "objection_handling"
    APPOINTMENT_BOOKING = "appointment_booking"
    NO_SHOW_FOLLOW_UP = "no_show_follow_up"
    MISSED_CALL_FOLLOW_UP = "missed_call_follow_up"
    REQUESTED_DATE_FOLLOW_UP = "requested_date_follow_up"

# Fix & Flip Property Templates (Based on Project Documentation)
FIX_FLIP_TEMPLATES = {
    "initial_outreach": [
        "Hey {first_name}, I saw you might be the owner of {property_address} — would you be open to a no-obligation cash offer for the property?",
        "We buy homes as-is and can close on your timeline. Just wanted to see if that's something you'd consider?"
    ],
    
    "qualification": [
        "Great! I just need a few quick details to see if it's a fit. Is the property currently vacant, rented, or owner-occupied?",
        "And how's the condition? Any recent repairs or major issues we should know about?",
        "Thanks for the info! Based on what you shared, we may be able to make a fair cash offer. Want to schedule a quick call to go over next steps and your offer? You can pick a time here: {booking_link}"
    ],
    
    "offer_inquiry": [
        "Totally fair question! In order to give you the best and most accurate cash offer, we just need a bit more info about the property — and ideally a quick walkthrough.",
        "Is the property currently vacant, rented, or owner-occupied? That helps us tailor the offer to your situation.",
        "And how's the condition of the home? Any major repairs or updates done recently?",
        "Thanks for sharing that! Once we have the full picture, we can line up a cash offer that reflects the property's true value. Want to book a quick call to go over everything? Here's the link to pick a time: {booking_link}"
    ],
    
    "follow_up": [
        "Just checking in — if you're at all curious what a cash offer might look like for {property_address}, I'd be happy to get that started. Totally no pressure.",
        "Still open to selling {property_address}? We make fair cash offers and cover closing costs. Let me know if you'd like to chat or want the offer sent over."
    ],
    
    "objection_handling": {
        "price_concern": "I understand price is important. Our offers are based on current market conditions and the property's condition. Would you like to hear what factors we consider?",
        "timing_concern": "No rush at all! We can work with your timeline. When would be a better time to discuss this?",
        "trust_concern": "I completely understand. We're a local company and can provide references from recent sellers. Would that help?"
    },
    
    "appointment_booking": [
        "Perfect! Let's schedule a quick 15-minute call to discuss your property and next steps.",
        "I have availability this week. What works better for you - mornings or afternoons?"
    ],
    
    "missed_call_follow_up": [
        "Hi {first_name}, this is Derek's assistant. I noticed we missed our call about your property at {property_address} yesterday. Totally understand schedules get busy. Would you like to reschedule a quick 15-minute call? Here's the link to pick a time: {booking_link}.",
        "Just checking in, {first_name}. Derek still has interest in your property at {property_address}. If the timing is better this week or next, I can help find a slot that works. Would you prefer afternoons or evenings?",
        "Hi {first_name}, I don't want to bother you, but Derek's calendar is open for a few more spots this week. Should I hold one for you, or check back later in the year?"
    ],
    
    "requested_date_follow_up": [
        "Hi {first_name}, just following up like you asked about your property at {property_address}. Derek is still interested and ready to chat whenever works best. Would you like to schedule a quick call this week? {booking_link}.",
        "Hey {first_name}, circling back on our follow-up. No pressure at all—just making sure I reach you at a good time. Should I hold a spot on Derek's calendar, or check back another time?",
        "Hi {first_name}, I'll close my file for now unless you'd like to revisit selling {property_address}. If circumstances change, Derek would be glad to reconnect and make a cash offer."
    ]
}

# Vacant Land Templates (Based on Project Documentation)
VACANT_LAND_TEMPLATES = {
    "initial_outreach": [
        "Hi {first_name}, this is Derek. I'm buying vacant land in {county} and noticed you own a parcel near {nearest_town}. Would you consider a cash offer if it was simple and hassle-free? (If not interested, just let me know. Reply STOP to opt out.)"
    ],
    
    "qualification": [
        "Great! To put something together that makes sense, could I ask a few quick questions about the property? Won't take long.",
        "Do you know roughly how many acres or lot size your parcel is?",
        "Does it have road access, or is it landlocked?",
        "Any idea if utilities (water, power, septic/sewer) are nearby?",
        "Are there any back taxes, liens, or HOA fees tied to the land?",
        "If we agreed on a fair cash price, what's the ballpark amount you'd want?"
    ],
    
    "appointment_booking": [
        "Perfect, thanks for sharing that. The next step is super simple: we'll do a quick 15-minute call where Derek can review your land details and give you a cash range. What's easier for you— afternoon or evening this week?",
        "Got it! I've booked you for {date_time}. You'll get a confirmation from our calendar. If anything changes, just reply here and we'll reschedule. Looking forward to it!"
    ],
    
    "not_interested": [
        "No problem at all, I appreciate the reply. If you ever reconsider selling your land in the future, feel free to reach out."
    ],
    
    "follow_up": [
        "Just checking in about your land near {nearest_town}. Any updates on your plans?",
        "Hi {first_name}, following up about your vacant land. Let me know if you'd like to discuss selling."
    ],
    
    "objection_handling": {
        "development_plans": "I understand you had development plans. Sometimes selling now and investing elsewhere can be more profitable. Would you like to explore that?",
        "family_land": "I respect that it's family land. I work with many families and can ensure it goes to someone who will appreciate it.",
        "holding_investment": "Land can be a great long-term investment. I can also provide market analysis to help you decide the best timing."
    }
}

# Long-Term Rental Templates
RENTAL_TEMPLATES = {
    "initial_outreach": [
        "Hi {first_name}! I'm interested in your rental property at {property_address}. I buy investment properties for cash. Would you consider an offer? Text STOP to opt out."
    ],
    
    "qualification": [
        "Excellent! Is the property currently rented? What's the monthly income?",
        "Thanks. Are you dealing with any tenant or management issues?",
        "I'd love to discuss how I can help. When's a good time for a brief call?",
        "I specialize in rental properties and can close quickly. Here's my calendar: {booking_link}"
    ],
    
    "follow_up": [
        "Hi {first_name}, following up about your rental property at {property_address}. Any changes in your situation?",
        "Just checking in about your investment property. Let me know if you'd like to discuss selling options."
    ],
    
    "objection_handling": {
        "good_income": "I understand it's producing good income. I factor rental income into my offers and can often pay more than traditional buyers because I'm keeping it as a rental.",
        "tenant_occupied": "Tenant-occupied properties are actually my specialty. I can take over the existing lease and handle everything.",
        "market_timing": "I get it - timing the market is tricky. I can provide a current market analysis to help you decide."
    }
}

# Compliance Templates (Based on Project Documentation)
COMPLIANCE_TEMPLATES = {
    "opt_out_confirmation": "You have been removed from our contact list. Thank you.",
    "opt_out_instructions": "Reply STOP to opt out.",
    "sender_identification": "This is Derek's assistant.",
    "business_hours_message": "Thanks for your message! Our business hours are 8 AM - 8 PM EST. We'll respond during business hours.",
    "error_message": "I apologize, but I'm having technical difficulties. Can you please try again?"
}

# Follow-up Rules (Based on Project Documentation)
FOLLOW_UP_RULES = {
    "missed_call": {
        "max_attempts": 3,
        "intervals": [1, 3, 7],  # days
        "stop_after_no_response": True
    },
    "requested_date": {
        "max_attempts": 3,
        "intervals": [0, 4, 7],  # days (0 = same day)
        "stop_after_no_response": True
    },
    "general": {
        "max_attempts": 2,
        "intervals": [2, 4],  # days
        "stop_after_no_response": True
    }
}

# Combine all templates
DIALOGUE_TEMPLATES = {
    PropertyType.FIX_FLIP: FIX_FLIP_TEMPLATES,
    PropertyType.RENTAL: RENTAL_TEMPLATES,
    PropertyType.VACANT_LAND: VACANT_LAND_TEMPLATES,
    "compliance": COMPLIANCE_TEMPLATES,
    "follow_up_rules": FOLLOW_UP_RULES
}

def get_template(property_type: PropertyType, template_key: str) -> List[str]:
    """Get a specific template for a property type"""
    templates = DIALOGUE_TEMPLATES.get(property_type, {})
    return templates.get(template_key, [])

def get_qualification_flow(property_type: PropertyType) -> List[str]:
    """Get qualification questions for a property type"""
    return get_template(property_type, "qualification")

def get_follow_up_sequence(property_type: PropertyType, sequence_type: str) -> List[str]:
    """Get follow-up sequence for a property type and situation"""
    if sequence_type == "missed_call":
        return get_template(property_type, "missed_call_follow_up")
    elif sequence_type == "requested_date":
        return get_template(property_type, "requested_date_follow_up")
    else:
        return get_template(property_type, "follow_up")

def get_objection_response(property_type: PropertyType, objection_type: str) -> str:
    """Get response to common objections"""
    templates = DIALOGUE_TEMPLATES.get(property_type, {})
    responses = templates.get("objection_handling", {})
    return responses.get(objection_type, "I understand your concern. Let me see how I can help address that.")

def get_compliance_message(message_type: str) -> str:
    """Get compliance-related messages"""
    return COMPLIANCE_TEMPLATES.get(message_type, "")

def get_follow_up_rules(follow_up_type: str) -> Dict[str, Any]:
    """Get follow-up rules for different scenarios"""
    return FOLLOW_UP_RULES.get(follow_up_type, FOLLOW_UP_RULES["general"])

# Example usage and testing
if __name__ == "__main__":
    # Test template access
    flip_initial = get_template(PropertyType.FIX_FLIP, "initial_outreach")
    print(f"Fix & Flip Initial: {flip_initial}")
    
    land_qualification = get_qualification_flow(PropertyType.VACANT_LAND)
    print(f"Land Qualification: {len(land_qualification)} steps")
    
    missed_call_followup = get_follow_up_sequence(PropertyType.FIX_FLIP, "missed_call")
    print(f"Missed Call Follow-up: {len(missed_call_followup)} messages")
    
    compliance_opt_out = get_compliance_message("opt_out_confirmation")
    print(f"Opt-out message: {compliance_opt_out}")
