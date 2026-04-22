import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def test_import_agent():
    import agent_retell
    assert hasattr(agent_retell, 'entrypoint')

def test_voice_agent_config():
    from voice_agent.config import DASHBOARD_API_URL, MAX_CALL_DURATION
    assert DASHBOARD_API_URL is not None
    assert MAX_CALL_DURATION > 0
