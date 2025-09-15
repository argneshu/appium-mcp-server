@echo off
setlocal

echo 🧹 Deleting old .venv if it exists...
rmdir /s /q .venv 2>nul

echo 🐍 Creating new virtual environment...
python -m venv .venv

if errorlevel 1 (
    echo ❌ Failed to create virtual environment. Make sure Python 3.12+ is installed and in PATH.
    exit /b 1
)

echo 📦 Installing dependencies into .venv...
call .venv\Scripts\python.exe -m ensurepip
call .venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
call .venv\Scripts\python.exe -m pip install -r requirements.txt

if errorlevel 1 (
    echo ❌ Failed to install dependencies.
    exit /b 1
)

if not exist ".venv\Lib\site-packages" (
    echo ❌ site-packages not found in .venv — install failed.
    exit /b 1
)

echo ✅ .venv setup complete.
echo.
echo 👉 To activate, run:
echo      .venv\Scripts\activate   (for cmd)
echo      .\.venv\Scripts\Activate.ps1  (for PowerShell)
echo      source .venv/Scripts/activate (for Git Bash)

endlocal
