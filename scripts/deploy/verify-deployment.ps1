# LiveKit Voice AI Platform - Deployment & Verification Script
# Run this after deploying code to verify everything is working

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "LiveKit Voice AI - Deployment Verification" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$PROJECT_ROOT = "C:\LiveKit-Project"
$REMOTE_HOST = "13.135.81.172"
$REMOTE_USER = "ubuntu"
$SSH_KEY = "$PROJECT_ROOT\livekit-company-key.pem"
$BACKEND_URL = "http://127.0.0.1:8000"

# Step 1: Local Compilation Checks
Write-Host "[1/6] Checking local compilation..." -ForegroundColor Yellow

Write-Host "  - Checking backend Python files..." -NoNewline
$backendCheck = python -m py_compile backend/main.py 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host " OK" -ForegroundColor Green
} else {
    Write-Host " FAILED" -ForegroundColor Red
    Write-Host $backendCheck
    exit 1
}

Write-Host "  - Checking TypeScript compilation..." -NoNewline
$tsCheck = npx tsc --noEmit 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host " OK" -ForegroundColor Green
} else {
    Write-Host " FAILED" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 2: Remote Health Checks
Write-Host "[2/6] Checking remote health endpoints..." -ForegroundColor Yellow

Write-Host "  - Backend health..." -NoNewline
$backendHealth = ssh -i $SSH_KEY ${REMOTE_USER}@${REMOTE_HOST} "curl -s ${BACKEND_URL}/health" 2>&1
if ($LASTEXITCODE -eq 0 -and $backendHealth -match "healthy") {
    Write-Host " OK" -ForegroundColor Green
} else {
    Write-Host " FAILED" -ForegroundColor Red
    Write-Host "  Response: $backendHealth"
}

Write-Host "  - PM2 processes..." -NoNewline
$pm2Status = ssh -i $SSH_KEY ${REMOTE_USER}@${REMOTE_HOST} "pm2 status" 2>&1
if ($LASTEXITCODE -eq 0 -and $pm2Status -match "online") {
    Write-Host " OK" -ForegroundColor Green
} else {
    Write-Host " CHECK MANUALLY" -ForegroundColor Yellow
}

Write-Host "  - Docker containers..." -NoNewline
$dockerStatus = ssh -i $SSH_KEY ${REMOTE_USER}@${REMOTE_HOST} "docker ps --format '{{.Names}}: {{.Status}}'" 2>&1
if ($LASTEXITCODE -eq 0 -and $dockerStatus -match "voice-agent") {
    Write-Host " OK" -ForegroundColor Green
    Write-Host "  $dockerStatus" -ForegroundColor Gray
} else {
    Write-Host " CHECK MANUALLY" -ForegroundColor Yellow
}

Write-Host ""

# Step 3: API Endpoint Tests
Write-Host "[3/6] Testing API endpoints..." -ForegroundColor Yellow

Write-Host "  - Agent list..." -NoNewline
$agentList = ssh -i $SSH_KEY ${REMOTE_USER}@${REMOTE_HOST} "curl -s ${BACKEND_URL}/api/agents/" 2>&1
if ($LASTEXITCODE -eq 0 -and $agentList -match "id") {
    Write-Host " OK" -ForegroundColor Green
} else {
    Write-Host " FAILED" -ForegroundColor Red
}

Write-Host "  - TTS providers..." -NoNewline
$ttsProviders = ssh -i $SSH_KEY ${REMOTE_USER}@${REMOTE_HOST} "curl -s ${BACKEND_URL}/api/tts/providers" 2>&1
if ($LASTEXITCODE -eq 0 -and $ttsProviders -match "deepgram") {
    Write-Host " OK" -ForegroundColor Green
} else {
    Write-Host " FAILED" -ForegroundColor Red
}

Write-Host "  - Phone numbers SIP endpoint..." -NoNewline
$sipEndpoint = ssh -i $SSH_KEY ${REMOTE_USER}@${REMOTE_HOST} "curl -s ${BACKEND_URL}/api/phone-numbers/sip-endpoint" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host " OK" -ForegroundColor Green
} else {
    Write-Host " FAILED" -ForegroundColor Red
}

Write-Host ""

# Step 4: Database Migration Status
Write-Host "[4/6] Checking Alembic migration status..." -ForegroundColor Yellow

$migrationStatus = ssh -i $SSH_KEY ${REMOTE_USER}@${REMOTE_HOST} "cd ~/livekit-dashboard-api && python -m alembic current" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host " Current migration: $migrationStatus" -ForegroundColor Green
} else {
    Write-Host " CHECK MANUALLY" -ForegroundColor Yellow
}

Write-Host ""

# Step 5: Voice Agent Logs
Write-Host "[5/6] Checking voice agent logs..." -ForegroundColor Yellow

$agentLogs = ssh -i $SSH_KEY ${REMOTE_USER}@${REMOTE_HOST} "docker logs --tail 20 voice-agent" 2>&1
if ($LASTEXITCODE -eq 0 -and $agentLogs -match "Worker started") {
    Write-Host " Agent running OK" -ForegroundColor Green
} elseif ($LASTEXITCODE -eq 0) {
    Write-Host " Agent logs:" -ForegroundColor Yellow
    Write-Host $agentLogs
} else {
    Write-Host " CHECK MANUALLY" -ForegroundColor Red
}

Write-Host ""

# Step 6: Summary
Write-Host "[6/6] Summary" -ForegroundColor Yellow
Write-Host ""
Write-Host "Deployment verification complete!" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Place a test call to verify end-to-end flow" -ForegroundColor White
Write-Host "2. Check call history in dashboard" -ForegroundColor White
Write-Host "3. Verify cost tracking is working" -ForegroundColor White
Write-Host "4. Test agent configuration updates" -ForegroundColor White
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Cyan
Write-Host "  - Backend logs: ssh -i $SSH_KEY ${REMOTE_USER}@${REMOTE_HOST} 'pm2 logs api'" -ForegroundColor Gray
Write-Host "  - Agent logs: ssh -i $SSH_KEY ${REMOTE_USER}@${REMOTE_HOST} 'docker logs voice-agent'" -ForegroundColor Gray
Write-Host "  - Database: ssh -i $SSH_KEY ${REMOTE_USER}@${REMOTE_HOST} 'cd ~/livekit-dashboard-api && python -m alembic upgrade head'" -ForegroundColor Gray
Write-Host ""
