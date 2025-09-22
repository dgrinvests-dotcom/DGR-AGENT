# Project Structure

## 📁 Directory Layout

```
Agent Estate/
├── src/                          # Core application code
│   ├── agents/                   # AI agents
│   │   ├── property_specialists/ # Property-specific agents
│   │   ├── base_agent.py        # Base agent class
│   │   ├── supervisor_agent.py  # Main supervisor
│   │   ├── communication_router.py
│   │   ├── sms_agent.py
│   │   ├── email_agent.py
│   │   └── booking_agent.py
│   ├── api/                     # API endpoints
│   ├── schemas/                 # Data schemas
│   ├── services/                # External service integrations
│   ├── utils/                   # Utility functions
│   ├── database_main_new.py     # Main API server
│   ├── langgraph_complete.py    # LangGraph system
│   └── init_database.py         # Database setup
├── frontend/                    # React dashboard
├── Project Doc/                 # Documentation
├── .env                        # Environment variables
├── .env.example               # Environment template
├── requirements.txt           # Python dependencies
├── requirements_google.txt    # Google-specific dependencies
├── agent_estate.db           # SQLite database
├── dgr-agent-*.json         # Google service account
└── README.md                # Project documentation
```

## 🔧 Core Files

### Main Application
- `database_main_new.py` - FastAPI server with all endpoints
- `langgraph_complete.py` - Complete multi-agent system
- `init_database.py` - Database initialization

### Agents
- `supervisor_agent.py` - Main conversation coordinator
- `communication_router.py` - Routes between SMS/Email
- `property_specialists/` - Property-type specific agents
- `booking_agent.py` - Google Calendar integration

### Configuration
- `.env` - Production environment variables
- `requirements.txt` - Core Python dependencies
- `requirements_google.txt` - Google Calendar dependencies

## 🚀 Deployment Ready

All test files, debug scripts, and development artifacts have been removed.
The project is now ready for production deployment.
