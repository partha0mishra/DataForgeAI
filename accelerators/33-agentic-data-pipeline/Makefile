.PHONY: help install dev test lint format clean docker-build docker-up docker-down

help:
	@echo "Agentic Data Pipeline Generator - Available Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install       Install production dependencies"
	@echo "  make dev           Install development dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make test          Run tests with coverage"
	@echo "  make lint          Run linting (ruff + mypy)"
	@echo "  make format        Format code with black"
	@echo "  make clean         Clean generated files"
	@echo ""
	@echo "Running:"
	@echo "  make ui            Start Streamlit UI"
	@echo "  make api           Start FastAPI server"
	@echo "  make cli           Run CLI help"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build  Build Docker images"
	@echo "  make docker-up     Start all services"
	@echo "  make docker-down   Stop all services"
	@echo ""

install:
	pip install -e .

dev:
	pip install -e ".[dev]"
	pre-commit install

test:
	pytest --cov=agentic_data_pipeline --cov-report=html --cov-report=term

test-watch:
	ptw -- --cov=agentic_data_pipeline

lint:
	ruff check src/ tests/
	mypy src/

format:
	black src/ tests/
	ruff check src/ tests/ --fix

clean:
	rm -rf build/ dist/ *.egg-info
	rm -rf .pytest_cache .coverage htmlcov
	rm -rf .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf data/pipelines.db data/chroma logs/*.log

ui:
	streamlit run src/agentic_data_pipeline/ui.py

api:
	uvicorn agentic_data_pipeline.api:app --reload

cli:
	agentic-pipeline --help

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d
	@echo "Services started:"
	@echo "  UI:  http://localhost:8501"
	@echo "  API: http://localhost:8000"

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

# Create necessary directories
init:
	mkdir -p data/chroma logs output
	cp .env.example .env
	@echo "Created directories and .env file. Please edit .env with your API keys."
