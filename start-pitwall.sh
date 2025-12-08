#!/bin/bash
# Pitwall Startup Script
# Run this to start the API and tunnel for pitwall.one

echo "🏎️  Starting Pitwall..."

# Start PostgreSQL if not running
if ! docker ps | grep -q pitwall_postgres; then
    echo "Starting PostgreSQL..."
    docker start pitwall_postgres
    sleep 2
fi

# Kill any existing processes
pkill -f "uvicorn api.main" 2>/dev/null
pkill -f "cloudflared tunnel" 2>/dev/null
sleep 1

# Start API
echo "Starting API on port 8000..."
cd /Users/gavinmiller/Programming/pitwall
nohup python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 > /tmp/pitwall-api.log 2>&1 &
sleep 2

# Start Cloudflare Tunnel
echo "Starting Cloudflare Tunnel..."
nohup cloudflared tunnel run pitwall-api > /tmp/cloudflared.log 2>&1 &
sleep 3

# Verify
if curl -s "https://api.pitwall.one/" | grep -q "healthy"; then
    echo "✅ Pitwall is live at https://pitwall.one"
else
    echo "❌ Something went wrong. Check /tmp/pitwall-api.log and /tmp/cloudflared.log"
fi



