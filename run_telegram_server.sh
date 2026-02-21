#!/bin/bash

BASE_DIR="/Users/orlandobruno/Documents/Dev/telegram-mcp"

# Run the MCP server using uv
uv run --directory "$BASE_DIR" python "$BASE_DIR/telegram-mcp-server/main.py"
