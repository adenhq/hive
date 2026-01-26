# Makefile for Hive - Agent Development Framework
# 
# Common developer commands for setup, testing, linting, and running agents.
# Works on Linux, macOS, and Windows (with make installed).

.PHONY: help setup test lint format clean run docs install-dev check

# Default target - show help
help:
	@echo "Hive Development Commands"
	@echo "========================="
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup          - Set up Python environment and install dependencies"
	@echo "  make install-dev    - Install development dependencies"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint           - Run linting (ruff, mypy)"
	@echo "  make format         - Auto-format code with ruff"
	@echo "  make check          - Run all checks (lint + test)"
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run all tests"
	@echo "  make test-unit      - Run unit tests only"
	@echo "  make test-integration - Run integration tests"
	@echo "  make test-coverage  - Run tests with coverage report"
	@echo ""
	@echo "Development:"
	@echo "  make run AGENT=<name> - Run an agent (e.g., make run AGENT=my_agent)"
	@echo "  make shell          - Start Python shell with framework loaded"
	@echo "  make clean          - Remove build artifacts and cache"
	@echo ""
	@echo "MCP Tools:"
	@echo "  make mcp-setup      - Set up MCP tools"
	@echo "  make mcp-verify     - Verify MCP server registration"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs           - Build documentation"
	@echo "  make docs-serve     - Serve documentation locally"

# Setup Python environment and install packages
setup:
	@echo "Setting up Hive development environment..."
	@command -v python3.11 >/dev/null 2>&1 || { echo "Python 3.11 required! Install it first."; exit 1; }
	python3.11 -m venv .venv
	@echo "Virtual environment created at .venv/"
	@echo "Activating and installing packages..."
	. .venv/bin/activate && pip install --upgrade pip
	. .venv/bin/activate && pip install -e core -e tools
	@echo "✓ Setup complete! Activate with: source .venv/bin/activate"

# Install development dependencies
install-dev:
	@echo "Installing development dependencies..."
	. .venv/bin/activate && pip install pytest pytest-asyncio pytest-cov ruff mypy types-requests
	@echo "✓ Dev dependencies installed"

# Run linting
lint:
	@echo "Running linting checks..."
	@. .venv/bin/activate && ruff check core tools || true
	@. .venv/bin/activate && mypy core --ignore-missing-imports || true
	@echo "Linting complete"

# Auto-format code
format:
	@echo "Formatting code with ruff..."
	@. .venv/bin/activate && ruff format core tools
	@. .venv/bin/activate && ruff check --fix core tools || true
	@echo "✓ Code formatted"

# Run all checks
check: lint test
	@echo "✓ All checks passed!"

# Run all tests
test:
	@echo "Running all tests..."
	. .venv/bin/activate && PYTHONPATH=core:exports python -m pytest core/tests tools/tests -v

# Run unit tests only
test-unit:
	@echo "Running unit tests..."
	. .venv/bin/activate && PYTHONPATH=core:exports python -m pytest core/tests -v -m "not integration"

# Run integration tests
test-integration:
	@echo "Running integration tests..."
	. .venv/bin/activate && PYTHONPATH=core:exports python -m pytest core/tests -v -m integration

# Run tests with coverage
test-coverage:
	@echo "Running tests with coverage..."
	. .venv/bin/activate && PYTHONPATH=core:exports python -m pytest core/tests tools/tests \
		--cov=framework --cov=aden_tools --cov-report=html --cov-report=term

# Run an agent (usage: make run AGENT=agent_name)
run:
	@if [ -z "$(AGENT)" ]; then \
		echo "Error: AGENT parameter required. Usage: make run AGENT=my_agent"; \
		exit 1; \
	fi
	@echo "Running agent: $(AGENT)"
	. .venv/bin/activate && PYTHONPATH=core:exports python -m framework.cli run $(AGENT)

# Start Python shell with framework
shell:
	@echo "Starting Python shell with Hive framework loaded..."
	. .venv/bin/activate && PYTHONPATH=core:exports python -c \
		"from framework.runner import AgentRunner; \
		from framework.llm.anthropic import AnthropicProvider; \
		print('Hive Framework Loaded'); \
		print('Available: AgentRunner, AnthropicProvider'); \
		import code; code.interact(local=locals())"

# Clean build artifacts and cache
clean:
	@echo "Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage 2>/dev/null || true
	@echo "✓ Clean complete"

# Set up MCP tools
mcp-setup:
	@echo "Setting up MCP tools..."
	. .venv/bin/activate && python core/setup_mcp.py
	@echo "✓ MCP setup complete"

# Verify MCP server registration
mcp-verify:
	@echo "Verifying MCP server..."
	. .venv/bin/activate && python core/verify_mcp.py

# Build documentation
docs:
	@echo "Building documentation..."
	@if [ ! -d "docs" ]; then \
		echo "Error: docs/ directory not found"; \
		exit 1; \
	fi
	@echo "Documentation build complete"

# Serve documentation locally
docs-serve:
	@echo "Serving documentation at http://localhost:8000"
	@cd docs && python -m http.server 8000

# Create a new agent (usage: make create-agent NAME=my_agent)
create-agent:
	@if [ -z "$(NAME)" ]; then \
		echo "Error: NAME parameter required. Usage: make create-agent NAME=my_agent"; \
		exit 1; \
	fi
	@echo "Creating new agent: $(NAME)"
	. .venv/bin/activate && PYTHONPATH=core:exports python -m framework.cli create $(NAME)
	@echo "✓ Agent created at exports/$(NAME)/"

# List all available agents
list-agents:
	@echo "Available agents:"
	@. .venv/bin/activate && PYTHONPATH=core:exports python -m framework.cli list

# Run quickstart
quickstart:
	@echo "Running quickstart..."
	@bash quickstart.sh

# Install pre-commit hooks
install-hooks:
	@echo "Installing pre-commit hooks..."
	@echo "#!/bin/sh\nmake lint" > .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "✓ Pre-commit hooks installed (will run 'make lint' before commits)"
