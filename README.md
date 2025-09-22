# AI Real Estate Outreach Agent

Professional AI-powered real estate outreach system for wholesale investors.

## 🎯 Features

- **Multi-Agent AI System**: Specialized agents for different property types
- **Multi-Channel Communication**: Email + SMS outreach
- **Google Calendar Integration**: Automatic appointment booking
- **Property-Specific Flows**: Fix & Flip, Vacant Land, Long-Term Rentals
- **TCPA Compliance**: Built-in compliance and opt-out handling
- **Campaign Management**: Multi-campaign support with analytics

## 🚀 Quick Start

### 1. Environment Setup
```bash
# Copy and configure environment variables
cp .env.example .env
# Edit .env with your API keys
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
pip install -r requirements_google.txt
```

### 3. Initialize Database
```bash
cd src
python init_database.py
```

### 4. Start the System
```bash
python database_main_new.py
```

### 5. Access the Dashboard
- **API**: http://localhost:8000
- **Frontend**: http://localhost:3000 (if running React app)
- **API Docs**: http://localhost:8000/docs

## 📋 Configuration

### Required Environment Variables
```bash
# OpenAI API
OPENAI_API_KEY=your_openai_key

# Gmail SMTP
GMAIL_ADDRESS=your_gmail@gmail.com
GMAIL_APP_PASSWORD=your_app_password

# Telnyx SMS (Optional)
TELNYX_API_KEY=your_telnyx_key
TELNYX_MESSAGING_PROFILE_ID=your_profile_id
TELNYX_PHONE_NUMBER=+1234567890

# Google Calendar (Optional)
GOOGLE_SERVICE_ACCOUNT_KEY={"type":"service_account",...}
GOOGLE_CALENDAR_ID=primary
```

## 📊 System Architecture

- **FastAPI Backend**: RESTful API with real-time capabilities
- **LangGraph Multi-Agent System**: AI conversation management
- **SQLite Database**: Lead and campaign management
- **React Frontend**: Management dashboard
- **External Integrations**: OpenAI, Telnyx, Gmail, Google Calendar

## 🏠 Property Types Supported

1. **Fix & Flip Properties**
   - Condition assessment
   - Repair cost evaluation
   - Quick cash offers

2. **Vacant Land**
   - Acreage and access evaluation
   - Utility availability
   - Development potential

3. **Long-Term Rentals**
   - Rental income analysis
   - Tenant situation handling
   - Investment evaluation

## 📞 Support

For technical support or questions, refer to the Project Doc folder for detailed documentation.

## 🔒 Security

- Environment variables for sensitive data
- TCPA/DNC compliance built-in
- Secure API key management
- Audit logging for all communications

---

**Ready for Production Deployment** ✅
