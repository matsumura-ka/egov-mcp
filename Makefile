.PHONY: help run docker-build docker-run format check lint install clean

# Default target
help:
	@echo "Available commands:"
	@echo "  help        - Show this help message"
	@echo "  install     - Install dependencies"
	@echo "  run         - Run the MCP server directly"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-run  - Run the MCP server in Docker container"
	@echo "  format      - Format code with ruff"
	@echo "  check       - Check code with ruff (lint)"
	@echo "  lint        - Alias for check"
	@echo "  clean       - Clean up Docker images and containers"

# Install dependencies and create MCP symlink
install:
	poetry install
	echo ""
	echo "✅ Installation complete!"
	echo ""
	echo "📝 MCP Client Configuration:"
	echo "Add this to your MCP client config file:"
	echo ""
	echo '{'
	echo '  "mcpServers": {'
	echo '    "egov-mcp": {'
	echo '      "command": "poetry",'
	echo '      "args": ["run", "python", "egov_mcp/main.py"],'
	echo '      "cwd": "'$$(pwd)'",'
	echo '      "env": {}'
	echo '    }'
	echo '  }'
	echo '}'
	echo ""

# Run the MCP server directly
run:
	poetry run python egov_mcp/main.py

# Build Docker image
docker-build:
	docker build -t egov-mcp .

# Run the MCP server in Docker container
docker-run: docker-build
	docker run -p 8000:8000 egov-mcp

# Format code with ruff
format:
	poetry run ruff format .

# Check code with ruff (lint)
check:
	poetry run ruff check .

# Alias for check
lint: check

# Clean up Docker images and containers
clean:
	docker rmi egov-mcp 2>/dev/null || true
	docker container prune -f

 