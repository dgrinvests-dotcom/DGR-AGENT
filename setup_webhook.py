"""
Quick Webhook Setup with ngrok
Expose your local server to receive Telnyx webhooks
"""

import subprocess
import time
import requests
import json

def setup_ngrok_webhook():
    """Set up ngrok tunnel and configure Telnyx webhook"""
    print("🔗 Setting up webhook with ngrok...")
    
    # Step 1: Check if ngrok is installed
    try:
        result = subprocess.run(['ngrok', 'version'], capture_output=True, text=True)
        print(f"✅ ngrok found: {result.stdout.strip()}")
    except FileNotFoundError:
        print("❌ ngrok not found!")
        print("\n📥 Install ngrok:")
        print("1. Go to https://ngrok.com/download")
        print("2. Download and extract ngrok.exe")
        print("3. Put ngrok.exe in your PATH or current directory")
        print("4. Run: ngrok authtoken YOUR_TOKEN (sign up for free)")
        return False
    
    # Step 2: Start ngrok tunnel
    print("\n🚀 Starting ngrok tunnel...")
    print("📋 Your FastAPI server should be running on port 8000")
    
    # Start ngrok in background
    try:
        ngrok_process = subprocess.Popen(
            ['ngrok', 'http', '8000', '--log=stdout'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print("⏳ Waiting for ngrok to start...")
        time.sleep(3)
        
        # Get ngrok URL
        try:
            response = requests.get('http://localhost:4040/api/tunnels')
            tunnels = response.json()
            
            if tunnels['tunnels']:
                public_url = tunnels['tunnels'][0]['public_url']
                webhook_url = f"{public_url}/webhooks/telnyx"
                
                print(f"✅ ngrok tunnel active!")
                print(f"🌐 Public URL: {public_url}")
                print(f"🔗 Webhook URL: {webhook_url}")
                
                print(f"\n📋 NEXT STEPS:")
                print(f"1. Go to Telnyx Portal: https://portal.telnyx.com/")
                print(f"2. Navigate to: Messaging → Messaging Profiles")
                print(f"3. Edit your profile: Real Estate Outreach Profile")
                print(f"4. Set Outbound Webhook URL to:")
                print(f"   {webhook_url}")
                print(f"5. Save the changes")
                print(f"\n🧪 Then test by sending SMS to: +17325320590")
                
                return webhook_url
                
            else:
                print("❌ No ngrok tunnels found")
                return False
                
        except Exception as e:
            print(f"❌ Could not get ngrok URL: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Could not start ngrok: {e}")
        return False

def add_webhook_endpoint():
    """Add webhook endpoint to FastAPI server"""
    print("\n🔧 Adding webhook endpoint to your FastAPI server...")
    
    webhook_code = '''
# Add this webhook endpoint to handle incoming SMS
@app.post("/webhooks/telnyx")
async def telnyx_webhook(request: Request):
    """Handle incoming Telnyx webhooks (SMS messages)"""
    try:
        payload = await request.body()
        data = json.loads(payload)
        
        print(f"📱 Received webhook: {data}")
        
        # Check if it's an SMS message
        if data.get("data", {}).get("event_type") == "message.received":
            message_data = data["data"]["payload"]
            
            from_number = message_data.get("from", {}).get("phone_number")
            message_text = message_data.get("text")
            to_number = message_data.get("to", [{}])[0].get("phone_number")
            
            print(f"📨 SMS from {from_number}: {message_text}")
            
            # Process the message through your AI system
            # This will trigger the LangGraph conversation flow
            await process_incoming_sms(from_number, message_text, to_number)
            
        return {"status": "received"}
        
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return {"status": "error", "message": str(e)}

async def process_incoming_sms(from_number: str, message: str, to_number: str):
    """Process incoming SMS through the AI system"""
    try:
        # Import your LangGraph system
        from langgraph_complete import create_complete_real_estate_graph
        from schemas.agent_state import create_initial_state
        
        # Find or create lead based on phone number
        conn = get_db_connection()
        
        # Look for existing lead
        lead = conn.execute(
            "SELECT * FROM leads WHERE phone = ?", (from_number,)
        ).fetchone()
        
        if lead:
            # Create state for existing lead
            state = create_initial_state(
                lead_id=lead[0],
                lead_name=f"{lead[1]} {lead[2]}",
                property_address=lead[5],
                property_type=lead[6],
                campaign_id=lead[7],
                lead_phone=from_number,
                lead_email=lead[4],
                incoming_message=message
            )
        else:
            # Create new lead
            lead_id = str(uuid.uuid4())
            state = create_initial_state(
                lead_id=lead_id,
                lead_name="New Lead",
                property_address="Unknown Property",
                property_type="fix_flip",
                campaign_id="incoming",
                lead_phone=from_number,
                incoming_message=message
            )
        
        # Run the conversation through LangGraph
        graph = create_complete_real_estate_graph()
        result = graph.invoke(state)
        
        print(f"✅ Processed message through AI system")
        print(f"📊 Result: {result.get('conversation_stage', 'unknown')}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error processing SMS: {e}")
'''
    
    print("📝 Add this code to your database_main_new.py file:")
    print("=" * 60)
    print(webhook_code)
    print("=" * 60)

if __name__ == "__main__":
    print("🔗 Webhook Setup for AI Real Estate Agent")
    print("This will expose your local server to receive SMS messages")
    print()
    
    # Set up ngrok
    webhook_url = setup_ngrok_webhook()
    
    if webhook_url:
        print(f"\n🎉 Webhook setup ready!")
        print(f"🔗 Your webhook URL: {webhook_url}")
        
        # Show how to add webhook endpoint
        add_webhook_endpoint()
        
        print(f"\n⚠️ IMPORTANT:")
        print(f"- Keep this terminal open (ngrok tunnel)")
        print(f"- Add the webhook endpoint code to database_main_new.py")
        print(f"- Configure the webhook URL in Telnyx Portal")
        print(f"- Then test SMS to +17325320590")
        
    else:
        print(f"\n❌ Webhook setup failed")
        print(f"Try installing ngrok first")
