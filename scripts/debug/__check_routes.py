import main
print('main_file', getattr(main, '__file__', ''))
print('has_test_chat', any(getattr(r, 'path', '') == '/api/agents/{agent_id}/test-chat' for r in main.app.routes))
for r in main.app.routes:
    p = getattr(r, 'path', '')
    if p.startswith('/api/agents/'):
        print('route', p, getattr(r, 'methods', ''))
