#!/usr/bin/env python3
"""
Appium MCP Server with proper Options implementation
"""

import asyncio
import json
from typing import Any, Sequence
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import Resource, Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import AnyUrl
import mcp.types as types
from selenium.common.exceptions import StaleElementReferenceException
import time

# Appium imports
from appium import webdriver
from appium.options.ios import XCUITestOptions
from appium.options.android import UiAutomator2Options


# Global session storage
active_session = {
    "driver": None,
    "session_id": None
}

# Global store for WebElements
element_store = {}

def start_session(platform: str, device_name: str, app_path: str = "", bundle_id: str = "", app_package: str = "", app_activity: str = "", start_url: str = "") -> dict:
    print(f"DEBUG: start_session called with platform={platform}, device={device_name}")
    print("🚀 MCP Server: Running from local-mcp-server")

    try:
        if platform.lower() == "ios":
            print("Using XCUITestOptions approach")
            options = XCUITestOptions()
            options.platform_name = "iOS"
            options.device_name = device_name
            options.platform_version = "17.0"
            options.automation_name = "XCUITest"
            if bundle_id:
                options.bundle_id = bundle_id
            elif app_path:
                options.app = app_path
            else:
                options.browser_name = "Safari"
                options.safari_allow_popups = True
                options.safari_ignore_fraud_warning = True

        elif platform.lower() == "android":
            options = UiAutomator2Options()
            options.platform_name = "Android"
            options.device_name = device_name
            options.automation_name = "UiAutomator2"
            options.chromedriver_autodownload = True
            if app_package and app_activity:
                options.app_package = app_package
                options.app_activity = app_activity
            elif app_path:
                options.app = app_path
            else:
                options.browser_name = "Chrome"
        else:
            raise ValueError(f"Unsupported platform: {platform}")

        options.new_command_timeout = 300
        options.no_reset = True

        driver = webdriver.Remote("http://localhost:4723", options=options)
        active_session["driver"] = driver
        active_session["session_id"] = driver.session_id

        if getattr(options, "browser_name", None) and start_url:
            import time
            print(f"DEBUG: Waiting for Safari context before navigating to {start_url}")
            time.sleep(3)  # Allow Safari to launch

            driver.implicitly_wait(10)
            max_wait = 15
            interval = 1
            found_webview = False

            for _ in range(max_wait):
                contexts = driver.contexts
                print(f"DEBUG: Available contexts: {contexts}")
                for ctx in contexts:
                    if "WEBVIEW" in ctx or "Safari" in ctx:
                        print(f"DEBUG: Switching to context: {ctx}")
                        driver.switch_to.context(ctx)
                        found_webview = True
                        break
                if found_webview:
                    break
                time.sleep(interval)

            if found_webview:
                print(f"DEBUG: Navigating to URL: {start_url}")
                driver.get(start_url)
            else:
                print("❌ No webview context found. Cannot navigate to URL.")

        return {
            "status": "success",
            "session_id": driver.session_id,
            "platform": platform,
            "device": device_name,
            "capabilities": options.to_capabilities(),
            "message": f"Started Appium session on {platform} for {device_name}"
        }

    except Exception as e:
        if active_session.get("driver"):
            try:
                active_session["driver"].quit()
            except:
                pass
        active_session["driver"] = None
        active_session["session_id"] = None

        return {
            "status": "error",
            "error_type": type(e).__name__,
            "message": f"Failed to start session: {str(e)}"
        }

    return {
        "status": "error",
        "message": "start_session ended unexpectedly without return"
    }

def find_element(strategy: str, value: str) -> dict:
    """
    Find an element using the specified strategy and store it
    """
    try:
        if not active_session.get("driver"):
            return {
                "status": "error",
                "message": "No active session. Please start a session first."
            }

        driver = active_session["driver"]

        if strategy == "id":
            element = driver.find_element("id", value)
        elif strategy == "xpath":
            element = driver.find_element("xpath", value)
        elif strategy == "class_name":
            element = driver.find_element("class name", value)
        elif strategy == "accessibility_id":
            element = driver.find_element("accessibility id", value)
        else:
            return {
                "status": "error",
                "message": f"Unsupported locator strategy: {strategy}"
            }

        element_store[element.id] = element

        return {
            "status": "success",
            "element_id": element.id,
            "strategy": strategy,
            "value": value,
            "message": f"Found element using {strategy}: {value}"
        }

    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "message": f"Failed to find element: {str(e)}"
        }


