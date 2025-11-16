.PHONY: help install test clean dev-up dev-down deploy-prod

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo '$(BLUE)DataForge AI Platform - Make Commands$(NC)'
	@echo ''
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-30s$(NC) %s\n", $$1, $$2}'

install: ## Install all dependencies
	@echo '$(BLUE)Installing shared libraries...$(NC)'
	cd shared/common && pip install -e .
	cd shared/connectors && pip install -e .
	cd shared/ai-core && pip install -e .
	@echo '$(GREEN)Dependencies installed successfully!$(NC)'

install-dev: ## Install development dependencies
	@echo '$(BLUE)Installing development dependencies...$(NC)'
	pip install pytest pytest-cov black flake8 mypy pre-commit
	pre-commit install
	@echo '$(GREEN)Development environment ready!$(NC)'

test: ## Run all tests
	@echo '$(BLUE)Running tests...$(NC)'
	pytest tests/ -v --cov=shared --cov=accelerators --cov-report=html
	@echo '$(GREEN)Tests completed!$(NC)'

test-accelerator: ## Test specific accelerator (usage: make test-accelerator ACC=01-pipeline-automation)
	@echo '$(BLUE)Testing accelerator $(ACC)...$(NC)'
	cd accelerators/$(ACC) && pytest tests/ -v
	@echo '$(GREEN)Accelerator tests completed!$(NC)'

test-integration: ## Run integration tests
	@echo '$(BLUE)Running integration tests...$(NC)'
	pytest tests/integration/ -v
	@echo '$(GREEN)Integration tests completed!$(NC)'

test-coverage: ## Run tests with coverage report
	@echo '$(BLUE)Generating coverage report...$(NC)'
	pytest tests/ --cov=. --cov-report=html --cov-report=term
	@echo '$(GREEN)Coverage report generated at htmlcov/index.html$(NC)'

lint: ## Run code linting
	@echo '$(BLUE)Running linters...$(NC)'
	black --check shared/ accelerators/ platform-services/
	flake8 shared/ accelerators/ platform-services/
	mypy shared/ accelerators/ platform-services/
	@echo '$(GREEN)Linting completed!$(NC)'

format: ## Format code with black
	@echo '$(BLUE)Formatting code...$(NC)'
	black shared/ accelerators/ platform-services/
	@echo '$(GREEN)Code formatted!$(NC)'

clean: ## Clean build artifacts
	@echo '$(BLUE)Cleaning build artifacts...$(NC)'
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov/ .coverage build/ dist/
	@echo '$(GREEN)Cleaned!$(NC)'

dev-up: ## Start all services locally with Docker Compose
	@echo '$(BLUE)Starting DataForge AI Platform...$(NC)'
	docker-compose -f deployments/local/docker-compose.yml up -d
	@echo '$(GREEN)Platform is running!$(NC)'
	@echo '$(YELLOW)Access services at:$(NC)'
	@echo '  - Airflow: http://localhost:8080'
	@echo '  - MLflow: http://localhost:5000'
	@echo '  - Superset: http://localhost:8088'
	@echo '  - Grafana: http://localhost:3001'
	@echo '  - Knowledge Repo: http://localhost:3000'

dev-down: ## Stop all local services
	@echo '$(BLUE)Stopping services...$(NC)'
	docker-compose -f deployments/local/docker-compose.yml down
	@echo '$(GREEN)Services stopped!$(NC)'

dev-logs: ## View logs from all services
	docker-compose -f deployments/local/docker-compose.yml logs -f

dev-rebuild: ## Rebuild and restart all services
	@echo '$(BLUE)Rebuilding services...$(NC)'
	docker-compose -f deployments/local/docker-compose.yml up -d --build
	@echo '$(GREEN)Services rebuilt!$(NC)'

build-shared: ## Build shared library packages
	@echo '$(BLUE)Building shared libraries...$(NC)'
	cd shared/common && python setup.py sdist bdist_wheel
	cd shared/connectors && python setup.py sdist bdist_wheel
	cd shared/ai-core && python setup.py sdist bdist_wheel
	@echo '$(GREEN)Shared libraries built!$(NC)'

publish-shared: build-shared ## Publish shared libraries to PyPI
	@echo '$(BLUE)Publishing shared libraries...$(NC)'
	twine upload shared/*/dist/*
	@echo '$(GREEN)Libraries published!$(NC)'

create-accelerator: ## Create new accelerator (usage: make create-accelerator NAME=my-accelerator)
	@echo '$(BLUE)Creating new accelerator: $(NAME)...$(NC)'
	mkdir -p accelerators/$(NAME)/{src,tests,k8s,config}
	touch accelerators/$(NAME)/README.md
	touch accelerators/$(NAME)/Dockerfile
	touch accelerators/$(NAME)/requirements.txt
	@echo '$(GREEN)Accelerator $(NAME) created!$(NC)'

deploy-prod: ## Deploy entire platform to production Kubernetes
	@echo '$(BLUE)Deploying to production...$(NC)'
	kubectl apply -f deployments/production/namespace.yaml
	kubectl apply -f deployments/production/
	@echo '$(GREEN)Deployed to production!$(NC)'

deploy-accelerator: ## Deploy specific accelerator (usage: make deploy-accelerator ACC=01-pipeline-automation)
	@echo '$(BLUE)Deploying accelerator $(ACC)...$(NC)'
	kubectl apply -f accelerators/$(ACC)/k8s/
	@echo '$(GREEN)Accelerator deployed!$(NC)'

terraform-init: ## Initialize Terraform
	@echo '$(BLUE)Initializing Terraform...$(NC)'
	cd terraform && terraform init
	@echo '$(GREEN)Terraform initialized!$(NC)'

terraform-plan: ## Plan Terraform changes
	@echo '$(BLUE)Planning infrastructure changes...$(NC)'
	cd terraform && terraform plan
	@echo '$(GREEN)Plan completed!$(NC)'

terraform-apply: ## Apply Terraform changes
	@echo '$(BLUE)Applying infrastructure changes...$(NC)'
	cd terraform && terraform apply
	@echo '$(GREEN)Infrastructure deployed!$(NC)'

docs-serve: ## Serve documentation locally
	@echo '$(BLUE)Starting documentation server...$(NC)'
	cd docs && mkdocs serve
	@echo '$(GREEN)Docs available at http://localhost:8000$(NC)'

docs-build: ## Build documentation
	@echo '$(BLUE)Building documentation...$(NC)'
	cd docs && mkdocs build
	@echo '$(GREEN)Documentation built!$(NC)'

security-scan: ## Run security vulnerability scan
	@echo '$(BLUE)Scanning for vulnerabilities...$(NC)'
	safety check
	bandit -r shared/ accelerators/ platform-services/
	@echo '$(GREEN)Security scan completed!$(NC)'

docker-build-all: ## Build all Docker images
	@echo '$(BLUE)Building all Docker images...$(NC)'
	./scripts/build-all-images.sh
	@echo '$(GREEN)All images built!$(NC)'

k8s-status: ## Check Kubernetes deployment status
	@echo '$(BLUE)Checking deployment status...$(NC)'
	kubectl get pods -n dataforge
	kubectl get services -n dataforge
	kubectl get deployments -n dataforge

k8s-logs: ## View logs from Kubernetes pods (usage: make k8s-logs POD=airflow-webserver)
	kubectl logs -f $(POD) -n dataforge

setup: install install-dev ## Complete initial setup
	@echo '$(GREEN)Setup completed! Run "make dev-up" to start the platform.$(NC)'
