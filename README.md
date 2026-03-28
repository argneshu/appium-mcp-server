# Appium MCP Server

A Model Context Protocol (MCP) server that provides Appium mobile automation capabilities to Claude and other MCP-compatible clients.

## Features

- **Cross-platform mobile automation**: Support for both iOS and Android
- **Multiple app launch modes**: Native apps, browser automation, or installed apps
- **Element interaction**: Find, tap, and input text to mobile elements
- **Session management**: Start, monitor, and terminate Appium sessions
- **Page inspection**: Get page source and scroll functionality
- **Easy integration**: Works seamlessly with Claude Desktop and other MCP clients

## Prerequisites

- **Python 3.12+** installed on your system : Environment variable should be set correctly in your bash or zsh so that claude can read it from your system
- **Node.js 18.1+** (for npx usage)
- **Appium Server** running on `http://localhost:4723`
- **Mobile devices/simulators** configured and accessible

### Setting up Appium Server

```bash
# Install Appium globally
npm install -g appium

# Install drivers for your platforms
appium driver install xcuitest     # for iOS
appium driver install uiautomator2 # for Android

# Start Appium server
appium server --port 4723
```

## Installation & Usage

### Option 1: Using npx

Add this configuration to your Claude Desktop config file:

```json
{
  "mcpServers": {
    "appium-mcp-server": {
      "command": "npx",
      "args": ["-y", "appium-mcp-server@latest"]
    }
  }
}
```
Requirements
Node.js >= 18 installed globally
npx available in PATH


---

### 🔹 2. ⚠️ Important note (THIS IS KEY)

```md
> ⚠️ Note:
> If you are using Node via NVM, Claude Desktop may not detect it automatically.
> In that case, use Option 2 below.

### Option 2: NVM Users (Recommended if Option 1 fails)

```json
{
  "mcpServers": {
    "appium-mcp-server": {
      "command": "bash",
      "args": [
        "-lc",
        "export NVM_DIR=\"$HOME/.nvm\" && source \"$NVM_DIR/nvm.sh\" && npx -y appium-mcp-server@latest"
      ]
    }
  }
}
```

### Option 3: NVM Users (Recommended if Option 2 fails)

```json
{
  "mcpServers": {
    "appium-mcp-server": {
      "command": "bash",
      "args": [
        "-lc",
        "export NVM_DIR=\"$HOME/.nvm\" && [ -s \"/opt/homebrew/opt/nvm/nvm.sh\" ] && . \"/opt/homebrew/opt/nvm/nvm.sh\" && nvm use 20 >/dev/null && npx -y appium-mcp-server@latest"
      ]
    }
  }
}
```

---

### 🔹 4. 💪 Advanced / stable (BEST for reliability)

```md
### Option 3: Use Node directly (Most reliable)

```json
{
  "mcpServers": {
    "appium-mcp-server": {
      "command": "/path/to/your/node",
      "args": [
        "/path/to/appium-mcp-server/bin/appium-mcp-server.js"
      ]
    }
  }
}
```
To find your Node path:
which node


---

## 🧠 Why this is the BEST approach

You cover:

| User type | Works? |
|----------|--------|
| Beginner | ✅ npx |
| NVM user | ✅ bash fix |
| Power user | ✅ direct node |

---

### Option 4: VS Code Local Setup (Github Copilot / Cursor)

If you want to use `appium-mcp-server` with **GitHub Copilot or Cursor inside your existing VS Code project**, follow these steps:

