#!/usr/bin/env python3
# run_agent.py - Generic Mobile Automation Agent for Any App
# Works with your existing MCP server and appium_controller

import argparse
import asyncio
import json
import re
import subprocess
import threading
import time
import sys

from llm_clients.gemini_client import run_prompt as run_with_gemini
from llm_clients.claude_client import run_prompt as run_with_claude

# Import the Enhanced MCP Client
from enhanced_mcp_client import EnhancedMCPClient

# Start the MCP server subprocess (your existing server)
mcp_proc = subprocess.Popen(
    ["python", "src/mcp_server.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1
)

# Log MCP server stderr asynchronously
def log_stderr(stream):
    for line in stream:
        if line.strip():
            print("🔴 MCP Server STDERR:", line.strip())

threading.Thread(target=log_stderr, args=(mcp_proc.stderr,), daemon=True).start()

# Give server time to start
time.sleep(2)

# Parse CLI arguments
parser = argparse.ArgumentParser(description="Generic Mobile Automation Agent - Works with Any App")
mode_group = parser.add_mutually_exclusive_group(required=True)
parser.add_argument("--model", choices=["gemini", "claude"], required=True, help="LLM model to use")
mode_group.add_argument("--prompt", help="Natural language automation instructions")
mode_group.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode")
parser.add_argument("--debug", action="store_true", help="Enable debug mode with screenshots")
parser.add_argument("--platform", choices=["iOS", "Android"], help="Override platform detection")
parser.add_argument("--device", help="Override device name")

args = parser.parse_args()

# Generic tool instruction template - works for any app
instruction = """You are a universal mobile automation assistant that can interact with ANY mobile app using Appium and GENERATE COMPLETE APPIUM JAVA PROJECTS with Maven + TestNG

IMPORTANT PROJECT CONTEXT RULES:
1. When user asks to "write files created above" or "update the files" or similar, they want to MODIFY the LAST created project
2. For write_files_batch operations, use the SAME project structure as the most recently created project
3. DO NOT create new projects when asked to write/update existing files
4. Always use relative paths within the existing project structure

WORKFLOW DECISION LOGIC:
- NEW PROJECT: "create project", "generate project", "new framework" → use create_project tool
- UPDATE EXISTING: "write files above", "update files", "modify the project", "write all files" → use write_files_batch with existing project paths

IMPORTANT GUIDELINES:
1. Always start by launching the requested app
2. Inspect the page to see what elements are available before trying to interact
3. Use descriptive names when looking for elements
4. Be flexible with element names - they might not match exactly
5. Handle both iOS and Android apps automatically
6. For Safari browser automation, you can use start_url parameter to directly open websites
7. FOR PROJECT GENERATION: You CAN and MUST create Java projects when requested
8. FOR FILE UPDATES: Use write_files_batch with paths relative to the existing project

SUPPORTED PLATFORMS: iOS, Android
SUPPORTED APPS: Any mobile app (built-in apps, third-party apps, games, web browsers, etc.)

Available tools:
- appium_start_session: Start session for any app
- extract_selectors_from_page_source: Inspect available elements (ALWAYS use this after starting session)
- appium_find_element: Find elements using multiple strategies
- appium_tap_element: Tap on elements
- appium_get_text: Get text from elements
- appium_input_text: Type text into elements
- appium_scroll: Scroll the screen
- appium_take_screenshot: Take screenshots
- appium_get_page_source: Get the full page XML
- appium_quit_session: Quit/close/end/stop/terminate the current Appium session (use ONLY this tool name)
- create_project: Create complete Appium Java project with Maven + TestNG structure
- write_files_batch: Write multiple files at once (prefer this for bulk operations)  
- write_file: Write single file (fallback only)

SESSION PARAMETERS:
For iOS apps, use these patterns:
- Built-in apps: Use app name (e.g., "Settings", "Safari", "Notes", "Photos", "Calculator")
- Third-party apps: Use bundle ID (e.g., "com.spotify.client", "com.facebook.Facebook")
- Safari with URL: Use app name "Safari" and add start_url parameter

For Android apps, use these patterns:
- Built-in apps: Use app name (e.g., "Settings", "Chrome", "Contacts")
- Third-party apps: Use package name (e.g., "com.spotify.music", "com.facebook.katana")

SAFARI AUTOMATION:
When user wants to open Safari with a specific URL, use start_url parameter:
```json
{
  "tool": "appium_start_session",
  "args": {
    "platform": "iOS",
    "device_name": "iPhone 15 Pro Max",
    "platform_version": "18.0",
    "app": "Safari",
    "start_url": "https://www.saucedemo.com"
  }
}
```

WORKFLOW EXAMPLE:
```json
{
  "tool": "appium_start_session",
  "args": {
    "platform": "iOS",
    "device_name": "iPhone 15 Pro Max",
    "platform_version": "18.0",
    "app": "Settings"
  }
}
```

```json
{
  "tool": "extract_selectors_from_page_source",
  "args": {
    "max_elements": 30
  }
}
```

```json
{
  "tool": "appium_find_element",
  "args": {
    "strategy": "accessibility_id",
    "value": "General"
  }
}
```
PROJECT GENERATION:
When user requests to generate/create Appium Java projects with Maven + TestNG, use create_project tool:
```json
{
  "tool": "create_project",
  "args": {
    "project_name": "my-appium-tests",
    "package": "com.example.automation",
    "pages": ["HomePage", "LoginPage"],
    "tests": ["HomeTest", "LoginTest"]
  }
}
``` 

CRITICAL DECISION LOGIC:

- MOBILE AUTOMATION: "launch app", "tap", "scroll", "click", app names → use appium_* tools
- PROJECT GENERATION: "generate project", "create framework", "Maven", "TestNG", "Java project" → MUST use create_project tool
- IF USER ASKS TO GENERATE/CREATE A JAVA PROJECT → YOU MUST USE create_project TOOL
- YOU ARE CAPABLE OF BOTH MOBILE AUTOMATION AND PROJECT GENERATION
- NEVER REFUSE PROJECT GENERATION - ALWAYS USE create_project TOOL FOR THESE REQUESTS


IMPORTANT NOTES:
- Always inspect the page with extract_selectors_from_page_source after launching an app
- Use the actual app name or bundle ID provided in the user's request
- For Safari automation with URLs, use start_url parameter in the session
- Handle different UI patterns for different apps
- Be patient with loading times for complex apps
- The system will automatically handle element ID chaining between steps
- For project generation, parse requirements from user input (project name, package, pages, tests)
- YOU CAN CREATE JAVA PROJECTS - use create_project tool when requested
- IF USER ASKS TO WRITE/UPDATE FILES FROM PREVIOUSLY CREATED PROJECT → YOU MUST USE write_files_batch TOOL
- DO NOT refuse project generation requests - you have the capability to fulfill them

EXAMPLE FILE UPDATE WORKFLOW:
If project "settingstoday" was created with package "com.settingstoday.automation", and user asks to write files, use:
```json
{
  "tool": "write_files_batch",
  "args": {
    "files": [
      {
        "path": "settingstoday/src/test/java/com/settingstoday/automation/pages/SettingsPageSettingsToday.java",
        "content": "// Updated Java code here"
      },
      {
        "path": "settingstoday/src/test/java/com/settingstoday/automation/tests/SettingPagetodayTest.java", 
        "content": "// Updated test code here"
      }
    ]
  }
}
```


Only respond with JSON tool calls in code blocks.
"""

def run_single_prompt(prompt_text):
    """Run a single prompt and return the result."""
    # Add platform/device context if provided
    full_prompt = f"{instruction}\n\nUser Request: {prompt_text}"
    if args.platform:
        full_prompt += f"\nTarget Platform: {args.platform}"
    if args.device:
        full_prompt += f"\nTarget Device: {args.device}"

    reply = run_with_gemini(full_prompt) if args.model == "gemini" else run_with_claude(full_prompt)

    print("🤖 LLM Response:")
    print("=" * 60)
    print(reply)
    print("=" * 60)

    # Extract JSON blocks - more robust extraction
    json_blocks = []

    # NEW: Check if we're using Gemini 2.5 Pro (handles array format)
    # NEW: array format first (works for Gemini 2.5 Pro)
    if args.model == "gemini":
        # Try Gemini 2.5 Pro array format first
        json_blocks = extract_array_format(reply)
        if json_blocks:
            print(f"\n📋 Found {len(json_blocks)} tool calls (Gemini array format)")
            return json_blocks
    
    # Try multiple extraction patterns - FIXED ORDER for Safari URLs
    patterns = [
        r"```(?:json)?\s*(\{[\s\S]*?\})\s*```",              # Original pattern - GOOD FOR URLS
        r"```(?:json)?\s*(\{(?:[^{}]|{[^{}]*})*\})\s*```",  # Nested braces - backup
        r"```\s*(\{[\s\S]*?\})\s*```",                       # Without json marker
    ]
    
    for pattern in patterns:
        blocks = re.findall(pattern, reply, re.DOTALL)
        if blocks:
            json_blocks = blocks
            break
    
    # If still no blocks found, try manual extraction
    if not json_blocks:
        lines = reply.split('\n')
        in_json_block = False
        current_block = []
        
        for line in lines:
            if line.strip().startswith('```'):
                if in_json_block and current_block:
                    # End of block
                    json_str = '\n'.join(current_block)
                    if json_str.strip().startswith('{') and json_str.strip().endswith('}'):
                        json_blocks.append(json_str)
                    current_block = []
                    in_json_block = False
                else:
                    # Start of block
                    in_json_block = True
            elif in_json_block:
                current_block.append(line)

    if not json_blocks:
        print("\n❌ No valid JSON tool call found in the LLM response.")
        return False

    print(f"\n📋 Found {len(json_blocks)} tool calls to execute")
    return json_blocks

def interactive_mode():
    """Run in interactive mode for multiple commands."""
    print(f"🚀 Interactive Mobile Automation Assistant (Model: {args.model})")
    print("Available commands:")
    print("  - Any mobile automation task (e.g., 'Launch Instagram and like the first post')")
    print("  - 'screenshot' - Take a screenshot")
    print("  - 'quit session' - End current app session")
    print("  - 'help' - Show this help")
    print("  - 'exit' or 'quit' - Exit interactive mode")
    print("")

    # ADD THIS: Session tracking
    session_active = False
    
    while True:
        try:
            prompt = input("💬 Enter command: ").strip()
            
            if prompt.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            elif prompt.lower() == 'help':
                print("""
Available commands:
- Launch [app] on [device] (e.g., "Launch Settings on iPhone 15 Pro Max")
- Navigate to [section] (e.g., "Go to General settings")
- Tap on [element] (e.g., "Tap on the login button")
- Type [text] in [field] (e.g., "Type 'hello' in the search box")
- Scroll [direction] (e.g., "Scroll down")
- Take screenshot
- Get text from [element]
- Check if [element] contains [text]
- quit session - End current app session
- exit/quit - Exit interactive mode

Examples:
- "Launch Instagram and scroll through the feed"
- "Open Calculator and calculate 15 + 25"
- "Launch Safari and go to google.com"
- "Open Settings, go to General, then About"
                """)
                continue
            elif not prompt:
                continue
            elif prompt.lower() == 'screenshot':
                # Quick screenshot command
                json_blocks = [{"tool": "appium_take_screenshot", "args": {}}]
            elif prompt.lower() == 'quit session':
                # Quick quit session command
                json_blocks = [{"tool": "appium_quit_session", "args": {}}]
            elif "launch" in prompt.lower() and session_active:
                print("⚠️ A session is already active. Do you want to:")
                print("  1. Quit current session and launch new app")
                print("  2. Continue with current session")
                choice = input("Enter choice (1/2): ").strip()
                if choice == "1":
                    # Auto-quit current session first
                    print("🔄 Ending current session...")
                    quit_blocks = [{"tool": "appium_quit_session", "args": {}}]
                    try:
                        asyncio.run(execute_tool_calls(quit_blocks))
                        session_active = False
                        print("✅ Previous session ended")
                    except Exception as e:
                        print(f"❌ Error ending session: {e}")
                            # ADD THIS: Use same smart context logic
                    if session_active and not "launch" in prompt.lower():
                        enhanced_prompt = f"Continue in current app session. Task: {prompt}"
                    else:
                        enhanced_prompt = prompt
                    
                    # Now process the launch command normally
                    json_blocks = run_single_prompt(enhanced_prompt)
                    if not json_blocks:
                        continue
                else:
                    print("❌ Command cancelled. Continuing with current session.")
                    continue
            else:
                # Process normal automation command
                # MODIFIED: Add smart context for Gemini
                if session_active and not "launch" in prompt.lower():
                    # Tell Gemini we're in an existing session
                    enhanced_prompt = f"Continue in current app session. Task: {prompt}"
                else:
                    enhanced_prompt = prompt
                
                json_blocks = run_single_prompt(enhanced_prompt)
                if not json_blocks:
                    continue
            
            # Execute the commands
            try:
                asyncio.run(execute_tool_calls(json_blocks))
                # ADD THIS: Update session tracking
                if any("appium_start_session" in str(block) for block in json_blocks):
                    session_active = True
                    print("📱 Session started")
                if any("appium_quit_session" in str(block) for block in json_blocks):
                    session_active = False
                    print("📱 Session ended")

            except Exception as e:
                print(f"❌ Error executing commands: {e}")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

def is_new_app_command(prompt):
    """Check if command is trying to start a new app."""
    prompt_lower = prompt.lower()
    
    # Launch keywords - PRIMARY detection method
    launch_keywords = ["launch", "start", "open", "run", "begin", "load"]
    has_launch_keyword = any(keyword in prompt_lower for keyword in launch_keywords)
    
    # Device mentions - indicates new session
    device_keywords = ["iphone", "android", "simulator", "device", "emulator", "pixel", "samsung"]
    has_device = any(device in prompt_lower for device in device_keywords)
    
    # Bundle ID patterns (more reliable than app names)
    has_bundle_id = ("com." in prompt_lower) or ("bundle" in prompt_lower)
    
    # MAIN LOGIC: If has launch keyword OR (device + any app indication)
    return (has_launch_keyword or 
            has_bundle_id or 
            (has_device and ("app" in prompt_lower or "application" in prompt_lower)))

# Generic async tool execution loop
async def execute_tool_calls(json_blocks):
    """Execute tool calls with your existing MCP server."""
    
    try:
        # Create enhanced MCP client
        client = EnhancedMCPClient(mcp_proc)
        
        # Initialize the session
        print("🚀 Initializing mobile automation session...")
        init_result = await client.initialize()
        
        # List available tools for debugging
        if args.debug:
            print("🔧 Listing available tools...")
            tools_result = await client.list_tools()
            print(f"📋 Available tools: {[tool.get('name', 'unnamed') for tool in tools_result.get('tools', [])]}")
        
        # Execute each tool call with generic handling
        for i, block in enumerate(json_blocks):
            print(f"\n📦 Tool Call {i+1}/{len(json_blocks)}:")
            try:
                if isinstance(block, str):
                    # DON'T remove // comments as they break URLs
                    # Only remove control characters that break JSON parsing
                    clean_block = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', block)
                    clean_block = clean_block.strip()
                    
                    try:
                        tool_call = json.loads(clean_block)
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON Parse Error: {e}")
                        print(f"🔍 Raw JSON: {repr(clean_block[:200])}...")
                        print("⏭️ Skipping this tool call...")
                        continue
                else:
                    tool_call = block
                    
                tool_name = tool_call.get("tool")
                tool_args = tool_call.get("args", {})

                print(f"🛠️  Tool: {tool_name}")
                print(f"🧩 Args: {json.dumps(tool_args, indent=2)}")

                # ADD THE ALIAS HANDLING HERE - BEFORE the if/elif chain
                if tool_name in ["appium_close_session", "appium_destroy_session", "appium_end_session", "appium_stop_session", "appium_terminate_session"]:
                    tool_name = "appium_quit_session"
                    print(f"🔄 Corrected tool name: appium_close_session → appium_quit_session")

                # Handle different tool types generically
                if tool_name == "appium_start_session":
                    # Use enhanced start session with app normalization
                    result = await client.start_session(tool_args)
                    
                    if result.get('status') == 'success':
                        print("✅ Session started successfully!")
                        if args.debug:
                            await asyncio.sleep(2)  # Wait for app to load
                            await client.take_screenshot("session_start.png")
                    else:
                        print(f"❌ Session failed: {result}")
                        
                elif tool_name == "appium_find_element":
                    strategy = tool_args.get("strategy", "accessibility_id")
                    value = tool_args.get("value") or tool_args.get("selector")
                    description = tool_args.get("description")
                    
                    # Fix strategy mapping - iOS uses different attribute names
                    if strategy == "name":
                        strategy = "accessibility_id"
                        print(f"🔄 Converted 'name' strategy to 'accessibility_id' for iOS")
                    
                    # Use enhanced find element with retries
                    element_id, result = await client.smart_find_element(strategy, value, description)
                    
                    if element_id:
                        print(f"✅ Found element: {element_id}")
                        # Store for potential use in next steps
                        client.element_store[f"step_{i}"] = element_id
                    else:
                        print(f"❌ Element not found: {result}")
                        
                        # Try scrolling to find the element
                        print("🔄 Trying to scroll to find element...")
                        element_id, scroll_result = await client.scroll_to_find_element(strategy, value)
                        
                        if element_id:
                            print(f"✅ Found element after scrolling: {element_id}")
                            client.element_store[f"step_{i}"] = element_id
                        else:
                            print(f"❌ Element not found even after scrolling: {scroll_result}")
                        
                elif tool_name == "appium_tap_element":
                    element_id = tool_args.get("element_id")
                    # FIXED: Handle Gemini's generic element ID references
                    # ADDITIONAL: Handle common Gemini patterns at the execution level too
                    print(f"🔍 Tap request - Original element_id: '{element_id}'")
                    gemini_patterns = [
                        "element_id_from_previous_step", 
                        "previous_element_id", 
                        "found_element_id",
                        "current_element_id",
                        "last_element_id",
                        "element_from_previous_step",
                        "previous_element"
                        ]
                    if element_id in gemini_patterns:
                        print(f"🔄 Gemini used generic element ID '{element_id}', using last found element: {client.last_element_id}")
                        element_id = client.last_element_id

                     # STEP 2: Simple validation - ignore obviously fake element IDs  
                    elif element_id and not element_id.startswith(":"):
                        print(f"🔄 Invalid element_id format '{element_id}' (real IDs start with ':'), using last found: {client.last_element_id}")
                        element_id = client.last_element_id
                    
                    # Enhanced tap with automatic element resolution
                    result = await client.smart_tap_element(element_id)
                    
                    if result.get('status') == 'success':
                        print("✅ Tap successful!")
                        if args.debug:
                            await asyncio.sleep(1)  # Wait for UI to respond
                            await client.take_screenshot(f"after_tap_{i}.png")
                    else:
                        print(f"❌ Tap failed: {result}")
                        
                elif tool_name == "appium_get_text":
                    element_id = tool_args.get("element_id")

                    # ENHANCED: Debug logging for element ID
                    print(f"🔍 Get text request - Original element_id: '{element_id}'")

                    # ADDITIONAL: Handle common Gemini patterns at the execution level too
                    gemini_patterns = [
                        "element_id_from_previous_step", 
                        "previous_element_id", 
                        "found_element_id",
                        "current_element_id", 
                        "last_element_id",
                        "element_from_previous_step",
                        "previous_element"
                    ]

                    if element_id in gemini_patterns:
                        print(f"🔄 Detected Gemini generic pattern '{element_id}', using last found: {client.last_element_id}")
                        element_id = client.last_element_id
                      # STEP 2: Simple validation - ignore obviously fake element IDs
                    elif element_id and not element_id.startswith(":"):
                        print(f"🔄 Invalid element_id format '{element_id}' (real IDs start with ':'), using last found: {client.last_element_id}")
                        element_id = client.last_element_id
                    
                    # Enhanced get text with automatic element resolution
                    result = await client.smart_get_text(element_id)
                    
                    if result.get('status') == 'success':
                        text = result.get('text', '')
                        print(f"✅ Got text: '{text}'")
                        
                        # Generic text validation - works for any app
                        if any(keyword in text.lower() for keyword in ['iphone', 'android', 'device', 'name']):
                            print(f"📱 Device/name check: '{text}' - Found device-related text")
                    else:
                        print(f"❌ Get text failed: {result}")
                        
                elif tool_name == "appium_input_text":
                    text = tool_args.get("text")
                    element_id = tool_args.get("element_id")
                    print(f"🔍 Input text request - Original element_id: '{element_id}', text: '{text}'")
                    gemini_patterns = [
                        "element_id_from_previous_step", 
                        "previous_element_id", 
                        "found_element_id",
                        "current_element_id",
                        "last_element_id",
                        "element_from_previous_step",
                        "previous_element"
                    ]

                    # FIXED: Handle Gemini's generic element ID references
                    if element_id in gemini_patterns:
                        print(f"🔄 Gemini used generic element ID '{element_id}', using last found element: {client.last_element_id}")
                        element_id = client.last_element_id

                    # STEP 2: Simple validation - ignore obviously fake element IDs
                    elif element_id and not element_id.startswith(":"):
                        print(f"🔄 Invalid element_id format '{element_id}' (real IDs start with ':'), using last found: {client.last_element_id}")
                        element_id = client.last_element_id
                    
                    # Enhanced input text with automatic element resolution
                    result = await client.smart_input_text(text, element_id)
                    
                    if result.get('status') == 'success':
                        print(f"✅ Input successful: '{text}'")
                    else:
                        print(f"❌ Input failed: {result}")
                        
                elif tool_name == "extract_selectors_from_page_source":
                    max_elements = tool_args.get("max_elements", 25)
                    
                    # Use enhanced XML parser for better results
                    print("🔍 Using enhanced XML parser...")
                    parsed_result = await client.enhanced_extract_selectors(max_elements)
                    
                    if parsed_result.get('status') == 'success':
                        elements = parsed_result.get('elements', [])
                        print(f"✅ Enhanced parser found {len(elements)} elements on page:")
                        for j, element in enumerate(elements[:15]):  # Show first 15
                            text = element.get('text', '')
                            acc_id = element.get('accessibility_id', '')
                            elem_id = element.get('id', '')
                            tag = element.get('tag', 'Unknown')
                            clickable = element.get('clickable', False)
                            
                            # Format display based on what's available
                            display_text = text or acc_id or elem_id or 'No identifier'
                            click_indicator = " [CLICKABLE]" if clickable else ""
                            print(f"  {j+1:2d}. {tag}: '{display_text}'{click_indicator}")
                            
                        if len(elements) > 15:
                            print(f"  ... and {len(elements) - 15} more elements")
                            
                        # Look for specific elements that might be relevant
                        if any('general' in str(elem.get('text', '')).lower() or 
                               'general' in str(elem.get('accessibility_id', '')).lower() 
                               for elem in elements):
                            print("🎯 Found 'General' element in the list!")
                            
                    else:
                        print(f"❌ Enhanced parser failed: {parsed_result}")
                        # Fallback to server's method
                        print("🔄 Falling back to server's extract_selectors_from_page_source...")
                        result = await client.call_tool(tool_name, tool_args)
                        parsed_result = client.parse_tool_result(result)
                        
                        if parsed_result.get('status') == 'success':
                            elements = parsed_result.get('elements', []) or parsed_result.get('selectors', [])
                            print(f"✅ Server parser found {len(elements)} elements")
                        else:
                            print(f"❌ Both parsers failed: {parsed_result}")
                        
                elif tool_name == "appium_take_screenshot":
                    filename = tool_args.get("filename")
                    result = await client.take_screenshot(filename)
                    
                    if result.get('status') == 'success':
                        saved_path = result.get('path', result.get('filename', 'screenshot.png'))
                        print(f"✅ Screenshot saved: {saved_path}")
                    else:
                        print(f"❌ Screenshot failed: {result}")
                        
                elif tool_name == "appium_scroll":
                    direction = tool_args.get("direction", "down")
                    result = await client.call_tool(tool_name, tool_args)
                    parsed_result = client.parse_tool_result(result)
                    
                    if parsed_result.get('status') == 'success':
                        print(f"✅ Scrolled {direction}")
                    else:
                        print(f"❌ Scroll failed: {parsed_result}")
                        
                elif tool_name == "appium_get_page_source":
                    full = tool_args.get("full", False)
                    result = await client.get_page_source(full)
                    
                    if result.get('status') == 'success':
                        source_length = len(result.get('page_source', ''))
                        print(f"✅ Got page source ({source_length} characters)")
                        if args.debug:
                            # Save page source to file for debugging
                            with open(f"page_source_{i}.xml", 'w') as f:
                                f.write(result.get('page_source', ''))
                            print(f"📄 Page source saved to page_source_{i}.xml")
                    else:
                        print(f"❌ Get page source failed: {result}")
                        
                elif tool_name == "appium_quit_session":
                    result = await client.quit_session()
                    
                    if result.get('status') == 'success':
                        print("✅ Session ended successfully")
                    else:
                        print(f"❌ Failed to quit session: {result}")
                elif tool_name == "create_project":
                    # Handle project creation
                    project_name = tool_args.get("project_name")
                    package = tool_args.get("package")
                    pages = tool_args.get("pages", [])
                    tests = tool_args.get("tests", [])
    
                    print(f"🚀 Creating Appium project: {project_name}")
                    result = await client.create_project(project_name, package, pages, tests)
    
                    if result.get('status') == 'success':
                        print(f"✅ Project created successfully!")
                        print(f"📁 Location: {result.get('project_path')}")
                        print(f"📦 Package: {result.get('package')}")
                        print(f"📄 Pages: {', '.join(result.get('pages', []))}")
                        print(f"🧪 Tests: {', '.join(result.get('tests', []))}")
                        print(f"📋 Files created: {result.get('files_created')}")
                    else:
                        print(f"❌ Project creation failed: {result}")

                elif tool_name == "write_files_batch":
                    # Handle batch file writing
                    files = tool_args.get("files", [])
                    print(f"📝 Writing {len(files)} files...")
                    result = await client.write_files_batch(files)
                    if result.get('status') == 'success':
                        print(f"✅ Files written successfully: {result.get('message')}")
                    else:
                        print(f"❌ Batch file writing failed: {result}")

                elif tool_name == "write_file":
                    # Handle single file writing
                    path = tool_args.get("path") or tool_args.get("file_path")
                    content = tool_args.get("content")
                    if not path:  # ← Add this validation
                        print("❌ No path provided for write_file")
                        continue
    
                    print(f"📝 Writing file: {path}")
                    result = await client.write_file(path, content)
    
                    if result.get('status') == 'success':
                        print(f"✅ File written successfully: {result.get('message')}")
                    else:
                        print(f"❌ File writing failed: {result}")
                
                elif tool_name == "create_project":
                    # Handle project creation
                    project_name = tool_args.get("project_name")
                    package = tool_args.get("package")
                    pages = tool_args.get("pages", [])
                    tests = tool_args.get("tests", [])
    
                    if not project_name:  # ← Add validation
                        print("❌ No project_name provided for create_project")
                        continue
    
                    print(f"🚀 Creating Appium project: {project_name}")
                    result = await client.create_project(project_name, package, pages, tests)
    
                    if result.get('status') == 'success':
                        print(f"✅ Project created successfully!")
                        print(f"📁 Location: {result.get('project_path')}")
                        print(f"📦 Package: {result.get('package')}")
                        print(f"📄 Pages: {', '.join(result.get('pages', []))}")
                        print(f"🧪 Tests: {', '.join(result.get('tests', []))}")
                        print(f"📋 Files created: {result.get('files_created')}")
                    else:
                         print(f"❌ Project creation failed: {result}")

                elif tool_name == "generate_complete_appium_project":
                    # Handle high-level project generation
                    project_name = tool_args.get("project_name")
                    package = tool_args.get("package")
                    pages = tool_args.get("pages", [])
                    tests = tool_args.get("tests", [])
                    if not project_name:  # ← Add this validation
                        print("❌ No project_name provided for generate_complete_appium_project")
                        continue
    
                    print(f"🚀 Generating complete Appium project: {project_name}")
                    result = await client.generate_complete_appium_project(project_name, package, pages, tests)
    
                    if result.get('status') == 'success':
                        print(f"✅ Complete project generated successfully!")
                        details = result.get('details', {})
                        print(f"📁 Location: {details.get('project_path')}")
                        print(f"📦 Package: {details.get('package')}")
                        print(f"📄 Pages: {', '.join(details.get('pages', []))}")
                        print(f"🧪 Tests: {', '.join(details.get('tests', []))}")
                        print(f"📋 Files created: {details.get('files_created')}")
                        print(f"🏗️ Structure: {details.get('structure')}")
        
                        # Show features
                        features = details.get('features', [])
                        if features:
                            print("✨ Features included:")
                            for feature in features:
                                print(f"  • {feature}")
                    else:
                        print(f"❌ Project generation failed: {result}")
                elif tool_name in ["sleep", "wait"]:
                    seconds = tool_args.get("seconds", 5)
                    print(f"⏰ Waiting {seconds} seconds for page to load...")
                    await asyncio.sleep(seconds)
                    print(f"✅ Waited {seconds} seconds")
                
                # Handle assertion tools that LLMs sometimes generate
                elif tool_name in ["assert", "assert_value", "assert_equals", "validate", "check"]:
                    actual = tool_args.get("actual_value", tool_args.get("actual", ""))
                    expected = tool_args.get("expected_value", tool_args.get("expected", ""))
                    comparison = tool_args.get("comparison", "equals")
                    message = tool_args.get("message", "")
                    
                    if message:
                        print(f"🔍 Assertion: {message}")
                    
                    # Perform the assertion based on comparison type
                    if comparison in ["equals", "==", "eq"]:
                        if str(actual) == str(expected):
                            print(f"✅ Assertion passed: '{actual}' == '{expected}'")
                        else:
                            print(f"❌ Assertion failed: '{actual}' != '{expected}'")
                    elif comparison in ["contains", "in"]:
                        if str(expected) in str(actual):
                            print(f"✅ Assertion passed: '{actual}' contains '{expected}'")
                        else:
                            print(f"❌ Assertion failed: '{actual}' does not contain '{expected}'")
                    else:
                        print(f"✅ Generic assertion: {tool_name} - {actual} vs {expected}")
                        
                else:
                    # Regular tool call for any other tools our server supports
                    result = await client.call_tool(tool_name, tool_args)
                    parsed_result = client.parse_tool_result(result)
                    
                    if parsed_result.get('status') == 'success':
                        print(f"✅ Tool '{tool_name}' executed successfully")
                    else:
                        print(f"❌ Tool '{tool_name}' failed: {parsed_result}")
                        # For unknown tools, just continue instead of stopping
                        print(f"⏭️ Continuing with next tool...")

                # Add delay between actions for stability
                await asyncio.sleep(1.5)

            except Exception as e:
                print(f"❌ Error during tool execution: {e}")
                import traceback
                traceback.print_exc()
                
                # Continue with next tool call instead of stopping
                continue
                
    except Exception as e:
        print(f"❌ Error in tool execution: {e}")
        import traceback
        traceback.print_exc()

# NEW FUNCTION: Handle Gemini 2.0.5 Pro array format
def extract_array_format(response_text):
    """Extract JSON array format from Gemini 2.5 Pro responses."""
    json_blocks = []
    
    # Multiple patterns to try
    patterns = [
        r'```json\s*(\[[\s\S]*?\])\s*```',           # Your original
        r'```JSON\s*(\[[\s\S]*?\])\s*```',           # Uppercase
        r'```\s*json\s*(\[[\s\S]*?\])\s*```',        # Extra spaces
        r'```\s*(\[[\s\S]*?\])\s*```',               # No json marker
        r'```[^\n]*\n(\[[\s\S]*?\])\s*```',          # Any text after ```
    ]
    
    for i, pattern in enumerate(patterns):
        matches = re.findall(pattern, response_text, re.DOTALL)
        if matches:
            print(f"✅ Pattern {i+1} found {len(matches)} matches")
            for match in matches:
                try:
                    parsed_array = json.loads(match.strip())
                    if isinstance(parsed_array, list):
                        for item in parsed_array:
                            if isinstance(item, dict):
                                json_blocks.append(json.dumps(item))
                except json.JSONDecodeError:
                    continue
            return json_blocks
    
    return []

# Main execution logic
def main():
    try:
        if args.interactive:
            interactive_mode()
        else:
            # Single prompt mode
            json_blocks = run_single_prompt(args.prompt)
            if json_blocks:
                print("🚀 Starting mobile automation execution...")
                asyncio.run(execute_tool_calls(json_blocks))
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user")
    except Exception as e:
        print(f"❌ Error in main execution: {e}")
        import traceback
        traceback.print_exc()
    finally:
        mcp_proc.terminate()
        mcp_proc.wait()
        print("🔚 MCP process terminated")

if __name__ == "__main__":
    main()