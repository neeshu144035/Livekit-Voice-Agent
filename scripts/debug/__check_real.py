import importlib.util
p = '/home/ubuntu/livekit-dashboard-api/main.py'
spec = importlib.util.spec_from_file_location('live_main', p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
print('loaded', p)
print('has_test_chat', any(getattr(r, 'path', '') == '/api/agents/{agent_id}/test-chat' for r in m.app.routes))
for r in m.app.routes:
    path = getattr(r, 'path', '')
    if 'test-chat' in path:
        print('route', path, getattr(r, 'methods', ''))