At the **root of your existing project**, create a `.vscode` folder (if it doesn't exist) and inside it create a file named `mcp.json`:
```
your-existing-project/
└── .vscode/
    └── mcp.json
```

Paste the following into `mcp.json`:
```jsonc
{
  "servers": {
    "appium-mcp-prod": {
      "command": "/Users/username/appium-mcp-server/.venv/bin/python",
      "args": ["src/mcp_server.py"],
      "cwd": "~/appium-mcp-server",
      "env": {
        "APPIUM_PORT": "4723"
      }
    }
  }
}
```

> ⚠️ Replace `/Users/username/` with the actual path where you cloned `appium-mcp-server`.  
> Run `pwd` inside the cloned folder to get the exact path.

---


### ⚙️ Local System Setup Instructions for Apple M1/M2 and Windows

#### 🍎 Apple Silicon (M1/M2) – macOS

Apple Silicon users **must rebuild the Python virtual environment** (`.venv`) locally to avoid architecture compatibility errors like:

ImportError: ... incompatible architecture (have 'x86_64', need 'arm64')

✅ **Steps for M1/M2 Macs**:

- 🧬 Clone the project
- 📂 Open Terminal
- Navigate to your project repository
- 🛠️ Run: `chmod +x bootstrap.sh`
- 🛠️ Run: `./bootstrap.sh`
  - 🧹 Removes the prebuilt `.venv`
  - 🧱 Recreates `.venv` using native `arm64` Python
  - 📦 Reinstalls all Python dependencies
- 🔁 You only need to do this once, unless `.venv` is deleted or `requirements.txt` changes

---

#### 💻 Windows Users

Windows users can use the bundled `.venv` **if compatible**, or regenerate it locally.

✅ **Steps for Windows**:

- 🧬 Clone the project
- 📂 Open Command Prompt or PowerShell
- 📁 Navigate to your project folder (e.g. `cd C:\Users\YourName\appium-mcp-server`)
- 🛠️ Run: `bootstrap.bat`
  - 🧱 Creates a fresh `.venv` using your system’s Python (≥ 3.10)
  - 📦 Installs all dependencies from `requirements.txt`
- 🛑 Make sure Python is in your `PATH` and is version **≥ 3.10**

---

#### 🧪 Verify It Works

### 🧪 Starting the Server

After running the appropriate setup script (`./bootstrap.sh` on macOS or `bootstrap.bat` on Windows), start the MCP server using either of the following:

```bash
npx appium-mcp-server

Or run it directly from project path:

node bin/appium-mcp-server.js

You should see output like:
🚀 Starting MCP server using python3.12
🔧 Injecting PYTHONPATH = ...

### 🧪 Using Claude Desktop with a Local Project

To run your **local version** of the MCP server with Claude Desktop, follow these steps:

1. Open **Claude Desktop**
2. Go to **Settings → Developer → EditConfig button
3. This will open the `desktip-claude-config.json` file
4. Add the following configuration under `"mcpServers"`:

---

#### 🍎 macOS (Intel or Apple Silicon)

```json
{
  "mcpServers": {
    "local-appium-mcp": {
      "command": "node",
      "args": ["/Users/your.name/appium-mcp-server/bin/appium-mcp-server.js"]
    }
  }
}

💻 Windows
{
  "mcpServers": {
    "local-appium-mcp": {
      "command": "node",
      "args": ["C:\\Users\\your.name\\appium-mcp-server\\bin\\appium-mcp-server.js"]
    }
  }
}

📝 Replace /Users/your.name/... with the full path to your cloned project directory.


## Available Tools

### Session Management

- **`appium_start_session`**: Start an Appium session
  - `platform`: "iOS" or "Android"
  - `device_name`: Device name or UDID
  - `app_path`: Path to app file (optional)
  - `bundle_id`: iOS bundle ID (optional)
  - `app_package`: Android package name (optional)
  - `app_activity`: Android activity (optional)

- **`appium_get_session_info`**: Get current session information
- **`appium_quit_session`**: Terminate the current session

### Element Interaction

- **`appium_find_element`**: Find elements on screen
  - `strategy`: "id", "xpath", "class_name", or "accessibility_id"
  - `value`: Locator value

- **`appium_tap_element`**: Tap on an element
  - `element_id`: ID of previously found element

- **`appium_input_text`**: Send text to input fields
  - `element_id`: Target element ID
  - `text`: Text to input

### Page Navigation

- **`appium_get_page_source`**: Get current page source
- **`appium_scroll`**: Scroll the screen
  - `direction`: "up" or "down"

## Example Usage with Claude

```
Start an iOS session on iPhone 15 Pro Max simulator, then navigate to the SauceDemo website and automate the login process.
```

Claude will use the MCP server to:
1. Start an Appium session
2. Find login elements
3. Input credentials
4. Navigate through the app

## Configuration Examples

### iOS Safari Browser Testing
```json
{
  "platform": "iOS",
  "device_name": "iPhone 15 Pro Max"
}
```

### Android Chrome Browser Testing
```json
{
  "platform": "Android", 
  "device_name": "Android Emulator"
}
```

### iOS Native App Testing
```json
{
  "platform": "iOS",
  "device_name": "iPhone 15 Pro Max",
  "bundle_id": "com.example.myapp"
}
```

### Android Native App Testing
```json
{
  "platform": "Android",
  "device_name": "Android Emulator",
  "app_package": "com.example.myapp",
  "app_activity": ".MainActivity"
}
```
## 🚀 Quick Start with Gemini CLI

The easiest way to run mobile automation commands is using our simple CLI wrapper with Gemini.

### Setup Instructions
- 🧬 Clone the project
- 📂 Open Terminal
- Navigate to your project repository
- Also make sure you have created .env file in your project root and entered GEMINI_API_KEY key there

# Load environment variables from .env
load_dotenv()

# Get the API key
api_key = os.getenv("GEMINI_API_KEY")

1. **Make the setup script executable:**
   ```bash
   chmod +x mobile-setup.sh
   ```

2. **Load the mobile function:**
   ```bash
   source mobile-setup.sh
   ```
   
   You should see:
   ```
   Mobile automation function loaded!
   Usage: mobile "Launch Settings on iPhone"
          mobile -i
          mobile --claude "Open Instagram"
   
   To make this permanent, add this to your ~/.bashrc or ~/.zshrc:
   source "/path/to/your/mobile-setup.sh"
   ```

3. **Test the function:**
   ```bash
   # Test help
   mobile -h
   
   # Test interactive mode
   mobile -i
   
   # Test single command
   mobile "Launch Settings on iPhone"
   
   # Test with Claude
   mobile --claude "Open Instagram and scroll down"
   ```

### Make it Permanent (Optional)

To have the `mobile` function available every time you open a terminal:

**For Bash users:**
```bash
echo "source $(pwd)/mobile-setup.sh" >> ~/.bashrc
```

**For Zsh users:**
```bash
echo "source $(pwd)/mobile-setup.sh" >> ~/.zshrc
```

**For Fish shell users:**
```bash
mkdir -p ~/.config/fish/functions
# Then manually create the fish function file
```

### Usage Examples

```bash
# Single prompts (default Gemini)
mobile "Launch Settings on iPhone 15 Pro Max"
mobile "Open Instagram and like the first post"
mobile "Calculate 15 + 25 in Calculator app"
mobile "Launch Safari and go to google.com"

# Single prompts with Claude
mobile --claude "Open Notes and create a new note"
mobile --claude "Launch Camera and take a photo"

# Interactive modes
mobile -i                    # Interactive with Gemini
mobile --claude -i           # Interactive with Claude
mobile --interactive         # Interactive with Gemini

# Help
mobile -h
mobile --help
```

For Windows:

Run the setup script:
cmdmobile-setup.bat
You should see:
Mobile automation command created!

Usage: mobile "Launch Settings on iPhone"
       mobile -i
       mobile --claude "Open Instagram"

The 'mobile' command is now available for this session.
You should see:
Mobile automation function loaded!
Usage: mobile "Launch Settings on iPhone"
       mobile -i
       mobile --claude "Open Instagram"

To make this permanent, add this to your ~/.bashrc or ~/.zshrc:
source "/path/to/your/mobile-setup.sh"

Test the function:
bash# Test help
mobile -h

# Test interactive mode
mobile -i

# Test single command
mobile "Launch Settings on iPhone"

# Test with Claude
mobile --claude "Open Instagram and scroll down"

Make it Permanent (Optional)
For Windows:
Command Prompt:

Add the script directory to your system PATH, or
Run mobile-setup.bat each time you open a new command prompt

Usage Examples
bash# Single prompts (default Gemini)
mobile "Launch Settings on iPhone 15 Pro Max"
mobile "Open Instagram and like the first post"
mobile "Calculate 15 + 25 in Calculator app"
mobile "Launch Safari and go to google.com"

# Single prompts with Claude
mobile --claude "Open Notes and create a new note"
mobile --claude "Launch Camera and take a photo"

# Interactive modes
mobile -i                    # Interactive with Gemini
mobile --claude -i           # Interactive with Claude
mobile --interactive         # Interactive with Gemini

# Help
mobile -h
mobile --help

### Benefits

✅ **No PATH modifications needed**  
✅ **Self-contained in your project directory**  
✅ **Works from any directory once loaded**  
✅ **Easy to modify and customize**  
✅ **No external files created**  
✅ **Portable - just copy the script**

### Quick Workflow

1. **One-time setup:**
   ```bash
   chmod +x mobile-setup.sh
   source mobile-setup.sh
   ```

2. **Daily usage:**
   ```bash
   mobile "Launch Settings"
   mobile "Open Instagram"
   mobile -i  # for interactive mode
   ```

3. **For permanent access** (optional):
   ```bash
   echo "source $(pwd)/mobile-setup.sh" >> ~/.bashrc
   # Then restart terminal or run: source ~/.bashrc
   ```

---

## Troubleshooting

### Common Issues

1. **"No active session" errors**
   - Ensure Appium server is running on localhost:4723
   - Check device/simulator availability
   - Verify platform-specific setup (Xcode for iOS, Android SDK for Android)

2. **Element not found errors**
   - Use `appium_get_page_source` to inspect available elements
   - Try different locator strategies (id, xpath, accessibility_id)
   - Ensure proper timing - elements may need time to load

3. **Python environment issues**
   - The package automatically creates a virtual environment
   - If issues persist, check Python 3.8+ installation
   - Verify internet connectivity for dependency installation

### Debug Mode

Set `DEBUG=1` environment variable for verbose logging:

```bash
DEBUG=1 npx appium-mcp-server
```

## Development

To modify or contribute to this package:

```bash
git clone https://github.com/yourusername/appium-mcp-server.git
cd appium-mcp-server
npm install
npm link  # for local testing
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions welcome! Please read the contributing guidelines and submit pull requests to the main repository.
