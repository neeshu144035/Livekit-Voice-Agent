param(
    [string]$ProjectRoot = "C:\LiveKit-Project",
    [string]$ServerUser = "ubuntu",
    [string]$ServerHost = "13.135.81.172",
    [string]$SshKey = "C:\LiveKit-Project\livekit-company-key.pem",
    [string]$ServerWebRoot = "/var/www/html",
    [switch]$CleanupLegacySource
)

$ErrorActionPreference = "Stop"

Write-Host "==> Build frontend from latest local code"
Set-Location $ProjectRoot
if (Test-Path ".next") {
    Remove-Item -Recurse -Force ".next"
}
npm run build

Write-Host "==> Package .next artifact"
$tempDir = Join-Path $env:TEMP "next-deploy"
$tarPath = Join-Path $env:TEMP "next-deploy.tar.gz"
if (Test-Path $tempDir) {
    Remove-Item -Recurse -Force $tempDir
}
if (Test-Path $tarPath) {
    Remove-Item -Force $tarPath
}
Copy-Item -Recurse -Force ".next" $tempDir
tar -czf $tarPath -C $env:TEMP "next-deploy"

Write-Host "==> Upload artifact to server"
scp -o StrictHostKeyChecking=no -i $SshKey $tarPath "${ServerUser}@${ServerHost}:/tmp/"

Write-Host "==> Replace production build and restart nextjs"
$deployCmd = "cd $ServerWebRoot && sudo rm -rf .next && sudo mkdir .next && cd .next && sudo tar -xzf /tmp/next-deploy.tar.gz && sudo mv next-deploy/* . && sudo rm -rf next-deploy && sudo chown -R www-data:www-data . && sudo pm2 restart nextjs"
ssh -o StrictHostKeyChecking=no -i $SshKey "$ServerUser@$ServerHost" $deployCmd

if ($CleanupLegacySource) {
    Write-Host "==> One-time cleanup of old server source folders"
    $cleanupCmd = "rm -rf ~/livekit-dashboard ~/livekit-dashboard-old 2>/dev/null || true"
    ssh -o StrictHostKeyChecking=no -i $SshKey "$ServerUser@$ServerHost" $cleanupCmd
}

Write-Host "==> Verify key routes"
$verifyCmd = "curl -sS -I https://oyik.info/ | head -n 5 && curl -sS -I https://oyik.info/chatbot-dashboard | head -n 5 && sudo pm2 status nextjs"
ssh -o StrictHostKeyChecking=no -i $SshKey "$ServerUser@$ServerHost" $verifyCmd

Write-Host "Deployment completed."
