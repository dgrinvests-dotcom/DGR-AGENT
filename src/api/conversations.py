from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import uuid
from datetime import datetime
from ..agents.conversation_agent import ConversationAgent
from ..models import Conversation, ConversationStatus

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

class MessageSend(BaseModel):
    message: str

# Mock data storage (replace with actual database)
conversations_db = {}

@router.get("/")
async def get_conversations(
    lead_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 25
):
    """Get conversations with optional filtering and pagination"""
    try:
        # TODO: Replace with actual database query
        mock_conversations = [
            {
                "id": "1",
                "lead_id": "1",
                "status": "active",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T11:45:00Z",
                "messages": [
                    {
                        "id": "msg1",
                        "direction": "outbound",
                        "content": "Hi John! I saw you might be interested in selling your property at 123 Main St. I'd love to help you with a quick, hassle-free sale. Are you looking to sell soon?",
                        "timestamp": "2024-01-15T10:30:00Z",
                        "method": "sms",
                        "ai_generated": True
                    },
                    {
                        "id": "msg2",
                        "direction": "inbound",
                        "content": "Yes, I'm interested. What can you offer?",
                        "timestamp": "2024-01-15T11:15:00Z",
                        "method": "sms",
                        "ai_generated": False
                    },
                    {
                        "id": "msg3",
                        "direction": "outbound",
                        "content": "Great! I'd love to discuss this further. Based on what I can see, properties in your area are moving quickly. Would you be available for a brief call this week to discuss your timeline and what you're looking for?",
                        "timestamp": "2024-01-15T11:45:00Z",
                        "method": "sms",
                        "ai_generated": True
                    }
                ]
            },
            {
                "id": "2",
                "lead_id": "2",
                "status": "qualified",
                "created_at": "2024-01-16T14:20:00Z",
                "updated_at": "2024-01-16T15:30:00Z",
                "messages": [
                    {
                        "id": "msg4",
                        "direction": "outbound",
                        "content": "Hi Sarah! I noticed you have a vacant land property that might be perfect for our investment needs. Are you considering selling?",
                        "timestamp": "2024-01-16T14:20:00Z",
                        "method": "sms",
                        "ai_generated": True
                    },
                    {
                        "id": "msg5",
                        "direction": "inbound",
                        "content": "Yes, I've been thinking about it. It's just sitting there unused.",
                        "timestamp": "2024-01-16T14:45:00Z",
                        "method": "sms",
                        "ai_generated": False
                    },
                    {
                        "id": "msg6",
                        "direction": "outbound",
                        "content": "That's exactly what we specialize in! We can make you a fair cash offer and handle all the paperwork. Would you like to schedule a quick call to discuss the details?",
                        "timestamp": "2024-01-16T15:00:00Z",
                        "method": "sms",
                        "ai_generated": True
                    },
                    {
                        "id": "msg7",
                        "direction": "inbound",
                        "content": "Sure, that sounds good. When works for you?",
                        "timestamp": "2024-01-16T15:30:00Z",
                        "method": "sms",
                        "ai_generated": False
                    }
                ]
            }
        ]
        
        # Apply filters
        filtered_conversations = mock_conversations
        if lead_id:
            filtered_conversations = [c for c in filtered_conversations if c.get("lead_id") == lead_id]
        if status:
            filtered_conversations = [c for c in filtered_conversations if c.get("status") == status]
        
        # Apply pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_conversations = filtered_conversations[start_idx:end_idx]
        
        return {
            "conversations": paginated_conversations,
            "total": len(filtered_conversations)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get a specific conversation"""
    try:
        # TODO: Replace with actual database query
        conversations_response = await get_conversations()
        conversation = next((c for c in conversations_response["conversations"] if c["id"] == conversation_id), None)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/lead/{lead_id}")
async def get_conversations_by_lead(lead_id: str):
    """Get all conversations for a specific lead"""
    try:
        # TODO: Replace with actual database query
        conversations_response = await get_conversations(lead_id=lead_id)
        return conversations_response["conversations"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{lead_id}/message")
async def send_message(lead_id: str, message_data: MessageSend):
    """Send a message to a lead"""
    try:
        # TODO: Implement actual message sending logic
        # This should integrate with the ConversationAgent and messaging services
        
        # For now, return a mock response
        new_message = {
            "id": str(uuid.uuid4()),
            "direction": "outbound",
            "content": message_data.message,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "method": "sms",
            "ai_generated": False
        }
        
        return {
            "success": True,
            "message": "Message sent successfully",
            "data": new_message
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
