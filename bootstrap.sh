#!/bin/bash

set -e

echo "🧹 Cleaning old .venv if it exists..."
rm -rf .venv

echo "🐍 Creating new .venv using native Apple Silicon Python..."
arch -arm64 python3.12 -m venv .venv

echo "📦 Activating .venv and installing dependencies..."
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

echo "✅ .venv setup complete. You're ready to run the MCP server!"

