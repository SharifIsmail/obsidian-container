#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

# --- .env ---
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from template."
    echo "Edit .env to set your KasmVNC username and password, then re-run this script."
    exit 0
fi

# Check if .env still has placeholder values
if grep -q "your-username\|your-password" .env; then
    echo "Edit .env to set your KasmVNC username and password, then re-run this script."
    exit 1
fi

# --- Config directory ---
CONFIG_PATH="${CONFIG_PATH:-./config}"

if [ ! -d "$CONFIG_PATH/cmd-service" ]; then
    mkdir -p "$CONFIG_PATH/cmd-service"
    cp config-seed/cmd-service/* "$CONFIG_PATH/cmd-service/"
    echo "Seeded $CONFIG_PATH/cmd-service/ with default config."
    echo "Add at least one token to $CONFIG_PATH/cmd-service/tokens.md"
fi

# --- Start ---
docker compose up -d
echo ""
echo "Obsidian is running."
echo "  Web UI:          http://localhost:3000"
echo "  Web UI (HTTPS):  https://localhost:3001"
echo "  Command service: http://localhost:9999"
echo ""
echo "Add tokens to $CONFIG_PATH/cmd-service/tokens.md to use the command API."
