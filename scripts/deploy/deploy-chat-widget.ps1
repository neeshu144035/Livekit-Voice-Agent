# PowerShell script to deploy chat widget
$keyPath = "C:\LiveKit-Project\livekit-company-key.pem"
$localDir = "C:\LiveKit-Project\chat-widget-dashboard\dist"
$server = "ec2-user@oyik.info"
$remoteDir = "/var/www/html/chat"

Write-Host "Deploying chat widget dashboard..." -ForegroundColor Green
Write-Host "Local: $localDir" -ForegroundColor Cyan
Write-Host "Remote: $server:$remoteDir" -ForegroundColor Cyan

# Create archive
Write-Host "Creating archive..." -ForegroundColor Yellow
Compress-Archive -Path "$localDir\*" -DestinationPath "C:\LiveKit-Project\chat-dashboard.zip" -Force

Write-Host "Archive created: C:\LiveKit-Project\chat-dashboard.zip" -ForegroundColor Green
Write-Host "Files to deploy:"
Get-ChildItem -Path $localDir -Recurse | Select-Object FullName, Length

Write-Host "`nDeployment commands to run manually:" -ForegroundColor Yellow
Write-Host "1. Copy files using SCP or SFTP client to: $server:$remoteDir" -ForegroundColor Cyan
Write-Host "2. Or extract and upload using FTP client" -ForegroundColor Cyan
Write-Host "3. Test at: https://oyik.info/chat" -ForegroundColor Cyan
