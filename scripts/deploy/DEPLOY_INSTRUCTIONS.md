# Deployment Instructions for Chat Widget Dashboard

## Quick Deployment Options

### Option 1: SCP Command (From Windows Command Prompt or Git Bash)

```bash
scp -i C:\LiveKit-Project\livekit-company-key.pem -r C:\LiveKit-Project\chat-widget-dashboard\dist\* ec2-user@oyik.info:/var/www/html/chat/
```

### Option 2: Using PowerShell

```powershell
$keyPath = "C:\LiveKit-Project\livekit-company-key.pem"
$localDir = "C:\LiveKit-Project\chat-widget-dashboard\dist"
$server = "ec2-user@oyik.info"
$remoteDir = "/var/www/html/chat"

scp -i $keyPath -r $localDir\* $server:$remoteDir
```

### Option 3: Using SFTP Client (FileZilla, WinSCP, etc.)

1. Connect to: oyik.info with user: ec2-user
2. Use key: C:\LiveKit-Project\livekit-company-key.pem
3. Navigate to: /var/www/html/chat/
4. Upload all files from: C:\LiveKit-Project\chat-widget-dashboard\dist\

### Option 4: Simplest - Upload single HTML file

Upload `C:\LiveKit-Project\chat-widget-dashboard\standalone-demo.html` as:
- Remote path: /var/www/html/chat/index.html
- Or rename to: /var/www/html/chat/widget.html

## Files to Deploy

From `C:\LiveKit-Project\chat-widget-dashboard\dist\`:

```
dist/
├── index.html                    (0.4 KB)
└── assets/
    ├── index-QxyCslUl.js         (409 KB)
    ├── index-QxyCslUl.js.map     (1.97 MB - sourcemap, optional)
    └── index-re7PRR07.css        (20.6 KB)
```

## Post-Deployment Steps

1. **Access the dashboard**: https://oyik.info/chat
2. **Verify it works**: The dashboard should load with the chat customization interface
3. **Test the widget**: Click the chat button to test the preview

## Troubleshooting

### SSH Permission Denied

If you get "Permission denied (publickey)":

1. Ensure key file exists: `C:\LiveKit-Project\livekit-company-key.pem`
2. Check file permissions should be readable
3. Try from PowerShell:
```powershell
scp -o StrictHostKeyChecking=no -i C:\LiveKit-Project\livekit-company-key.pem -r C:\LiveKit-Project\chat-widget-dashboard\dist\* ec2-user@oyik.info:/var/www/html/chat/
```

### Files Not Showing

1. Check server permissions:
```bash
ssh -i C:\LiveKit-Project\livekit-company-key.pem ec2-user@oyik.info "ls -la /var/www/html/chat/"
```

2. Set proper permissions:
```bash
ssh -i C:\LiveKit-Project\livekit-company-key.pem ec2-user@oyik.info "chmod -R 755 /var/www/html/chat/"
```

### Dashboard Not Loading

1. Check browser console (F12) for errors
2. Verify all files uploaded
3. Check server logs:
```bash
ssh -i C:\LiveKit-Project\livekit-company-key.pem ec2-user@oyik.info "tail -f /var/log/nginx/error.log"
```

## Alternative: Use Standalone Demo

If you're having trouble with the full dashboard, the standalone demo works perfectly:

Upload `C:\LiveKit-Project\chat-widget-dashboard\standalone-demo.html` as `/var/www/html/chat/index.html`

This is a single file (33KB) with:
- Complete chat widget
- No external dependencies
- Works immediately

## Verify Deployment

Once deployed, test at:
- https://oyik.info/chat (dashboard)
- Standalone version if used

The dashboard should show:
1. Configuration panel on the left
2. Live preview on the right
3. Chat button in bottom-right corner

## Default Widget Settings

The widget comes pre-configured with:
- Webhook: https://oyik.cloud/webhook/a05f977e-05e7-461d-a8a3-70f9c7c05025/chat
- Company: Ariya Property
- Theme: Orange gradient
- Quick replies for properties (rent/buy)

## Next Steps After Deployment

1. ✅ Access dashboard at https://oyik.info/chat
2. ✅ Customize colors, messages, positions
3. ✅ Test with live preview
4. ✅ Export embed code or download HTML
5. ✅ Integrate widget into other websites

## Support

For deployment issues:
- Check SSH key permissions
- Verify server is accessible
- Review browser console for errors
- Check network connectivity

---

**Dashboard location**: C:\LiveKit-Project\chat-widget-dashboard\
**Built files**: `dist/` folder (ready for deployment)
**Standalone demo**: `standalone-demo.html` (single file alternative)
