# DEPLOYMENT READY! 🚀

## Files Are Ready at: C:\LiveKit-Project\chat-widget-dashboard\

## Option 1: EASIEST - Upload Single File

**File to upload:** `C:\LiveKit-Project\chat-widget-dashboard\standalone-demo.html`

**Upload to:** `/var/www/html/chat/index.html` on oyik.info

**How to upload:**
1. Open FileZilla, WinSCP, or any SFTP client
2. Connect with:
   - Host: oyik.info
   - User: ec2-user
   - Key file: C:\LiveKit-Project\livekit-company-key.pem
3. Navigate to: /var/www/html/chat/
4. Upload standalone-demo.html
5. Rename it to index.html
6. Access at: https://oyik.info/chat

**That's it!** The chat widget will work immediately.

---

## Option 2: FULL DASHBOARD (Recommended)

**Upload these files from: C:\LiveKit-Project\chat-widget-dashboard\dist\**

Required files:
- index.html (0.4 KB) → /var/www/html/chat/
- assets/index-QxyCslUl.js (409 KB) → /var/www/html/chat/assets/
- assets/index-re7PRR07.css (20.6 KB) → /var/www/html/chat/assets/

Optional:
- assets/index-QxyCslUl.js.map (1.9 MB) - sourcemap for debugging

**Upload steps:**
1. Connect via SFTP (same as above)
2. Create folder: /var/www/html/chat/assets/
3. Upload dist/index.html to /var/www/html/chat/
4. Upload dist/assets/index-QxyCslUl.js to /var/www/html/chat/assets/
5. Upload dist/assets/index-re7PRR07.css to /var/www/html/chat/assets/
6. Access at: https://oyik.info/chat

---

## Command Line Deployment (PowerShell or Git Bash)

### From PowerShell:
```powershell
scp -i "C:\LiveKit-Project\livekit-company-key.pem" `
  -o StrictHostKeyChecking=no `
  -r "C:\LiveKit-Project\chat-widget-dashboard\dist\*" `
  ec2-user@oyik.info:/var/www/html/chat/
```

### From Git Bash (if available):
```bash
scp -i C:/LiveKit-Project/livekit-company-key.pem \
  -o StrictHostKeyChecking=no \
  -r C:/LiveKit-Project/chat-widget-dashboard/dist/* \
  ec2-user@oyik.info:/var/www/html/chat/
```

---

## What You'll Get at https://oyik.info/chat

### With Full Dashboard:
- Dark-themed customization dashboard
- Configuration panel (left side):
  * Webhook URL
  * Company name
  * Welcome message
  * Button position
  * Colors (4 presets + custom)
  * Quick replies
- Live preview panel (right side)
- Export button (embed code + HTML download)

### With Standalone Demo:
- Full featured chat widget
- No dashboard
- Widget works immediately
- Button in bottom-right corner

---

## Quick Test After Deployment

1. Visit: https://oyik.info/chat
2. Full Dashboard: Customize and preview in real-time
3. Standalone: Click chat button to test

---

## Default Widget Settings

- Webhook: https://oyik.cloud/webhook/a05f977e-05e7-461d-a8a3-70f9c7c05025/chat
- Company: Ariya Property
- Theme: Orange gradient
- Quick replies: Rent property, Buy property

You can change all settings in the dashboard!

---

## Troubleshooting

If you can't connect via SSH:
- Use SFTP client (FileZilla, WinSCP) instead
- Manual upload works perfectly

If files don't load:
- Check all files uploaded correctly
- Verify /var/www/html/chat/ is world-readable
- Open browser console (F12) for errors

---

## Files Summary

| File | Size | Description |
|------|------|-------------|
| dist/index.html | 0.4 KB | Main dashboard page |
| dist/assets/*.js | 409 KB | Dashboard JavaScript |
| dist/assets/*.css | 20.6 KB | Dashboard styles |
| standalone-demo.html | 33.5 KB | Single-file widget demo |

---

**CHOOSE YOUR OPTION:**
- Quick: Upload standalone-demo.html
- Full: Upload dist/ folder contents

**ACCESS:** https://oyik.info/chat

**TIME ESTIMATE:** 2-5 minutes to upload

**STATUS:** ✅ READY TO DEPLOY!

---

For detailed instructions: See MANUAL_DEPLOY.txt or DEPLOY_INSTRUCTIONS.md
