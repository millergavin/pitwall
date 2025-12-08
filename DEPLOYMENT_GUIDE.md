# Pitwall Deployment Guide

This guide covers how to set up Pitwall on a self-hosted server (your PC) so the site runs 24/7.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                           INTERNET                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   pitwall.one ──────────► Vercel (Frontend)                         │
│                              │                                       │
│                              │ API calls to                          │
│                              ▼                                       │
│   api.pitwall.one ──────► Cloudflare Tunnel                         │
│                              │                                       │
│                              │ Routes to                             │
│                              ▼                                       │
│   ┌──────────────────────────────────────────┐                      │
│   │           YOUR PC (Server)                │                      │
│   │                                           │                      │
│   │   cloudflared ◄─── Tunnel connection      │                      │
│   │        │                                  │                      │
│   │        ▼                                  │                      │
│   │   FastAPI (port 8000)                     │                      │
│   │        │                                  │                      │
│   │        ▼                                  │                      │
│   │   PostgreSQL (Docker, port 5433)          │                      │
│   │        │                                  │                      │
│   │        ▼                                  │                      │
│   │   64GB F1 Data                            │                      │
│   └──────────────────────────────────────────┘                      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Key Components:**
- **Vercel**: Hosts the React frontend (automatic, no server needed)
- **Cloudflare Tunnel**: Securely exposes your local API to the internet
- **FastAPI**: Python backend that serves F1 data
- **PostgreSQL**: Database with all F1 data (runs in Docker)

---

## Prerequisites

Install these on your PC:

