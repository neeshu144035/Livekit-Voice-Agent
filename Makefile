.PHONY: dev build test lint format clean deploy-agent deploy-backend deploy-frontend

# Development
dev:
	npm run dev

dev-backend:
	cd backend && uvicorn main:app --reload --port 8000

dev-agent:
	python agent_retell.py start

# Build
build:
	npm run build

# Testing
test:
	pytest tests/ -v

test-frontend:
	npx vitest run

# Linting & Formatting
lint:
	npx tsc --noEmit
	python -m py_compile backend/main.py agent_retell.py

format:
	black backend/ voice_agent/ tests/
	pre-commit run --all-files

# Cleanup
clean:
	rm -rf .next node_modules __pycache__ .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Deployment helpers (requires livekit-company-key.pem)
deploy-frontend: build
	@echo "Deploy frontend manually via scripts/deploy/deploy.sh or PM2"

deploy-backend:
	scp -i livekit-company-key.pem backend/main.py ubuntu@13.135.81.172:~/livekit-dashboard-api/main.py
	ssh -i livekit-company-key.pem ubuntu@13.135.81.172 "sudo pm2 restart api --update-env"

deploy-agent:
	scp -i livekit-company-key.pem agent_retell.py ubuntu@13.135.81.172:~/livekit-agent/agent_retell.py
	ssh -i livekit-company-key.pem ubuntu@13.135.81.172 "cd ~/livekit-agent && docker compose up -d --build voice-agent"