def tap_element(element_id: str) -> dict:
    """
    Tap on an element using the element store, with retry for staleness
    """
    try:
        if not active_session.get("driver"):
            return {"status": "error", "message": "No active session. Please start a session first."}

        driver = active_session["driver"]
        element = element_store.get(element_id)
        if not element:
            return {"status": "error", "message": f"Element ID {element_id} not found in element store"}

        for attempt in range(3):
            try:
                element.click()
                return {
                    "status": "success",
                    "element_id": element_id,
                    "message": f"Successfully tapped element: {element_id}"
                }
            except StaleElementReferenceException:
                time.sleep(1)

        return {
            "status": "error",
            "message": f"Failed to tap element {element_id} after retries due to staleness"
        }

    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "message": f"Failed to tap element: {str(e)}"
        }


def get_session_info() -> dict:
    """
    Get information about the current session
    """
    if not active_session.get("driver"):
        return {
            "status": "no_session",
            "message": "No active session"
        }
    
    try:
        driver = active_session["driver"]
        return {
            "status": "active",
            "session_id": active_session["session_id"],
            "platform": driver.capabilities.get("platformName"),
            "device": driver.capabilities.get("deviceName"),
            "automation": driver.capabilities.get("automationName"),
            "app": driver.capabilities.get("app", "Browser"),
            "message": "Session is active"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get session info: {str(e)}"
        }

def quit_session() -> dict:
    """
    Quit the current session
    """
    try:
        if active_session.get("driver"):
            active_session["driver"].quit()
            session_id = active_session["session_id"]
            active_session["driver"] = None
            active_session["session_id"] = None
            return {
                "status": "success",
                "message": f"Session {session_id} terminated successfully"
            }
        else:
            return {
                "status": "no_session",
                "message": "No active session to quit"
            }
    except Exception as e:
        # Force cleanup even if quit fails
        active_session["driver"] = None
        active_session["session_id"] = None
        return {
            "status": "error",
            "message": f"Error quitting session: {str(e)}"
        }
    
def input_text(element_id: str = None, text: str = "", strategy: str = None, value: str = None) -> dict:
    """
    Send input text to an element either by stored ID or by finding it on-the-fly
    """
    try:
        if not active_session.get("driver"):
            return {"status": "error", "message": "No active session"}

        driver = active_session["driver"]

        if element_id:
            element = element_store.get(element_id)
            if not element:
                return {"status": "error", "message": f"Element ID {element_id} not found in element store"}
        elif strategy and value:
            if strategy == "id":
                element = driver.find_element("id", value)
            elif strategy == "xpath":
                element = driver.find_element("xpath", value)
            elif strategy == "class_name":
                element = driver.find_element("class name", value)
            elif strategy == "accessibility_id":
                element = driver.find_element("accessibility id", value)
            else:
                return {
                    "status": "error",
                    "message": f"Unsupported locator strategy: {strategy}"
                }
            element_store[element.id] = element
            element_id = element.id
        else:
            return {"status": "error", "message": "Must provide either element_id or strategy+value"}

        element.send_keys(text)

        return {
            "status": "success",
            "element_id": element_id,
            "text": text,
            "message": f"Sent text to element: {element_id}"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
def get_page_source(full: bool = False) -> dict:
    try:
        driver = active_session.get("driver")
        if not driver:
            return {"status": "error", "message": "No active session"}

        source = driver.page_source

        if not full:
            max_len = 30000
            if len(source) > max_len:
                source = source[:max_len] + "\n... [truncated]"

        return {"status": "success", "page_source": source}

    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "message": f"Failed to get page source: {str(e)}"
        }



    
def scroll(direction: str = "down") -> dict:
    try:
        if not active_session.get("driver"):
            return {"status": "error", "message": "No active session"}

        size = active_session["driver"].get_window_size()
        width = size["width"]
        height = size["height"]

        start_x = width // 2
        start_y = int(height * 0.8 if direction == "down" else height * 0.2)
        end_y = int(height * 0.2 if direction == "down" else height * 0.8)

        active_session["driver"].swipe(start_x, start_y, start_x, end_y)
        return {"status": "success", "direction": direction, "message": f"Scrolled {direction}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
def get_text(element_id: str) -> dict:
    """
    Retrieve the text content of a previously located element.
    """
    try:
        if not active_session.get("driver"):
            return {
                "status": "error",
                "message": "No active session. Please start a session first."
            }

        element = element_store.get(element_id)
        if not element:
            return {
                "status": "error",
                "message": f"No element found with ID: {element_id}"
            }

        text = element.text
        return {
            "status": "success",
            "element_id": element_id,
            "text": text,
            "message": f"Retrieved text from element: {text}"
        }

    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "message": f"Failed to retrieve text: {str(e)}"
        }

    


