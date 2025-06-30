import asyncio
import json
from mcp.server.stdio import stdio_server
from mcp.server import Server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    CallToolRequest,
    CallToolResult,
    ListResourcesRequest,
    ListToolsRequest,
    ReadResourceRequest,
)
from pydantic import AnyUrl
from appium_controller import (
    start_session,
    find_element,
    tap_element,
    input_text,
    get_page_source,
    scroll
)

# Create the server instance
server = Server("appium-mcp-server")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    print("DEBUG: list_tools called - returning available tools")
    """List available tools for Appium automation."""
    return [
        Tool(
            name="appium_start_session",
            description="Start an Appium session with desired capabilities",
            inputSchema={
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "description": "Platform name (iOS/Android)",
                        "enum": ["iOS", "Android"]
                    },
                    "device_name": {
                        "type": "string",
                        "description": "Device name or UDID"
                    },
                    "app_path": {
                        "type": "string",
                        "description": "Path to the application"
                    },
                    "bundle_id": {
                        "type": "string",
                        "description": "iOS bundle ID to launch an installed app"
                    },
                    "app_package": {
                        "type": "string",
                        "description": "Android app package name"
                    },
                    "app_activity": {
                        "type": "string",
                        "description": "Android app activity name"
                    },
                    "start_url": {
                        "type": "string",
                        "description": "Optional: URL to navigate if browser is launched"
                    }
                },
                "required": ["platform", "device_name"]
            }
        ),

        Tool(
            name="appium_input_text",
            description="Send text input to an element by ID or by strategy/value",
            inputSchema={
                "type": "object",
                "properties": {
                "element_id": {
                "type": "string",
                "description": "Optional: Element ID to send text to"
                    },
                "text": {
                "type": "string",
                "description": "The text to input"
                    },
                "strategy": {
                "type": "string",
                "enum": ["id", "xpath", "class_name", "accessibility_id"],
                "description": "Optional: Locator strategy if no element_id"
                     },
                "value": {
                "type": "string",
                "description": "Optional: Locator value if no element_id"
                    }
                },
        "required": ["text"]
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
                        "description": "Locator strategy",
                        "enum": ["id", "xpath", "class_name", "accessibility_id"]
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
            name="appium_scroll",
            description="Scroll the screen in the specified direction (down or up)",
            inputSchema={
                "type": "object",
                "properties": {
                "direction": {
                "type": "string",
                "enum": ["up", "down"],
                "description": "Direction to scroll (default is down)"
                    }   
                },
        "required": []
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
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls for Appium operations."""
    print(f"DEBUG: ANY tool call received: name={name}, args={arguments}")

    if name == "appium_start_session":
        platform = arguments.get("platform")
        device_name = arguments.get("device_name")
        app_path = arguments.get("app_path", "")
        bundle_id = arguments.get("bundle_id", "")
        app_package = arguments.get("app_package", "")
        app_activity = arguments.get("app_activity", "")
        start_url=arguments.get("start_url", "")

        try:
            result = start_session(platform, device_name, app_path, bundle_id, app_package, app_activity, start_url)
            if result is None:
                raise ValueError("start_session returned None unexpectedly")
        except Exception as e:
            result = {
                "status": "error",
                "message": f"Exception in start_session: {str(e)}"
            }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "appium_find_element":
        strategy = arguments.get("strategy")
        value = arguments.get("value")
        result = find_element(strategy, value)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "appium_tap_element":
        element_id = arguments.get("element_id")
        result = tap_element(element_id)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "appium_input_text":
        element_id = arguments.get("element_id")
        text = arguments.get("text")
        strategy = arguments.get("strategy")
        value = arguments.get("value")
        result = input_text(element_id, text)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "appium_get_page_source":
        result = get_page_source()
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "appium_scroll":
        direction = arguments.get("direction", "down")
        result = scroll(direction)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]



@server.list_resources()
async def handle_list_resources() -> list[Resource]:
    """List available resources."""
    return [
        Resource(
            uri=AnyUrl("appium://capabilities"),
            name="Appium Capabilities",
            description="Available Appium capabilities and configurations",
            mimeType="application/json"
        )
    ]

@server.read_resource()
async def handle_read_resource(uri: AnyUrl) -> str:
    """Read resource content."""
    print("DEBUG: list_tools handler called!")
    if str(uri) == "appium://capabilities":
        capabilities = {
            "iOS": {
                "platformName": "iOS",
                "platformVersion": "17.0",
                "deviceName": "iPhone 15 Pro Max",
                "automationName": "XCUITest"
            },
            "Android": {
                "platformName": "Android",
                "platformVersion": "14.0",
                "deviceName": "Android Emulator",
                "automationName": "UiAutomator2"
            }
        }
        return json.dumps(capabilities, indent=2)
    
    raise ValueError(f"Unknown resource: {uri}")

async def main():
    """Main function to run the MCP server."""
    EXPECTED_VERSION = "0.1.12"
    print("🚀 Starting Appium MCP Server on {EXPECTED_VERSION}..")
    
    async with stdio_server() as (read_stream, write_stream):
        print(f"✅ MCP server booting with version {EXPECTED_VERSION}")
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
