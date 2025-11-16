# PDFsaver Deployment Guide

This guide explains how to deploy the PDFsaver application using Docker.

## Deployment Scenario Selection

### Scenario 1: Single Machine Local Use
- **Use Case**: Use on a single machine only
- **Access**: `http://localhost:3000`
- **Difficulty**: ⭐ Easiest
- **Reference**: Jump directly to "Quick Start" section

### Scenario 2: Internal Network Multi-User Access (Recommended)
- **Use Case**: Team use, staff access from their own computers
- **Access**: `http://[server-IP]:3000` or `http://pdfsaver.internal`
- **Difficulty**: ⭐⭐ Simple (requires network configuration)
- **Reference**: See "Internal Network Deployment" section

### Scenario 3: Production Environment Deployment
- **Use Case**: Formal production environment, requires HTTPS, domain name, etc.
- **Access**: `https://pdfsaver.yourdomain.com`
- **Difficulty**: ⭐⭐⭐ Medium (requires Nginx, SSL configuration)
- **Reference**: See "Production Environment Configuration" section

---

## Quick Start (Common to All Scenarios)

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- At least 4GB RAM (8GB+ recommended)
- At least 10GB disk space

### 1. Prepare Project

```bash
# Clone or upload project
git clone <your-repo-url>
cd pdfsaver
```

### 2. Configure Environment Variables

Create `.env` file:

```bash
# OCR Worker authentication token (must change!)
OCR_TOKEN=$(openssl rand -hex 32)

# Configure according to deployment scenario (see below)
# Scenario 1 (Single machine): Use default values
# Scenario 2 (Internal network): See configuration below
# Scenario 3 (Production): See configuration below
```

### 3. Start Services

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 4. Access Application

- **Scenario 1**: http://localhost:3000
- **Scenario 2**: http://[server-IP]:3000
- **Scenario 3**: https://your-domain.com

---

## Scenario 2: Internal Network Deployment (Allow Staff Access)

### Step 1: Get Server IP

```bash
# Linux/Mac
hostname -I | awk '{print $1}'

# Windows PowerShell
ipconfig | findstr IPv4
```

### Step 2: Configure .env File

```bash
# Server IP (replace with actual IP)
SERVER_IP=192.168.1.100

# OCR Worker configuration
OCR_TOKEN=$(openssl rand -hex 32)

# Allowed origins (staff access addresses)
ALLOW_ORIGINS=http://192.168.1.100:3000,http://pdfsaver.internal:3000

# Frontend configuration
NEXT_PUBLIC_APP_ORIGIN=http://192.168.1.100:3000
```

### Step 3: Configure Firewall

**Ubuntu/Debian:**
```bash
sudo ufw allow 3000/tcp
sudo ufw reload
```

**CentOS/RHEL:**
```bash
sudo firewall-cmd --permanent --add-port=3000/tcp
sudo firewall-cmd --reload
```

**Windows Server:**
```powershell
New-NetFirewallRule -DisplayName "PDFsaver" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow
```

### Step 4: Restart Services to Apply Configuration

```bash
docker-compose restart
```

### Staff Access Methods

#### Method A: Direct IP Access (Simplest)

Staff enter in browser: `http://192.168.1.100:3000`

#### Method B: Using Domain Name (Recommended)

1. **Initial Setup for Staff** (one-time only):
   
   **Windows:**
   - Open Notepad as Administrator
   - Open `C:\Windows\System32\drivers\etc\hosts`
   - Add: `192.168.1.100  pdfsaver.internal`
   - Save

   **Mac/Linux:**
   ```bash
   sudo nano /etc/hosts
   # Add: 192.168.1.100  pdfsaver.internal
   ```

2. **Access**: `http://pdfsaver.internal:3000`

---

## Scenario 3: Production Environment Deployment

### Step 1: Configure Domain and SSL

1. Configure DNS records to point to server IP
2. Obtain SSL certificate (Let's Encrypt or commercial certificate)

### Step 2: Install and Configure Nginx

```bash
# Install Nginx
sudo apt-get update
sudo apt-get install nginx
```

Create `/etc/nginx/sites-available/pdfsaver`:

```nginx
server {
    listen 80;
    server_name pdfsaver.yourdomain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name pdfsaver.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Enable configuration:
```bash
sudo ln -s /etc/nginx/sites-available/pdfsaver /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Step 3: Configure .env File

```bash
OCR_TOKEN=$(openssl rand -hex 32)
ALLOW_ORIGINS=https://pdfsaver.yourdomain.com
NEXT_PUBLIC_APP_ORIGIN=https://pdfsaver.yourdomain.com
```

### Step 4: Restart Services

```bash
docker-compose restart
```

---

## Using Local LLM (Optional)

If you need to use local LLM (Ollama):

```bash
# Start all services (including Ollama)
docker-compose --profile llm up -d

# Download model
docker exec -it pdfsaver-ollama ollama pull llama3
```

---

## Common Commands

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f ocr-worker
```

### Restart Services
```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart web
```

### Update Application
```bash
git pull
docker-compose build
docker-compose up -d
```

### Stop Services
```bash
docker-compose down
```

---

## Troubleshooting

### Issue 1: Cannot Access Application

**Checklist:**
1. Are services running? `docker-compose ps`
2. Is firewall port open? `sudo ufw status` or `sudo firewall-cmd --list-ports`
3. Is network reachable? `ping [server-IP]`
4. View logs: `docker-compose logs web`

### Issue 2: CORS Error

**Solution:**
1. Check `ALLOW_ORIGINS` configuration in `.env`
2. Ensure complete access URL is included (including port)
3. Restart service: `docker-compose restart ocr-worker`

### Issue 3: OCR Worker Connection Failed

**Check:**
1. Is OCR Worker running? `docker-compose ps`
2. Internal network connection: `docker exec pdfsaver-web wget -O- http://ocr-worker:8123/healthz`
3. Check environment variables: `docker exec pdfsaver-web env | grep OCR`

---

## Security Recommendations

1. **Change Default Token**
   ```bash
   openssl rand -hex 32
   ```

2. **Restrict Network Access**
   - Only open necessary ports
   - Use firewall to restrict source IPs

3. **Regular Updates**
   ```bash
   git pull
   docker-compose build
   docker-compose up -d
   ```

---

## Quick Reference

| Scenario | Access URL | Configuration Complexity | Use Case |
|----------|-----------|-------------------------|----------|
| Single Machine | `http://localhost:3000` | ⭐ Easiest | Personal use |
| Internal Network | `http://[IP]:3000` | ⭐⭐ Simple | Team use |
| Production | `https://domain.com` | ⭐⭐⭐ Medium | Formal deployment |

---

**Need Help?** See detailed documentation:
- Staff Access Guide: `STAFF-ACCESS-GUIDE.md`
- Detailed Configuration: See scenario sections in this document
