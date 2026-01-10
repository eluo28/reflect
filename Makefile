.PHONY: help install dev backend frontend clean

help:
	@echo "Reflect - Video Editing Agent"
	@echo ""
	@echo "Commands:"
	@echo "  make install    Install all dependencies"
	@echo "  make dev        Show instructions to start services"
	@echo "  make backend    Start backend server"
	@echo "  make frontend   Start frontend dev server"
	@echo "  make clean      Remove dependencies"

install:
	@echo "Installing backend dependencies..."
	cd backend && poetry install
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
	@echo "Done!"

backend:
	@echo "Starting backend (connecting to MongoDB Atlas)..."
	cd backend && poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	@echo "Starting frontend..."
	cd frontend && npm run dev

dev:
	@echo ""
	@echo "Reflect - Video Editing Agent"
	@echo "=============================="
	@echo ""
	@echo "MongoDB: Using MongoDB Atlas (configured in backend/.env)"
	@echo ""
	@echo "Run in separate terminals:"
	@echo "  Terminal 1: make backend   -> http://localhost:8000"
	@echo "  Terminal 2: make frontend  -> http://localhost:5173"
	@echo ""

clean:
	@echo "Cleaning up..."
	rm -rf backend/.venv
	rm -rf frontend/node_modules
	@echo "Done!"
