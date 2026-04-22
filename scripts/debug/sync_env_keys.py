from pathlib import Path
backend_env = Path('/home/ubuntu/livekit-dashboard-api/.env')
agent_env = Path('/home/ubuntu/livekit-agent/.env')
if not backend_env.exists() or not agent_env.exists():
    raise SystemExit('env file missing')

def parse_env(path: Path):
    data = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        data[k.strip()] = v.strip()
    return data

backend = parse_env(backend_env)
agent = parse_env(agent_env)
changed = False
for key in ('OPENAI_API_KEY', 'MOONSHOT_API_KEY'):
    if (not backend.get(key)) and agent.get(key):
        backend[key] = agent[key]
        changed = True

if changed:
    backend_env.write_text('\\n'.join(f'{k}={v}' for k, v in backend.items()) + '\\n')
print('changed' if changed else 'nochange')
