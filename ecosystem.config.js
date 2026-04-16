module.exports = {
  apps: [
    {
      name: 'frontend',
      script: 'npm',
      args: 'start',
      cwd: '/home/ubuntu/livekit-dashboard',
      interpreter: 'none',
      watch: false,
      autorestart: true
    },
    {
      name: 'api',
      script: '/home/ubuntu/livekit-dashboard-api/venv/bin/python',
      args: '-m uvicorn main:app --host 0.0.0.0 --port 8000',
      cwd: '/home/ubuntu/livekit-dashboard-api',
      interpreter: 'none',
      watch: false,
      autorestart: true
    }
  ]
};
