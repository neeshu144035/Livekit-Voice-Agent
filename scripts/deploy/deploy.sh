#!/bin/bash

# Deploy script for Voice AI Platform
# Run this on your server: bash deploy.sh

set -e

echo "========================================="
echo "Voice AI Platform - Deployment Script"
echo "========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
   echo "Please run as root or with sudo"
   exit 1
fi

# Configuration
PROJECT_DIR="/root/livekit-voice-ai"
BACKEND_DIR="$PROJECT_DIR/backend"
AGENT_DIR="$PROJECT_DIR/agent"

# Create project directory
mkdir -p $PROJECT_DIR

# Copy files from local to server (this will be done via scp in real deployment)
echo "Please ensure all project files are in $PROJECT_DIR"

# Navigate to project directory
cd $PROJECT_DIR

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << 'EOF'
DEEPGRAM_API_KEY=your_deepgram_api_key
MOONSHOT_API_KEY=your_moonshot_api_key
OPENAI_API_KEY=your_openai_api_key
EOF
    echo "Please update .env with your API keys!"
fi

# Stop existing containers
echo "Stopping existing containers..."
docker-compose -f docker-compose.production.yml down 2>/dev/null || true

# Build and start services
echo "Building Docker images..."
docker-compose -f docker-compose.production.yml build

echo "Starting services..."
docker-compose -f docker-compose.production.yml up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

# Check service status
echo "Checking service status..."
docker-compose -f docker-compose.production.yml ps

# Check logs
echo "========================================="
echo "Backend API Logs:"
docker logs backend-api --tail 20
echo "========================================="
echo "Voice Agent Logs:"
docker logs voice-agent-1 --tail 20
echo "========================================="
echo "LiveKit Server Logs:"
docker logs livekit-server --tail 20

echo "========================================="
echo "Deployment complete!"
echo "========================================="
echo "Backend API: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "LiveKit: ws://localhost:7880"
echo "========================================="
