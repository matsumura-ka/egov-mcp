FROM python:3.11-slim

WORKDIR /app

# Install poetry
RUN pip install poetry

# Copy poetry configuration files
COPY pyproject.toml ./

# Configure poetry to not create virtual environment
RUN poetry config virtualenvs.create false

# Copy source code
COPY egov_mcp/ ./egov_mcp/

# Install dependencies
RUN poetry install --only=main

# Expose port for MCP server
EXPOSE 8000

# Run the MCP server
CMD ["python", "-m", "egov_mcp.main"] 