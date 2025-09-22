# AI Real Estate Agent - Testing Setup Guide

## 🚀 Quick Start for Email Testing

Since you're waiting for Telnyx 10DLC approval, we'll test the agent using email conversations first.

## 📋 Required API Keys & Setup

### 1. OpenAI API Key (REQUIRED)
- Go to: https://platform.openai.com/api-keys
- Create a new API key
- Copy the key (starts with `sk-`)

### 2. Gmail App Password (REQUIRED for email testing)
- Enable 2-Factor Authentication on your Gmail account
- Go to: https://myaccount.google.com/apppasswords
- Generate an app password for "Mail"
- Copy the 16-character password (no spaces)

### 3. Google Meet Integration (OPTIONAL)
- Go to: https://console.cloud.google.com/
- Create a new project or select existing
- Enable Google Calendar API
- Create credentials (OAuth 2.0)
- Download the credentials JSON file

## 🔧 Environment Setup

1. **Copy the environment file:**
   ```bash
   copy .env.example .env
   ```

2. **Edit the `.env` file with your actual values:**
   ```env
   # REQUIRED - Get from OpenAI
   OPENAI_API_KEY=sk-your-actual-openai-key-here
   
   # REQUIRED - Your Gmail credentials
   GMAIL_ADDRESS=your-email@gmail.com
   GMAIL_APP_PASSWORD=your-16-char-app-password
   
   # OPTIONAL - Google Meet (leave blank for now)
   GOOGLE_CREDENTIALS_FILE=
   GOOGLE_TOKEN_FILE=
   
   # OPTIONAL - Telnyx (leave blank until 10DLC approved)
   TELNYX_API_KEY=
   TELNYX_MESSAGING_PROFILE_ID=
   TELNYX_PHONE_NUMBER=
   TELNYX_WEBHOOK_SECRET=
   
   # Database and other settings (keep as is)
   DATABASE_URL=sqlite:///./agent_estate.db
   QUIET_HOURS_START=21:00
   QUIET_HOURS_END=08:00
   TIMEZONE=America/New_York
   DEBUG=True
   LOG_LEVEL=INFO
   ```

## 🧪 Testing the Agent

### Step 1: Start the Services
1. **Start the backend:**
   ```bash
   cd "C:\Users\7Roars\Desktop\Agent Estate"
   python src\simple_main.py
   ```
   Backend will run on: http://localhost:8000

2. **Start the frontend (in a new terminal):**
   ```bash
   cd "C:\Users\7Roars\Desktop\Agent Estate\frontend"
   npm start
   ```
   Dashboard will open at: http://localhost:3000

### Step 2: Test the Agent
1. **Edit the test file:**
   - Open `src\test_agent.py`
   - Replace `your_test_email@gmail.com` with your actual email address

2. **Run the agent test:**
   ```bash
   python src\test_agent.py
   ```

### Step 3: Monitor in Dashboard
- Open http://localhost:3000
- Navigate to "Conversations" to see agent interactions
- Check "Leads" to see test lead data
- View "Dashboard" for overall statistics

## 📧 Email Testing Flow

The agent will:
1. Generate initial outreach emails for leads
2. Process email responses using AI
3. Qualify leads through conversation
4. Schedule appointments when leads show interest
5. Handle follow-ups and objections

## 🔍 What to Test

1. **Initial Outreach**: Agent generates personalized emails
2. **Response Handling**: AI processes and responds to lead replies
3. **Qualification**: Agent asks relevant questions based on property type
4. **Appointment Setting**: Agent offers to schedule calls/meetings
5. **Follow-ups**: Agent handles no-shows and future contact requests

## 📊 Dashboard Features to Verify

- [ ] Dashboard shows campaign statistics
- [ ] Leads are displayed with proper status
- [ ] Conversations show message history
- [ ] Integration status shows Gmail as connected
- [ ] Campaign management works (create/edit campaigns)

## 🚨 Troubleshooting

### Common Issues:
1. **OpenAI API Error**: Check your API key and billing
2. **Gmail Authentication**: Ensure 2FA is enabled and app password is correct
3. **Import Errors**: Make sure you're in the correct directory
4. **Port Conflicts**: Ensure ports 3000 and 8000 are available

### Debug Steps:
1. Check the backend logs for errors
2. Verify environment variables are loaded
3. Test API endpoints directly at http://localhost:8000/docs
4. Check browser console for frontend errors

## 🎯 Success Criteria

You'll know everything is working when:
- ✅ Backend starts without errors
- ✅ Frontend loads the dashboard
- ✅ Test agent generates realistic responses
- ✅ Dashboard displays conversation data
- ✅ Email integration status shows as connected

## 🔄 Next Steps After Testing

1. **Add Real Leads**: Import your actual lead data
2. **Configure Telnyx**: Once 10DLC is approved, add SMS capability
3. **Set up Google Meet**: For automated appointment scheduling
4. **Database Setup**: Replace mock data with real database
5. **Production Deployment**: Deploy to a server for live use

## 📞 Ready for Production

Once Telnyx 10DLC is approved:
1. Add Telnyx credentials to `.env`
2. Test SMS conversations
3. Set up webhook endpoints
4. Configure phone number routing
5. Launch live campaigns!
