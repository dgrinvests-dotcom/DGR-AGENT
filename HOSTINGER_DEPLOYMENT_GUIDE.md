# 🚀 Hostinger VPS Deployment Guide

## Step 1: Get Hostinger VPS ($3.99/month)

1. **Login to Hostinger**
2. **Go to VPS section**
3. **Choose VPS Plan 1**: $3.99/month
   - 1 vCPU
   - 1GB RAM  
   - 20GB SSD
   - Ubuntu 20.04
4. **Complete purchase**

## Step 2: Initial Server Setup

### Connect to your VPS:
```bash
ssh root@your-vps-ip
```

### Update system:
```bash
apt update && apt upgrade -y
```

### Install Python and dependencies:
```bash
apt install python3 python3-pip nginx git -y
pip3 install fastapi uvicorn python-dotenv openai telnyx
```

## Step 3: Deploy Your Backend

### Upload your project:
```bash
# Option 1: Git clone (if you have GitHub repo)
git clone https://github.com/yourusername/agent-estate.git
cd agent-estate

# Option 2: Upload via SCP/SFTP
# Upload your entire project folder to /root/agent-estate/
```

### Install Python dependencies:
```bash
cd /root/agent-estate
pip3 install -r requirements.txt
pip3 install -r requirements_google.txt
```

### Set up environment variables:
```bash
nano .env
# Copy your .env content here
```

### Test the backend:
```bash
cd src
python3 database_main_new.py
```

## Step 4: Set up Production Service

### Create systemd service:
```bash
nano /etc/systemd/system/agent-estate.service
```

**Service file content:**
```ini
[Unit]
Description=AI Real Estate Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/agent-estate/src
Environment=PATH=/usr/local/bin:/usr/bin:/bin
ExecStart=/usr/bin/python3 database_main_new.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Start the service:
```bash
systemctl daemon-reload
systemctl enable agent-estate
systemctl start agent-estate
systemctl status agent-estate
```

## Step 5: Configure Nginx (Web Server)

### Create Nginx config:
```bash
nano /etc/nginx/sites-available/agent-estate
```

**Nginx config:**
```nginx
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain
    
    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # Webhooks
    location /webhooks/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # Frontend (React build)
    location / {
        root /root/agent-estate/frontend/build;
        try_files $uri $uri/ /index.html;
    }
}
```

### Enable the site:
```bash
ln -s /etc/nginx/sites-available/agent-estate /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

## Step 6: Build and Deploy Frontend

### Install Node.js:
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
apt-get install -y nodejs
```

### Build React frontend:
```bash
cd /root/agent-estate/frontend
npm install
npm run build
```

## Step 7: Configure Domain and SSL

### Point your domain to VPS IP:
- **A Record**: `yourdomain.com` → `your-vps-ip`
- **CNAME**: `www.yourdomain.com` → `yourdomain.com`

### Install SSL certificate (free):
```bash
apt install certbot python3-certbot-nginx -y
certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

## Step 8: Configure Telnyx Webhook

**Your webhook URL will be:**
```
https://yourdomain.com/webhooks/telnyx
```

1. **Go to Telnyx Portal**
2. **Messaging → Messaging Profiles**
3. **Edit your profile**
4. **Set webhook URL**: `https://yourdomain.com/webhooks/telnyx`
5. **Save**

## Step 9: Test Everything

### Test backend:
```bash
curl https://yourdomain.com/api/health
```

### Test webhook:
```bash
curl -X POST https://yourdomain.com/webhooks/telnyx \
  -H "Content-Type: application/json" \
  -d '{"test": "webhook"}'
```

### Test SMS:
Send SMS to your Telnyx number: +17325320590

## 🎉 **Deployment Complete!**

### **Your URLs:**
- **Frontend Dashboard**: https://yourdomain.com
- **Backend API**: https://yourdomain.com/api
- **Webhook**: https://yourdomain.com/webhooks/telnyx
- **API Docs**: https://yourdomain.com/docs

### **Monthly Cost:** $3.99/month
### **No ngrok needed!** ✅
### **Professional deployment** ✅

## 🔧 **Maintenance Commands**

### Check service status:
```bash
systemctl status agent-estate
```

### View logs:
```bash
journalctl -u agent-estate -f
```

### Restart service:
```bash
systemctl restart agent-estate
```

### Update code:
```bash
cd /root/agent-estate
git pull  # If using Git
systemctl restart agent-estate
```

---

**This gives you a professional, production-ready deployment for just $3.99/month!**