### 1. Docker
- **Windows**: [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- **Linux**: 
  ```bash
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker $USER
  ```

### 2. Python 3.11+
- **Windows**: [python.org](https://www.python.org/downloads/)
- **Linux**: `sudo apt install python3 python3-pip python3-venv`

### 3. Git
- **Windows**: [git-scm.com](https://git-scm.com/download/win)
- **Linux**: `sudo apt install git`

### 4. Cloudflared
- **Windows**: Download from [Cloudflare releases](https://github.com/cloudflare/cloudflared/releases)
- **Linux**:
  ```bash
  curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
  chmod +x cloudflared
  sudo mv cloudflared /usr/local/bin/
  ```

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/millergavin/pitwall.git
cd pitwall
```

---

## Step 2: Set Up PostgreSQL

### Start the Database Container

```bash
docker-compose up -d
```

This creates a PostgreSQL container with:
- **Port**: 5433 (mapped to 5432 inside container)
- **User**: pitwall_admin
- **Password**: pitwall_admin
- **Database**: pitwall

### Verify It's Running

```bash
docker ps | grep pitwall
```

You should see `pitwall_postgres` running.

---

## Step 3: Migrate Database from Mac

### On Your Mac (source):

```bash
# Export the entire database (this will be ~64GB)
cd ~/Programming/pitwall
docker exec pitwall_postgres pg_dump -U pitwall_admin -Fc pitwall > pitwall_backup.dump

# Or export just the essential data (~1.5GB, faster):
docker exec pitwall_postgres pg_dump -U pitwall_admin -Fc \
  --exclude-table='bronze.car_gps_raw' \
  --exclude-table='bronze.car_telemetry_raw' \
  --exclude-table='silver.car_gps' \
  --exclude-table='silver.car_telemetry' \
  pitwall > pitwall_backup_slim.dump
```

### Transfer to PC:

Use your preferred method:
- USB drive
- `scp` over network: `scp pitwall_backup.dump user@your-pc:/path/to/pitwall/`
- Cloud storage (Google Drive, etc.)

### On Your PC (destination):

```bash
# Restore the database
cd /path/to/pitwall
docker exec -i pitwall_postgres pg_restore -U pitwall_admin -d pitwall --clean --if-exists < pitwall_backup.dump

# If you get errors about existing objects, that's usually OK
```

### Verify the Data

```bash
docker exec pitwall_postgres psql -U pitwall_admin -d pitwall -c "SELECT COUNT(*) FROM silver.meetings;"
```

---

## Step 4: Set Up Python Environment

```bash
cd /path/to/pitwall

# Create virtual environment
python3 -m venv .venv

# Activate it
# Linux/Mac:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Create .env File

```bash
cat > .env << 'EOF'
PGHOST=localhost
PGPORT=5433
PGDATABASE=pitwall
PGUSER=pitwall_admin
PGPASSWORD=pitwall_admin
EOF
```

---

## Step 5: Set Up Cloudflare Tunnel

The tunnel securely connects your local API to `api.pitwall.one`.

### Authenticate with Cloudflare

```bash
cloudflared tunnel login
```

This opens a browser — log in and authorize.

### Transfer Tunnel Credentials from Mac

You need the existing tunnel credentials (so it connects to the same `api.pitwall.one`):

**On Mac**, copy these files to your PC:
```
~/.cloudflared/cert.pem
~/.cloudflared/d167cd07-e7b4-41d4-a6cd-309d2fd199c5.json  (your tunnel credentials)
~/.cloudflared/config.yml
```

**On PC**, place them in:
- **Linux**: `~/.cloudflared/`
- **Windows**: `C:\Users\YourName\.cloudflared\`

### Update config.yml Paths

Edit `~/.cloudflared/config.yml` to update paths for your PC:

```yaml
tunnel: pitwall-api
credentials-file: /home/youruser/.cloudflared/d167cd07-e7b4-41d4-a6cd-309d2fd199c5.json

ingress:
  - hostname: api.pitwall.one
    service: http://localhost:8000
  - service: http_status:404
```

### Test the Tunnel

```bash
cloudflared tunnel run pitwall-api
```

If it connects successfully, you'll see "Registered tunnel connection".

---

## Step 6: Start Everything

### Quick Start Script

Create a startup script (Linux):

```bash
cat > start-pitwall.sh << 'EOF'
#!/bin/bash
echo "🏎️  Starting Pitwall..."

# Start PostgreSQL if not running
if ! docker ps | grep -q pitwall_postgres; then
    echo "Starting PostgreSQL..."
    docker start pitwall_postgres || docker-compose up -d
    sleep 3
fi

# Activate Python environment
source /path/to/pitwall/.venv/bin/activate

# Start API in background
echo "Starting API..."
cd /path/to/pitwall
nohup python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 > /tmp/pitwall-api.log 2>&1 &
sleep 2

# Start Cloudflare tunnel in background
echo "Starting Cloudflare tunnel..."
nohup cloudflared tunnel run pitwall-api > /tmp/cloudflared.log 2>&1 &
sleep 3

# Verify
if curl -s "https://api.pitwall.one/" | grep -q "healthy"; then
    echo "✅ Pitwall is live at https://pitwall.one"
else
    echo "⚠️  API may not be reachable yet. Check logs:"
    echo "   tail -f /tmp/pitwall-api.log"
    echo "   tail -f /tmp/cloudflared.log"
fi
EOF

chmod +x start-pitwall.sh
```

### Windows Startup Script

Create `start-pitwall.bat`:

```batch
@echo off
echo Starting Pitwall...

:: Start Docker container
docker start pitwall_postgres

:: Wait for DB
timeout /t 3

:: Start API
cd C:\path\to\pitwall
start /B python -m uvicorn api.main:app --host 0.0.0.0 --port 8000

:: Wait for API
timeout /t 2

:: Start tunnel
start /B cloudflared tunnel run pitwall-api

echo Pitwall should be starting...
echo Check https://pitwall.one in a minute
```

---

## Step 7: Auto-Start on Boot (Optional)

### Linux (systemd)

Create `/etc/systemd/system/pitwall.service`:

```ini
[Unit]
Description=Pitwall F1 Dashboard
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/pitwall
ExecStart=/path/to/pitwall/start-pitwall.sh
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable it:
```bash
sudo systemctl enable pitwall
sudo systemctl start pitwall
```

### Windows (Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task → "Pitwall"
3. Trigger: "When the computer starts"
4. Action: Start a program → `C:\path\to\start-pitwall.bat`
5. Check "Run with highest privileges"

---

## Updating F1 Data

To fetch the latest race data:

```bash
cd /path/to/pitwall
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

python update_database.py --skip-high-volume
```

Or use the admin page at `https://pitwall.one/admin` (password: `pitwall`).

---

## Troubleshooting

### "Failed to fetch" on the website
1. Check if API is running: `curl http://localhost:8000/`
2. Check if tunnel is running: `pgrep cloudflared`
3. Check logs: `tail -f /tmp/pitwall-api.log`

### Database connection errors
1. Check Docker is running: `docker ps`
2. Check PostgreSQL container: `docker logs pitwall_postgres`
3. Verify .env file has correct credentials

### Tunnel won't connect
1. Check credentials file exists: `ls ~/.cloudflared/`
2. Re-authenticate: `cloudflared tunnel login`
3. Check Cloudflare dashboard for tunnel status

### Port already in use
```bash
# Find what's using port 8000
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Kill it
kill <PID>  # Linux/Mac
taskkill /PID <PID> /F  # Windows
```

---

## File Locations Summary

| What | Location |
|------|----------|
| Project code | `/path/to/pitwall/` |
| Python venv | `/path/to/pitwall/.venv/` |
| Database data | Docker volume `pitwall_pgdata` |
| Tunnel config | `~/.cloudflared/config.yml` |
| Tunnel credentials | `~/.cloudflared/*.json` |
| API logs | `/tmp/pitwall-api.log` |
| Tunnel logs | `/tmp/cloudflared.log` |

---

## Important Credentials

| Service | Detail |
|---------|--------|
| PostgreSQL | User: `pitwall_admin`, Pass: `pitwall_admin`, Port: `5433` |
| Admin page | Password: `pitwall` |
| Tunnel ID | `d167cd07-e7b4-41d4-a6cd-309d2fd199c5` |

---

## Need Help?

- Check the logs first (`/tmp/*.log`)
- Cloudflare Tunnel docs: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/
- Docker docs: https://docs.docker.com/
- FastAPI docs: https://fastapi.tiangolo.com/

---

*Last updated: December 2025*



