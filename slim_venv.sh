#!/bin/bash

echo "🧹 Slimming down .venv before npm pack..."

# Delete all __pycache__ folders
find .venv -type d -name "__pycache__" -exec rm -rf {} +

# Delete *.dist-info and *.egg-info (metadata not needed at runtime)
find .venv -type d \( -name "*.dist-info" -o -name "*.egg-info" \) -exec rm -rf {} +

# Delete tests folders (often inside packages)
find .venv -type d -name "tests" -exec rm -rf {} +

# Delete pip, setuptools, wheel (not needed for runtime)
rm -rf .venv/lib/*/site-packages/pip*
rm -rf .venv/lib/*/site-packages/setuptools*
rm -rf .venv/lib/*/site-packages/wheel*

echo "✅ .venv has been slimmed down."

