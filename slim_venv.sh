#!/bin/bash

echo "🧹 Slimming down .venv before npm pack..."

# Detect site-packages path (supports python3.10–3.12)
SITE_PACKAGES=$(find .venv/lib -type d -name "site-packages" | head -n 1)

if [ -z "$SITE_PACKAGES" ]; then
  echo "❌ Could not find site-packages inside .venv"
  exit 1
fi

echo "📂 site-packages found at: $SITE_PACKAGES"

# 1. Delete __pycache__ folders
find "$SITE_PACKAGES" -type d -name "__pycache__" -exec rm -rf {} +

# 2. Delete tests folders
find "$SITE_PACKAGES" -type d -name "tests" -exec rm -rf {} +

# 3. Keep only mcp-*.dist-info, remove all others
find "$SITE_PACKAGES" -type d -name "*.dist-info" ! -iname "mcp-*.dist-info" -exec rm -rf {} +

# 4. Delete *.egg-info folders
find "$SITE_PACKAGES" -type d -name "*.egg-info" -exec rm -rf {} +

# 5. Remove build-time tools
rm -rf "$SITE_PACKAGES"/pip*
rm -rf "$SITE_PACKAGES"/setuptools*
rm -rf "$SITE_PACKAGES"/wheel*

echo "✅ .venv has been slimmed down."
du -sh .venv
