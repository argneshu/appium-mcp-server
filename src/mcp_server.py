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
    scroll,
    get_text,
    extract_selectors_from_page_source
)
import os
import pathlib
from tools.create_project_handler import handle_create_project_tool
from tools.write_files_batch import handle_write_files_batch

# Create the server instance
server = Server("appium-mcp-server")

# Add new FILE TOOL after mcp is created
PROJECT_ROOT = pathlib.Path.home() / "generated-framework"
PROJECT_ROOT.mkdir(parents=True, exist_ok=True)


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
            },
             "udid": {
                 "type": "string",
                 "description": "UDID of the real device (optional, inferred from device_name if missing)"
             },
            "xcode_org_id": {
                "type": "string",
                "description": "Apple Developer Team ID (iOS real device only)"
             },
            "wda_bundle_id": {
                 "type": "string",
                 "description": "Updated WDA bundle ID for iOS real device"
            },
            "xcode_signing_id": {
                "type": "string",
                "description": "Xcode signing identity (e.g. 'iPhone Developer')"
            }
                },
                "required": ["platform", "device_name"]
             }
        ),
        Tool(
            name="extract_selectors_from_page_source",
            description="Extract a small preview of tag names, IDs, classes, and accessibility labels from the page source for faster inspection.",
            inputSchema={
                 "type": "object",
                 "properties": {
                        "max_elements": {
                            "type": "integer",
                            "description": "Maximum number of elements to preview (default 25)"
                    }
                },
                "required": []
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
            name="appium_get_page_source",
            description="Get the XML page source from the current screen",
            inputSchema={
                 "type": "object",
                 "properties": {
                        "full": {
                            "type": "boolean",
                            "description": "Whether to return the full page source (default is false/truncated)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="write_files_batch",
            description="Write multiple files at once under ~/generated-framework/<path>",
            inputSchema={
                "type": "object",
                "properties": {
                    "files": {
                    "type": "array",
                    "description": "List of files to write with relative paths and content",
                    "items": {
                        "type": "object",
                        "properties": {
                        "path": {"type": "string", "description": "Relative path inside the project root"},
                        "content": {"type": "string", "description": "Content to write to the file"}
                        },
                    "required": ["path", "content"]
                    }
                }
            },
                "required": ["files"]
            }
        ),
        Tool(
            name="write_file",
            description="Write a file under ~/generated-framework/<path>",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path inside project"},
                    "content": {"type": "string", "description": "File content"}
                },
                "required": ["path", "content"]
            }
        ),
        Tool(
            name="create_project",
            description="Scaffold a generic Java Maven + TestNG Appium project.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_name": {
                    "type": "string",
                    "description": "Root folder of the project (e.g. youtube-appium-tests)"
                    },
                "package": {
                    "type": "string",
                    "description": "Java base package (e.g. com.mycompany.app). If omitted, it is inferred."
                    },
                "pages": {
                    "type": "array",
                    "description": "Page object class names (without .java)",
                    "items": { "type": "string" }
                    },
                "tests": {
                    "type": "array",
                    "description": "Test class names (without .java)",
                    "items": { "type": "string" }
                    }
                },
                "required": ["project_name"]
            }
        ),

    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls for Appium operations."""
    print(f"DEBUG: ANY tool call received: name={name}, args={arguments}")


    # ✅ NEW TOOL HANDLER: write_file
    if name == "write_file":
        path = arguments.get("path")
        content = arguments.get("content")

        try:
            target_path = PROJECT_ROOT / path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(content)
            return [TextContent(type="text", text=f"✅ File written to: {target_path}")]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Failed to write file: {str(e)}")]

    if name == "appium_start_session":
        platform = arguments.get("platform")
        device_name = arguments.get("device_name")
        app_path = arguments.get("app_path", "")
        bundle_id = arguments.get("bundle_id", "")
        app_package = arguments.get("app_package", "")
        app_activity = arguments.get("app_activity", "")
        start_url=arguments.get("start_url", "")
        udid=arguments.get("udid", "")
        xcode_org_id=arguments.get("xcode_org_id", "")
        wda_bundle_id=arguments.get("wda_bundle_id", "")
        xcode_signing_id = arguments.get("xcode_signing_id", "iPhone Developer")

           # 🆕 WDA-related options with enforced defaults
        use_new_wda = arguments.get("use_new_wda", False)
        use_prebuilt_wda = arguments.get("use_prebuilt_wda", True)
        skip_server_installation = arguments.get("skip_server_installation", True)
        show_xcode_log = arguments.get("show_xcode_log", True)
        no_reset = arguments.get("no_reset", True)

            # Filter out empty/None values to avoid sending invalid udid etc.
        kwargs = {
            "platform": platform,
            "device_name": device_name
            }
        optional_fields = {
            "app_path": app_path,
            "bundle_id": bundle_id,
            "app_package": app_package,
            "app_activity": app_activity,
            "start_url": start_url,
            "udid": udid,
            "xcode_org_id": xcode_org_id,
            "wda_bundle_id": wda_bundle_id,
            "xcode_signing_id": xcode_signing_id
            }
        if udid:
            optional_fields.update({
            "use_new_wda": use_new_wda,
            "use_prebuilt_wda": use_prebuilt_wda,
            "skip_server_installation": skip_server_installation,
            "show_xcode_log": show_xcode_log,
            "no_reset": no_reset
        })

        for key, value in optional_fields.items():
            if value:  # skip empty string or None
                kwargs[key] = value

        try:
            result = start_session(**kwargs)
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
        full = arguments.get("full", False)
        result = get_page_source(full=full)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "appium_scroll":
        direction = arguments.get("direction", "down")
        result = scroll(direction)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "extract_selectors_from_page_source":
        max_elements = arguments.get("max_elements", 25)
        result = extract_selectors_from_page_source(max_elements=max_elements)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    
    elif name == "appium_get_text":
        element_id = arguments.get("element_id")
        result = get_text(element_id)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "create_project":
        return handle_create_project_tool(arguments)
    
    elif name == "write_files_batch":
        result_text = await handle_write_files_batch(arguments)
        return [result_text]

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
    print(f"🚀 Starting Appium MCP Server on {EXPECTED_VERSION}..")
    
    async with stdio_server() as (read_stream, write_stream):
        print(f"✅ MCP server booting with version {EXPECTED_VERSION}")
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
