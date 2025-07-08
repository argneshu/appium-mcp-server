@echo off
setlocal

echo 🧹 Deleting old .venv if it exists...
rmdir /s /q .venv

echo 🐍 Creating new virtual environment...
python -m venv .venv

if errorlevel 1 (
    echo ❌ Failed to create virtual environment. Make sure Python 3.12+ is installed and in PATH.
    exit /b 1
)

echo 📦 Activating virtual environment and installing dependencies...
call .venv\Scripts\activate

python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo ❌ Failed to install dependencies.
    exit /b 1
)

echo ✅ .venv setup complete. You can now run the MCP server.
endlocal

