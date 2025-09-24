 
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path
import uvicorn
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime
import json
import sqlite3
import uuid
# Email monitoring removed - using direct agent communication

app = FastAPI(title="AI Real Estate Outreach Agent", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "https://web-production-0c70c.up.railway.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve React frontend
frontend_path = Path(__file__).parent.parent / "frontend" / "build"

if frontend_path.exists():
    # Serve static files (CSS, JS, images)
    app.mount("/static", StaticFiles(directory=frontend_path / "static"), name="static")
    
    # Serve React app for all non-API routes
    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        # If it's an API route, let FastAPI handle it
        if full_path.startswith("api/") or full_path.startswith("webhooks/") or full_path.startswith("docs") or full_path.startswith("openapi.json") or full_path.startswith("health"):
            raise HTTPException(status_code=404, detail="Not found")
        
        # Check if file exists in build directory
        file_path = frontend_path / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        
        # Otherwise serve index.html (React Router will handle routing)
        return FileResponse(frontend_path / "index.html")

# Database helper functions
def get_db_connection():
    conn = sqlite3.connect("agent_estate.db")
    conn.row_factory = sqlite3.Row
    return conn

def dict_from_row(row):
    return dict(row) if row else None

# Data models
class CampaignCreate(BaseModel):
    name: str
    property_type: str
    config: Dict[str, Any]

class LeadCreate(BaseModel):
    first_name: str
    last_name: str
    phone: str
    email: Optional[str] = None
    property_address: str
    property_type: str
    campaign_id: Optional[str] = None
    property_value: Optional[float] = None
    condition: Optional[str] = None
    notes: Optional[str] = None

# Simulation Chat API
class SimulateChatRequest(BaseModel):
    from_number: str
    text: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    property_address: Optional[str] = None
    property_type: Optional[str] = "fix_flip"
    campaign_id: Optional[str] = "incoming_response"

@app.post("/simulate/chat")
async def simulate_chat(req: SimulateChatRequest):
    """
    Simulate an inbound SMS without sending real messages.
    Runs the full LangGraph flow but forces SMS simulation mode for this request only.
    """
    from langgraph_complete import create_complete_real_estate_graph
    from schemas.agent_state import create_initial_state
    from langchain_core.messages import HumanMessage

    from_number = req.from_number
    message = req.text

    conn = get_db_connection()
    try:
        lead = conn.execute(
            "SELECT * FROM leads WHERE phone = ?", (from_number,)
        ).fetchone()

        if lead:
            lead_row = dict_from_row(lead)
            state = create_initial_state(
                lead_id=lead_row.get("id"),
                lead_name=f"{lead_row.get('first_name','')} {lead_row.get('last_name','')}".strip() or "Unknown Lead",
                property_address=lead_row.get("property_address", "Unknown Property"),
                property_type=lead_row.get("property_type", req.property_type or "fix_flip"),
                campaign_id=lead_row.get("campaign_id", req.campaign_id or "incoming_response"),
                lead_phone=from_number,
                lead_email=lead_row.get("email", "") or ""
            )
            # Load persisted continuity
            persisted_stage = lead_row.get("conversation_stage")
            if persisted_stage:
                state["conversation_stage"] = persisted_stage
            else:
                state["conversation_stage"] = "qualifying"
            try:
                persisted_q = lead_row.get("qualification_data")
                if persisted_q:
                    import json as _json
                    state["qualification_data"] = _json.loads(persisted_q)
            except Exception:
                pass
            # Load persisted messages if available
            try:
                persisted_msgs = lead_row.get("conversation_messages")
                if persisted_msgs:
                    msgs_list = json.loads(persisted_msgs)
                    from langchain_core.messages import HumanMessage as _HM, AIMessage as _AM
                    state["messages"] = []
                    for m in msgs_list:
                        role = (m.get("role") or "").lower()
                        content = m.get("content", "")
                        if role == "human":
                            state["messages"].append(_HM(content=content))
                        elif role == "ai":
                            state["messages"].append(_AM(content=content))
            except Exception:
                pass
        else:
            # Create new lead for simulation
            lead_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO leads (id, first_name, last_name, phone, email, property_address,
                                   property_type, campaign_id, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'responding', CURRENT_TIMESTAMP)
                """,
                (
                    lead_id,
                    req.first_name or "Unknown",
                    req.last_name or "Lead",
                    from_number,
                    "",
                    req.property_address or "Unknown Property",
                    req.property_type or "fix_flip",
                    req.campaign_id or "incoming_response",
                ),
            )
            conn.commit()
            state = create_initial_state(
                lead_id=lead_id,
                lead_name=f"{req.first_name or 'Unknown'} {req.last_name or 'Lead'}",
                property_address=req.property_address or "Unknown Property",
                property_type=req.property_type or "fix_flip",
                campaign_id=req.campaign_id or "incoming_response",
                lead_phone=from_number,
            )
            state["conversation_stage"] = "qualifying"
            state["messages"] = []

        # Add inbound message (append, do not overwrite)
        if "messages" not in state or not isinstance(state["messages"], list):
            state["messages"] = []
        state["messages"].append(HumanMessage(content=message))
        state["conversation_mode"] = "inbound_response"
        state["incoming_message"] = message
        state["sms_simulation"] = True

        # Run graph (simulation mode active for SMS agent)
        graph = create_complete_real_estate_graph()
        result = graph.invoke(state)

        # Persist continuity fields
        try:
            # Serialize messages for persistence
            msgs_to_save = result.get("messages", state.get("messages", [])) or []
            serialized_msgs = []
            for m in msgs_to_save:
                c = getattr(m, "content", None)
                if not isinstance(c, str):
                    c = str(c)
                role = "ai" if "AIMessage" in type(m).__name__ else "human"
                serialized_msgs.append({"role": role, "content": c})

            conn.execute(
                """
                UPDATE leads
                SET conversation_stage = ?, qualification_data = ?, status = 'responding', conversation_messages = ?
                WHERE phone = ?
                """,
                (
                    result.get("conversation_stage", state.get("conversation_stage", "qualifying")),
                    json.dumps(result.get("qualification_data", state.get("qualification_data", {}))),
                    json.dumps(serialized_msgs),
                    from_number,
                ),
            )
            conn.commit()
        except Exception as _e:
            print(f"⚠️ Failed to persist conversation state (simulate): {_e}")

        # Prepare response with fallbacks
        response_text = result.get("generated_response") or result.get("response_message") or ""
        if not response_text:
            try:
                msgs = result.get("messages", []) or []
                # Find last AI-like message with content
                for m in reversed(msgs):
                    content = getattr(m, "content", None)
                    if isinstance(content, str) and content.strip():
                        response_text = content
                        break
            except Exception:
                pass
        return {
            "success": True,
            "response": response_text,
            "conversation_stage": result.get("conversation_stage", state.get("conversation_stage")),
            "qualification_data": result.get("qualification_data", state.get("qualification_data", {})),
            "simulation": True,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

@app.get("/simulate/ui", response_class=HTMLResponse)
async def simulate_ui():
    """Serve a minimal HTML UI for simulation without building the React app."""
    return """
    <!DOCTYPE html>
    <html lang=\"en\">
    <head>
      <meta charset=\"UTF-8\" />
      <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
      <title>Simulation Chat</title>
      <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 0; background: #f6f7fb; }
        .container { max-width: 960px; margin: 24px auto; padding: 16px; }
        .card { background: #fff; border: 1px solid #eee; border-radius: 8px; padding: 16px; }
        .row { display: flex; gap: 8px; margin-bottom: 8px; }
        .row > * { flex: 1; }
        .chat { border: 1px solid #eee; border-radius: 8px; padding: 12px; background: #fafafa; height: 360px; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; }
        .bubble { display:inline-block; padding:10px 12px; border-radius:12px; margin:2px 0; max-width:80%; white-space:pre-wrap; word-break: break-word; }
        .user { background:#1976d2; color:#fff; margin-left:auto; }
        .agent { background:#e0e0e0; color:#222; margin-right:auto; }
        .state { font-family: monospace; font-size: 12px; white-space: pre-wrap; word-break: break-word; background: #f3f3f3; padding: 8px; border-radius: 6px; }
        button { padding: 8px 12px; }
        input, select { padding: 8px; }
      </style>
    </head>
    <body>
      <div class=\"container\">
        <h2>Simulation Chat (No SMS Cost)</h2>
        <div class=\"card\">
          <div class=\"row\">
            <input id=\"from\" placeholder=\"From Number (+1...)\" value=\"+16095551234\" />
            <input id=\"first\" placeholder=\"First Name\" value=\"Test\" />
            <input id=\"last\" placeholder=\"Last Name\" value=\"Lead\" />
          </div>
          <div class=\"row\">
            <input id=\"addr\" placeholder=\"Property Address\" value=\"123 Main St, Dallas, TX\" />
            <select id=\"ptype\">
              <option value=\"fix_flip\" selected>Fix & Flip</option>
              <option value=\"vacant_land\">Vacant Land</option>
              <option value=\"long_term_rental\">Long-term Rental</option>
            </select>
            <input id=\"camp\" placeholder=\"Campaign ID\" value=\"incoming_response\" />
          </div>
          <div id=\"chat\" class=\"chat\"></div>
          <div class=\"row\">
            <input id=\"msg\" placeholder=\"Type message...\" />
            <button id=\"send\">Send</button>
          </div>
          <div class=\"row\">
            <div style=\"flex:1\">
              <strong>Stage</strong>
              <div id=\"stage\">—</div>
            </div>
            <div style=\"flex:2\">
              <strong>Qualification Data</strong>
              <div id=\"qdata\" class=\"state\">{}</div>
            </div>
          </div>
        </div>
      </div>
      <script>
        const chat = document.getElementById('chat');
        const msg = document.getElementById('msg');
        const from = document.getElementById('from');
        const first = document.getElementById('first');
        const last = document.getElementById('last');
        const addr = document.getElementById('addr');
        const ptype = document.getElementById('ptype');
        const camp = document.getElementById('camp');
        const stage = document.getElementById('stage');
        const qdata = document.getElementById('qdata');
        const sendBtn = document.getElementById('send');

        function addBubble(role, text) {
          const div = document.createElement('div');
          div.className = 'bubble ' + (role === 'user' ? 'user' : 'agent');
          div.textContent = text;
          chat.appendChild(div);
          chat.scrollTop = chat.scrollHeight;
        }

        async function simulate() {
          const body = {
            from_number: from.value,
            text: msg.value,
            first_name: first.value,
            last_name: last.value,
            property_address: addr.value,
            property_type: ptype.value,
            campaign_id: camp.value
          };
          try {
            addBubble('user', body.text);
            msg.value = '';
            const res = await fetch('/simulate/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
            const data = await res.json();
            if (data.success && data.response) addBubble('agent', data.response);
            stage.textContent = data.conversation_stage || '—';
            qdata.textContent = JSON.stringify(data.qualification_data || {}, null, 2);
          } catch (e) {
            alert('Request failed');
          }
        }

        sendBtn.addEventListener('click', simulate);
        msg.addEventListener('keydown', (e) => { if (e.key === 'Enter') simulate(); });
      </script>
    </body>
    </html>
    """

# Initialize database
class Database:
    def __init__(self, db_path: str = "agent_estate.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create campaigns table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS campaigns (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                property_type TEXT NOT NULL,
                status TEXT DEFAULT 'created',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                config TEXT,
                description TEXT
            )
        ''')
        
        # Create leads table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leads (
                id TEXT PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                property_address TEXT,
                property_type TEXT,
                status TEXT DEFAULT 'new',
                campaign_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                property_value REAL,
                condition TEXT,
                notes TEXT,
                FOREIGN KEY (campaign_id) REFERENCES campaigns (id)
            )
        ''')
        
        # Add missing columns for conversation persistence (safe no-op if they already exist)
        try:
            cursor.execute("ALTER TABLE leads ADD COLUMN conversation_stage TEXT")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE leads ADD COLUMN qualification_data TEXT")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE leads ADD COLUMN conversation_messages TEXT")
        except Exception:
            pass
        
        # Create conversations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                lead_id TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads (id)
            )
        ''')
        
        # Create messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                direction TEXT,
                content TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                method TEXT DEFAULT 'email',
                ai_generated BOOLEAN DEFAULT 0,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id)
            )
        ''')
        
        conn.commit()
        conn.close()

# Initialize database
db = Database("agent_estate.db")

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    print("🚀 Starting AI Real Estate Agent Backend...")
    
    # Initialize database schema
    from init_database import init_complete_database
    init_success = init_complete_database()
    if init_success:
        print("✅ Database schema initialized")
    else:
        print("❌ Database initialization failed")
    
    print("✅ System ready for real estate outreach")

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event"""
    print("🛑 Shutting down AI Real Estate Agent Backend...")

# API Routes
@app.get("/")
async def root():
    return {"message": "AI Real Estate Outreach Agent API - Database Version"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Dashboard endpoints - Real database data
@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    conn = get_db_connection()
    
    # Get real statistics from database
    total_leads = conn.execute("SELECT COUNT(*) as count FROM leads").fetchone()["count"]
    active_conversations = conn.execute("SELECT COUNT(*) as count FROM conversations WHERE status = 'active'").fetchone()["count"]
    total_campaigns = conn.execute("SELECT COUNT(*) as count FROM campaigns").fetchone()["count"]
    active_campaigns = conn.execute("SELECT COUNT(*) as count FROM campaigns WHERE status = 'active'").fetchone()["count"]
    appointments_today = conn.execute("SELECT COUNT(*) as count FROM leads WHERE status = 'appointment_set' AND date(created_at) = date('now')").fetchone()["count"]
    
    # Calculate response rate (leads with conversations)
    leads_with_conversations = conn.execute("""
        SELECT COUNT(DISTINCT l.id) as count 
        FROM leads l 
        JOIN conversations c ON l.id = c.lead_id
    """).fetchone()["count"]
    
    response_rate = (leads_with_conversations / total_leads * 100) if total_leads > 0 else 0
    
    # Calculate conversion rate (leads with appointments)
    leads_with_appointments = conn.execute("SELECT COUNT(*) as count FROM leads WHERE status = 'appointment_set'").fetchone()["count"]
    conversion_rate = (leads_with_appointments / total_leads * 100) if total_leads > 0 else 0
    
    conn.close()
    
    return {
        "active_campaigns": active_campaigns,
        "total_leads": total_leads,
        "active_conversations": active_conversations,
        "appointments_today": appointments_today,
        "response_rate": round(response_rate, 1),
        "conversion_rate": round(conversion_rate, 1)
    }

@app.get("/api/dashboard/integrations")
async def get_integration_status():
    return {
        "telnyx": bool(os.getenv("TELNYX_API_KEY")),
        "google_meet": bool(os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")),
        "gmail": bool(os.getenv("GMAIL_ADDRESS") and os.getenv("GMAIL_APP_PASSWORD")),
        "openai": bool(os.getenv("OPENAI_API_KEY"))
    }

# Campaign endpoints - Real database data
@app.get("/api/campaigns")
async def get_campaigns():
    conn = get_db_connection()
    campaigns = conn.execute("""
        SELECT c.*, 
               COUNT(l.id) as total_leads,
               COUNT(CASE WHEN l.status != 'new' THEN 1 END) as contacted_leads,
               COUNT(CASE WHEN l.status IN ('responded', 'qualified', 'appointment_set') THEN 1 END) as responded_leads,
               COUNT(CASE WHEN l.status = 'appointment_set' THEN 1 END) as appointments_set
        FROM campaigns c
        LEFT JOIN leads l ON c.id = l.campaign_id
        GROUP BY c.id
        ORDER BY c.created_at DESC
    """).fetchall()
    
    result = []
    for campaign in campaigns:
        campaign_dict = dict(campaign)
        
        # Parse config JSON if it exists
        if campaign_dict.get('config'):
            try:
                campaign_dict['config'] = json.loads(campaign_dict['config'])
            except:
                campaign_dict['config'] = {}
        else:
            campaign_dict['config'] = {
                "max_daily_contacts": 50,
                "follow_up_days": [1, 3, 7, 14],
                "target_response_rate": 15.0,
                "quiet_hours_start": "21:00",
                "quiet_hours_end": "08:00"
            }
        
        # Calculate stats
        total_leads = campaign_dict.get('total_leads', 0)
        contacted_leads = campaign_dict.get('contacted_leads', 0)
        responded_leads = campaign_dict.get('responded_leads', 0)
        appointments_set = campaign_dict.get('appointments_set', 0)
        
        response_rate = (responded_leads / contacted_leads * 100) if contacted_leads > 0 else 0
        conversion_rate = (appointments_set / total_leads * 100) if total_leads > 0 else 0
        
        campaign_dict['stats'] = {
            "total_leads": total_leads,
            "contacted_leads": contacted_leads,
            "responded_leads": responded_leads,
            "appointments_set": appointments_set,
            "response_rate": round(response_rate, 1),
            "conversion_rate": round(conversion_rate, 1)
        }
        
        result.append(campaign_dict)
    
    conn.close()
    return result

@app.get("/api/campaigns/{campaign_id}")
async def get_campaign(campaign_id: str):
    conn = get_db_connection()
    campaign = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
    conn.close()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign_dict = dict(campaign)
    if campaign_dict.get('config'):
        try:
            campaign_dict['config'] = json.loads(campaign_dict['config'])
        except:
            campaign_dict['config'] = {}
    
    return campaign_dict

@app.post("/api/campaigns")
async def create_campaign(campaign: CampaignCreate):
    conn = get_db_connection()
    
    campaign_id = str(uuid.uuid4())
    config_json = json.dumps(campaign.config)
    
    conn.execute("""
        INSERT INTO campaigns (id, name, property_type, status, config)
        VALUES (?, ?, ?, 'created', ?)
    """, (campaign_id, campaign.name, campaign.property_type, config_json))
    
    conn.commit()
    
    # Get the created campaign
    new_campaign = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
    conn.close()
    
    campaign_dict = dict(new_campaign)
    campaign_dict['config'] = campaign.config
    campaign_dict['stats'] = {
        "total_leads": 0,
        "contacted_leads": 0,
        "responded_leads": 0,
        "appointments_set": 0,
        "response_rate": 0.0,
        "conversion_rate": 0.0
    }
    
    return campaign_dict

@app.put("/api/campaigns/{campaign_id}")
async def update_campaign(campaign_id: str, campaign_update: dict):
    conn = get_db_connection()
    
    # Check if campaign exists
    campaign = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
    if not campaign:
        conn.close()
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Build update query dynamically
    update_fields = []
    params = []
    
    if "name" in campaign_update:
        update_fields.append("name = ?")
        params.append(campaign_update["name"])
    if "property_type" in campaign_update:
        update_fields.append("property_type = ?")
        params.append(campaign_update["property_type"])
    if "config" in campaign_update:
        update_fields.append("config = ?")
        params.append(json.dumps(campaign_update["config"]))
    
    if update_fields:
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(campaign_id)
        query = f"UPDATE campaigns SET {', '.join(update_fields)} WHERE id = ?"
        conn.execute(query, params)
        conn.commit()
    
    # Get updated campaign
    updated_campaign = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
    conn.close()
    
    return dict(updated_campaign)

@app.delete("/api/campaigns/{campaign_id}")
async def delete_campaign(campaign_id: str):
    conn = get_db_connection()
    
    # Check if campaign exists
    campaign = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
    if not campaign:
        conn.close()
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Delete associated data
    # First get all conversations for leads in this campaign
    conversations = conn.execute("""
        SELECT c.id FROM conversations c
        JOIN leads l ON c.lead_id = l.id
        WHERE l.campaign_id = ?
    """, (campaign_id,)).fetchall()
    
    # Delete messages for these conversations
    for conv in conversations:
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conv["id"],))
    
    # Delete conversations
    conn.execute("""
        DELETE FROM conversations WHERE lead_id IN (
            SELECT id FROM leads WHERE campaign_id = ?
        )
    """, (campaign_id,))
    
    # Delete leads
    conn.execute("DELETE FROM leads WHERE campaign_id = ?", (campaign_id,))
    
    # Delete campaign
    conn.execute("DELETE FROM campaigns WHERE id = ?", (campaign_id,))
    
    conn.commit()
    conn.close()
    
    return {"success": True, "message": "Campaign and associated data deleted successfully"}

@app.post("/api/campaigns/{campaign_id}/start")
async def start_campaign(campaign_id: str):
    conn = get_db_connection()
    
    campaign = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
    if not campaign:
        conn.close()
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign["status"] not in ["created", "paused"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Campaign cannot be started from current status")
    
    conn.execute("UPDATE campaigns SET status = 'active', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (campaign_id,))
    conn.commit()
    conn.close()
    
    return {"success": True, "message": "Campaign started successfully"}

@app.post("/api/campaigns/{campaign_id}/pause")
async def pause_campaign(campaign_id: str):
    conn = get_db_connection()
    
    campaign = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
    if not campaign:
        conn.close()
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign["status"] != "active":
        conn.close()
        raise HTTPException(status_code=400, detail="Only active campaigns can be paused")
    
    conn.execute("UPDATE campaigns SET status = 'paused', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (campaign_id,))
    conn.commit()
    conn.close()
    
    return {"success": True, "message": "Campaign paused successfully"}

@app.post("/api/campaigns/{campaign_id}/stop")
async def stop_campaign(campaign_id: str):
    conn = get_db_connection()
    
    campaign = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
    if not campaign:
        conn.close()
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign["status"] in ["stopped", "completed"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Campaign is already stopped")
    
    conn.execute("UPDATE campaigns SET status = 'stopped', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (campaign_id,))
    conn.commit()
    conn.close()
    
    return {"success": True, "message": "Campaign stopped successfully"}

# Campaign execution endpoints
@app.post("/api/campaigns/{campaign_id}/execute")
async def execute_campaign(campaign_id: str):
    """Execute campaign - process new leads and send outreach"""
    import subprocess
    import threading
    
    conn = get_db_connection()
    campaign = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
    if not campaign:
        conn.close()
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Get new leads count
    new_leads = conn.execute("SELECT COUNT(*) as count FROM leads WHERE campaign_id = ? AND status = 'new'", (campaign_id,)).fetchone()["count"]
    conn.close()
    
    if new_leads == 0:
        return {"success": True, "message": "No new leads to process", "leads_processed": 0}
    
    # Execute campaign agent in background
    def run_campaign():
        try:
            result = subprocess.run([
                "python", "src/campaign_agent.py", "--campaign-id", campaign_id, "--once"
            ], capture_output=True, text=True, cwd=".")
            print(f"Campaign execution result: {result.stdout}")
        except Exception as e:
            print(f"Campaign execution error: {e}")
    
    # Start in background thread
    thread = threading.Thread(target=run_campaign)
    thread.daemon = True
    thread.start()
    
    return {"success": True, "message": f"Campaign execution started for {new_leads} leads", "leads_to_process": new_leads}

@app.get("/api/campaigns/{campaign_id}/status")
async def get_campaign_execution_status(campaign_id: str):
    """Get campaign execution status"""
    conn = get_db_connection()
    
    # Get campaign stats
    stats = conn.execute("""
        SELECT 
            COUNT(*) as total_leads,
            COUNT(CASE WHEN status = 'new' THEN 1 END) as new_leads,
            COUNT(CASE WHEN status = 'contacted' THEN 1 END) as contacted_leads,
            COUNT(CASE WHEN status IN ('responded', 'qualified') THEN 1 END) as responded_leads
        FROM leads WHERE campaign_id = ?
    """, (campaign_id,)).fetchone()
    
    conn.close()
    
    return {
        "campaign_id": campaign_id,
        "total_leads": stats["total_leads"],
        "new_leads": stats["new_leads"], 
        "contacted_leads": stats["contacted_leads"],
        "responded_leads": stats["responded_leads"],
        "is_processing": stats["new_leads"] > 0
    }

# Lead endpoints - Real database data
@app.get("/api/leads")
async def get_leads(
    campaign_id: Optional[str] = None,
    status: Optional[str] = None,
    property_type: Optional[str] = None,
    page: int = 1,
    limit: int = 25
):
    conn = get_db_connection()
    
    query = "SELECT * FROM leads WHERE 1=1"
    params = []
    
    if campaign_id:
        query += " AND campaign_id = ?"
        params.append(campaign_id)
    if status:
        query += " AND status = ?"
        params.append(status)
    if property_type:
        query += " AND property_type = ?"
        params.append(property_type)
    
    query += " ORDER BY created_at DESC"
    
    # Add pagination
    offset = (page - 1) * limit
    query += f" LIMIT {limit} OFFSET {offset}"
    
    leads = conn.execute(query, params).fetchall()
    total = conn.execute("SELECT COUNT(*) as count FROM leads").fetchone()["count"]
    
    conn.close()
    
    leads_list = [dict(lead) for lead in leads]
    
    return {"leads": leads_list, "total": total}

@app.get("/api/leads/{lead_id}")
async def get_lead(lead_id: str):
    conn = get_db_connection()
    lead = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    conn.close()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return dict(lead)

@app.post("/api/leads")
async def create_lead(lead: LeadCreate):
    conn = get_db_connection()
    
    lead_id = str(uuid.uuid4())
    conn.execute('''
        INSERT INTO leads 
        (id, first_name, last_name, phone, email, property_address, 
         property_type, status, campaign_id, property_value, condition, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        lead_id, lead.first_name, lead.last_name, lead.phone, lead.email,
        lead.property_address, lead.property_type, "new", lead.campaign_id,
        lead.property_value, lead.condition, lead.notes
    ))
    
    conn.commit()
    
    # Get the created lead
    new_lead = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    conn.close()
    
    return dict(new_lead)

@app.put("/api/leads/{lead_id}")
async def update_lead(lead_id: str, lead_update: dict):
    conn = get_db_connection()
    
    # Check if lead exists
    lead = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    if not lead:
        conn.close()
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Build update query dynamically
    update_fields = []
    params = []
    
    allowed_fields = ['first_name', 'last_name', 'phone', 'email', 'property_address', 
                     'property_type', 'status', 'campaign_id', 'property_value', 'condition', 'notes']
    
    for field in allowed_fields:
        if field in lead_update:
            update_fields.append(f"{field} = ?")
            params.append(lead_update[field])
    
    if update_fields:
        params.append(lead_id)
        query = f"UPDATE leads SET {', '.join(update_fields)} WHERE id = ?"
        conn.execute(query, params)
        conn.commit()
    
    # Get updated lead
    updated_lead = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    conn.close()
    
    return dict(updated_lead)

@app.delete("/api/leads/{lead_id}")
async def delete_lead(lead_id: str):
    conn = get_db_connection()
    
    # Check if lead exists
    lead = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
    if not lead:
        conn.close()
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Delete associated messages first
    conversations = conn.execute("SELECT id FROM conversations WHERE lead_id = ?", (lead_id,)).fetchall()
    for conv in conversations:
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conv["id"],))
    
    # Delete conversations
    conn.execute("DELETE FROM conversations WHERE lead_id = ?", (lead_id,))
    
    # Delete lead
    conn.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
    
    conn.commit()
    conn.close()
    
    return {"success": True, "message": "Lead and associated data deleted successfully"}

# Conversation endpoints - Real database data
@app.get("/api/conversations")
async def get_conversations(
    lead_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 25
):
    conn = get_db_connection()
    
    query = """
        SELECT c.*, l.first_name, l.last_name, l.email, l.phone, l.property_address
        FROM conversations c
        JOIN leads l ON c.lead_id = l.id
        WHERE 1=1
    """
    params = []
    
    if lead_id:
        query += " AND c.lead_id = ?"
        params.append(lead_id)
    if status:
        query += " AND c.status = ?"
        params.append(status)
    
    query += " ORDER BY c.updated_at DESC"
    
    conversations = conn.execute(query, params).fetchall()
    
    # Get messages for each conversation
    conversations_with_messages = []
    for conv in conversations:
        messages = conn.execute("""
            SELECT * FROM messages 
            WHERE conversation_id = ? 
            ORDER BY timestamp ASC
        """, (conv["id"],)).fetchall()
        
        conv_dict = dict(conv)
        conv_dict["messages"] = [dict(msg) for msg in messages]
        conversations_with_messages.append(conv_dict)
    
    conn.close()
    
    return {"conversations": conversations_with_messages, "total": len(conversations_with_messages)}

@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    conn = get_db_connection()
    
    conversation = conn.execute("""
        SELECT c.*, l.first_name, l.last_name, l.email, l.phone, l.property_address
        FROM conversations c
        JOIN leads l ON c.lead_id = l.id
        WHERE c.id = ?
    """, (conversation_id,)).fetchone()
    
    if not conversation:
        conn.close()
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = conn.execute("""
        SELECT * FROM messages 
        WHERE conversation_id = ? 
        ORDER BY timestamp ASC
    """, (conversation_id,)).fetchall()
    
    conn.close()
    
    conv_dict = dict(conversation)
    conv_dict["messages"] = [dict(msg) for msg in messages]
    
    return conv_dict

@app.post("/api/conversations/{lead_id}/message")
async def send_message(lead_id: str, message_data: dict):
    conn = get_db_connection()
    
    # Get or create conversation for this lead
    conversation = conn.execute("""
        SELECT * FROM conversations WHERE lead_id = ? ORDER BY created_at DESC LIMIT 1
    """, (lead_id,)).fetchone()
    
    if not conversation:
        # Create new conversation
        conversation_id = str(uuid.uuid4())
        conn.execute("""
            INSERT INTO conversations (id, lead_id, status) VALUES (?, ?, 'active')
        """, (conversation_id, lead_id))
    else:
        conversation_id = conversation["id"]
    
    # Add the message
    message_id = str(uuid.uuid4())
    conn.execute("""
        INSERT INTO messages (id, conversation_id, direction, content, method, ai_generated)
        VALUES (?, ?, 'outbound', ?, 'email', 0)
    """, (message_id, conversation_id, message_data.get("message", "")))
    
    # Update conversation timestamp
    conn.execute("""
        UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?
    """, (conversation_id,))
    
    conn.commit()
    conn.close()
    
    return {"success": True, "message": "Message sent successfully"}

# Webhook endpoint for Telnyx SMS
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
            # Create state for existing lead (use column names for safety)
            lead_row = dict_from_row(lead)
            state = create_initial_state(
                lead_id=lead_row.get("id"),
                lead_name=f"{lead_row.get('first_name','')} {lead_row.get('last_name','')}".strip(),
                property_address=lead_row.get("property_address", "Unknown Property"),
                property_type=lead_row.get("property_type", "fix_flip"),
                campaign_id=lead_row.get("campaign_id", "incoming_response"),
                lead_phone=from_number,
                lead_email=lead_row.get("email", "") or ""
            )
            # Load persisted conversation stage and qualification data if available
            persisted_stage = lead_row.get("conversation_stage")
            if persisted_stage:
                state["conversation_stage"] = persisted_stage
            else:
                state["conversation_stage"] = "qualifying"
            try:
                persisted_q = lead_row.get("qualification_data")
                if persisted_q:
                    import json as _json
                    state["qualification_data"] = _json.loads(persisted_q)
            except Exception:
                pass
        else:
            # Create new lead for unknown number - they're responding to outreach
            lead_id = str(uuid.uuid4())
            
            # Insert new lead into database
            conn.execute("""
                INSERT INTO leads (id, first_name, last_name, phone, email, property_address, 
                                 property_type, campaign_id, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (lead_id, "Unknown", "Lead", from_number, "", "Unknown Property", 
                  "fix_flip", "incoming_response", "responding"))
            conn.commit()
            
            state = create_initial_state(
                lead_id=lead_id,
                lead_name="Unknown Lead",
                property_address="Unknown Property",
                property_type="fix_flip",
                campaign_id="incoming_response",
                lead_phone=from_number
            )
            # Set to qualifying stage since they're responding to outreach
            state["conversation_stage"] = "qualifying"
        
        # Add the incoming message to the state
        from langchain_core.messages import HumanMessage
        state["messages"] = [HumanMessage(content=message)]
        
        # Run the conversation through LangGraph in inbound mode
        print("🤖 Processing through AI system (LangGraph inbound)...")
        state["conversation_mode"] = "inbound_response"
        state["incoming_message"] = message
        
        graph = create_complete_real_estate_graph()
        result = graph.invoke(state)
        
        # Log diagnostics (the SMS should be sent by SMSAgent inside the graph)
        print("✅ AI processing complete")
        print(f"📊 Stage: {result.get('conversation_stage', 'unknown')}")
        print(f"🎯 Next: {result.get('next_agent', 'unknown')}")
        print(f"🔍 Result keys: {list(result.keys())}")
        print(f"📝 Messages count: {len(result.get('messages', []))}")
        if result.get("generated_response"):
            print(f"💬 Generated response (by agent): {result['generated_response'][:120]}")
        if result.get("last_contact_method"):
            print(f"📨 Last contact method: {result['last_contact_method']}")
        if result.get("last_error"):
            print(f"⚠️ Last error: {result['last_error']}")
        
        # Persist updated conversation stage and qualification_data for continuity
        try:
            conn.execute(
                """
                UPDATE leads
                SET conversation_stage = ?, qualification_data = ?, status = 'responding'
                WHERE phone = ?
                """,
                (
                    result.get("conversation_stage", state.get("conversation_stage", "qualifying")),
                    json.dumps(result.get("qualification_data", state.get("qualification_data", {}))),
                    from_number,
                ),
            )
            conn.commit()
        except Exception as _e:
            print(f"⚠️ Failed to persist conversation state: {_e}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error processing SMS: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
