# Frontend Single-Source Deployment

This folder is the only approved frontend deployment path.

## Goal

- Build frontend from local latest code only.
- Deploy only `.next` artifacts to production.
- Replace production build fully on each deploy.
- Avoid stale code from old server source folders.

## Single source of truth

- Local source: `C:\LiveKit-Project`
- Live runtime path: `/var/www/html/.next`
- PM2 process: `nextjs`

Do not deploy frontend from `~/livekit-dashboard` or restart `frontend`.

## Use

```powershell
powershell -ExecutionPolicy Bypass -File .\deployment\frontend-single-source\deploy-frontend.ps1
```

Optional one-time legacy cleanup on server:

```powershell
powershell -ExecutionPolicy Bypass -File .\deployment\frontend-single-source\deploy-frontend.ps1 -CleanupLegacySource
```