# Initialize the MCP server
server = Server("appium-mcp-server")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """
    List available tools.
    """
    return [
        Tool(
            name="appium_start_session",
            description="Start an Appium session with desired capabilities",
            inputSchema={
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "enum": ["iOS", "Android"],
                        "description": "Platform name (iOS/Android)"
                    },
                    "device_name": {
                        "type": "string",
                        "description": "Device name or UDID"
                    },
                    "app_path": {
                        "type": "string",
                        "description": "Path to the application",
                        "default": ""
                    }
                },
                "required": ["platform", "device_name"]
            }
        ),
        Tool(
            name="appium_find_element",
            description="Find an element on the screen",
            inputSchema={
                "type": "object",
                "properties": {
                    "strategy": {
                        "type": "string",
                        "enum": ["id", "xpath", "class_name", "accessibility_id"],
                        "description": "Locator strategy"
                    },
                    "value": {
                        "type": "string",
                        "description": "Locator value"
                    }
                },
                "required": ["strategy", "value"]
            }
        ),
        Tool(
            name="appium_tap_element",
            description="Tap on an element",
            inputSchema={
                "type": "object",
                "properties": {
                    "element_id": {
                        "type": "string",
                        "description": "Element ID to tap"
                    }
                },
                "required": ["element_id"]
            }
        ),
        Tool(
            name="appium_get_session_info",
            description="Get information about the current session",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="appium_input_text",
            description="Send text to an input element",
            inputSchema={
                "type": "object",
                "properties": {
                "element_id": {"type": "string", "description": "Element ID"},
                "text": {"type": "string", "description": "Text to input"},
                },
                "required": ["element_id", "text"]
             }
        ),
        Tool(
            name="appium_get_page_source",
            description="Get the current page source",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="appium_scroll",
            description="Scroll the screen up or down",
            inputSchema={
                "type": "object",
                "properties": {
                "direction": {
                "type": "string",
                "enum": ["up", "down"],
                "default": "down",
                "description": "Scroll direction"
                }
                }
            }
        ),
         Tool(
            name="appium_get_text",
            description="Get the visible text content of an element",
            inputSchema={
                "type": "object",
                "properties": {
                    "element_id": {
                        "type": "string",
                        "description": "Element ID to retrieve text from"
                    }
                },
                "required": ["element_id"]
            }
        ),

        Tool(
            name="appium_quit_session",
            description="Quit the current Appium session",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """
    Handle tool calls for Appium operations.
    """
    
    if name == "appium_start_session":
        platform = arguments.get("platform")
        device_name = arguments.get("device_name")
        app_path = arguments.get("app_path", "")
        
        if not platform or not device_name:
            result = {
                "status": "error",
                "message": "Missing required parameters: platform and device_name"
            }
        else:
            result = start_session(platform, device_name, app_path)
            
    elif name == "appium_find_element":
        strategy = arguments.get("strategy")
        value = arguments.get("value")
        
        if not strategy or not value:
            result = {
                "status": "error",
                "message": "Missing required parameters: strategy and value"
            }
        else:
            result = find_element(strategy, value)
            
    elif name == "appium_tap_element":
        element_id = arguments.get("element_id")
        
        if not element_id:
            result = {
                "status": "error",
                "message": "Missing required parameter: element_id"
            }
        else:
            result = tap_element(element_id)
            
    elif name == "appium_get_session_info":
        result = get_session_info()
        
    elif name == "appium_quit_session":
        result = quit_session()
    
    elif name == "appium_input_text":
        element_id = arguments.get("element_id")
        text = arguments.get("text")
        result = input_text(element_id, text)
    
    elif name == "appium_get_text":
        element_id = arguments.get("element_id")

        if not element_id:
            result = {
                "status": "error",
                "message": "Missing required parameter: element_id"
            }
        else:
            result = get_text(element_id)

    elif name == "appium_get_page_source":
        result = get_page_source()

    elif name == "appium_scroll":
        direction = arguments.get("direction", "down")
        result = scroll(direction)
        
    else:
        result = {
            "status": "error",
            "message": f"Unknown tool: {name}"
        }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]

async def main():
    # Import here to avoid issues with event loops
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="appium-mcp-server",
                server_version="0.2.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
