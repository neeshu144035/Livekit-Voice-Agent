import sys
import os

# Ensure backend is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

def test_import_main():
    import main
    assert main.app is not None

def test_models_import():
    from backend.models import AgentModel, CallModel
    assert AgentModel.__tablename__ == "agents"
    assert CallModel.__tablename__ == "calls"
