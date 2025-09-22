# 🚀 Railway Full-Stack Deployment Guide

## Why Railway is Perfect for Your Project

✅ **Hosts both backend AND frontend**  
✅ **Automatic HTTPS with custom domain**  
✅ **Zero configuration deployment**  
✅ **Built-in environment variables**  
✅ **Automatic deployments from GitHub**  
✅ **Permanent webhook URLs**  
✅ **$5/month for everything**  

## Step 1: Prepare Your Project

### Create Railway configuration files:

**1. Create `railway.json`:**
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "cd src && python database_main_new.py",
    "healthcheckPath": "/health"
  }
}
```

**2. Create `Procfile`:**
```
web: cd src && python database_main_new.py
```

**3. Update `requirements.txt` to include all dependencies:**
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-dotenv==1.0.0
openai==1.3.0
telnyx==2.0.0
google-api-python-client==2.108.0
google-auth-httplib2==0.1.1
google-auth-oauthlib==1.1.0
pydantic==2.5.0
python-multipart==0.0.6
```

## Step 2: Modify FastAPI to Serve React Frontend

### Update your `database_main_new.py`:

Add these imports at the top:
```python
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from pathlib import Path
```

Add this after your app creation:
```python
# Serve React frontend
frontend_path = Path(__file__).parent.parent / "frontend" / "build"

if frontend_path.exists():
    # Serve static files (CSS, JS, images)
    app.mount("/static", StaticFiles(directory=frontend_path / "static"), name="static")
    
    # Serve React app for all non-API routes
    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        # If it's an API route, let FastAPI handle it
        if full_path.startswith("api/") or full_path.startswith("webhooks/"):
            raise HTTPException(status_code=404, detail="Not found")
        
        # Check if file exists in build directory
        file_path = frontend_path / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        
        # Otherwise serve index.html (React Router will handle routing)
        return FileResponse(frontend_path / "index.html")
```

## Step 3: Create Build Script

### Create `build.sh`:
```bash
#!/bin/bash
echo "🏗️ Building React Frontend..."

# Install Node.js dependencies
cd frontend
npm install

# Build React app
npm run build

echo "✅ Frontend build complete!"

# Go back to root
cd ..

echo "🚀 Ready for Railway deployment!"
```

Make it executable:
```bash
chmod +x build.sh
```

## Step 4: Deploy to Railway

### Option A: GitHub Integration (Recommended)

1. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "Prepare for Railway deployment"
   git push origin main
   ```

2. **Connect Railway:**
   - Go to https://railway.app/
   - Sign up with GitHub
   - Click "Deploy from GitHub repo"
   - Select your repository
   - Railway will auto-detect Python and deploy!

### Option B: Railway CLI

1. **Install Railway CLI:**
   ```bash
   npm install -g @railway/cli
   ```

2. **Login and deploy:**
   ```bash
   railway login
   railway init
   railway up
   ```

## Step 5: Configure Environment Variables

In Railway dashboard:
1. **Go to your project**
2. **Click "Variables" tab**
3. **Add all your environment variables:**

```bash
OPENAI_API_KEY=your_openai_key
GMAIL_ADDRESS=dgrinvests@gmail.com
GMAIL_APP_PASSWORD=your_gmail_password
TELNYX_API_KEY=your_telnyx_key
TELNYX_MESSAGING_PROFILE_ID=your_profile_id
TELNYX_PHONE_NUMBER=+17325320590
GOOGLE_SERVICE_ACCOUNT_KEY={"type":"service_account"...}
GOOGLE_CALENDAR_ID=primary
DATABASE_URL=sqlite:///./agent_estate.db
```

## Step 6: Get Your URLs

Railway will provide:
- **App URL**: `https://your-app-name.railway.app`
- **Custom Domain**: Connect your own domain (optional)

### Your endpoints will be:
- **Frontend Dashboard**: `https://your-app-name.railway.app`
- **Backend API**: `https://your-app-name.railway.app/api`
- **Webhook**: `https://your-app-name.railway.app/webhooks/telnyx`
- **API Docs**: `https://your-app-name.railway.app/docs`

## Step 7: Configure Telnyx Webhook

1. **Copy your Railway URL**: `https://your-app-name.railway.app`
2. **Go to Telnyx Portal**: https://portal.telnyx.com/
3. **Messaging → Messaging Profiles**
4. **Edit your profile**
5. **Set webhook URL**: `https://your-app-name.railway.app/webhooks/telnyx`
6. **Save**

## Step 8: Test Everything

### Test frontend:
Visit: `https://your-app-name.railway.app`

### Test backend API:
Visit: `https://your-app-name.railway.app/docs`

### Test webhook:
```bash
curl -X POST https://your-app-name.railway.app/webhooks/telnyx \
  -H "Content-Type: application/json" \
  -d '{"test": "webhook"}'
```

### Test SMS:
Send SMS to: +17325320590

## 🎉 **Deployment Complete!**

### **What You Get:**
- ✅ **Full-stack app** (frontend + backend)
- ✅ **Automatic HTTPS**
- ✅ **Permanent webhook URL**
- ✅ **Auto-deployments** from GitHub
- ✅ **Built-in monitoring**
- ✅ **Custom domain support**

### **Monthly Cost:** $5/month
### **Zero maintenance** ✅
### **Professional deployment** ✅

## 🔧 **Railway vs Other Options**

| Feature | Railway | Hostinger VPS | Current Setup |
|---------|---------|---------------|---------------|
| **Cost** | $5/month | $3.99/month | Free (ngrok issues) |
| **Setup Time** | 10 minutes | 30 minutes | Already done |
| **Maintenance** | Zero | Manual updates | ngrok restarts |
| **Frontend Hosting** | ✅ Included | ✅ Manual setup | ❌ Separate needed |
| **Auto Deployments** | ✅ GitHub integration | ❌ Manual | ❌ Manual |
| **Custom Domain** | ✅ Easy | ✅ Manual DNS | ❌ ngrok subdomain |
| **SSL Certificate** | ✅ Automatic | ✅ Manual setup | ✅ ngrok provides |

## 🎯 **Railway Advantages:**

1. **✅ Easiest deployment** (10 minutes vs 30+ minutes)
2. **✅ Hosts everything** (frontend + backend in one place)
3. **✅ Zero maintenance** (automatic updates, scaling)
4. **✅ Professional URLs** (your-app.railway.app)
5. **✅ GitHub integration** (push code → auto deploy)
6. **✅ Built-in monitoring** and logs

---

**Railway is perfect if you want the easiest, most professional deployment with minimal setup time!**
