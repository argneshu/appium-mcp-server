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

- **Python 3.8+** installed on your system
- **Node.js 16+** (for npx usage)
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

### Option 1: Using npx (Recommended)

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
