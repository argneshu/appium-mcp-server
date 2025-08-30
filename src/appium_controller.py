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
import re
import uuid
import os
import subprocess
import socket
import urllib.request
import json
import platform
import sys
from datetime import datetime
from bs4 import BeautifulSoup

# Appium imports
from appium import webdriver
from appium.options.ios import XCUITestOptions
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy


# Global session storage
active_session = {
    "driver": None,
    "session_id": None
}

# Global store for WebElements
element_store = {}

def start_session(platform: str, device_name: str, app_path: str = "", bundle_id: str = "", app_package: str = "", app_activity: str = "", start_url: str = "", udid: str = "", xcode_org_id: str = "", wda_bundle_id: str = "", xcode_signing_id: str = "iPhone Developer", use_new_wda: bool = False,use_prebuilt_wda: bool = True,skip_server_installation: bool = True,show_xcode_log: bool = True, no_reset: bool = True, platform_version: str = "",port: int = 4723) -> dict:
    print(f"DEBUG: start_session called with platform={platform}, device={device_name}, , udid={udid}", file=sys.stderr)
    print("🚀 MCP Server: Running from local-mcp-server", file=sys.stderr)

    try:
        if platform.lower() == "ios":
            print("Using XCUITestOptions approach")
            options = XCUITestOptions()
            options.platform_name = "iOS"
            options.device_name = device_name
            if not platform_version:
                platform_version = get_latest_ios_simulator_version()
            options.platform_version = platform_version
            options.automation_name = "XCUITest"
            
            udid_is_valid = bool(udid) and isinstance(udid, str)
            device_name_looks_like_udid = (
                isinstance(device_name, str) and (
                    (len(device_name) == 25 and device_name.count("-") == 4) or
                    (len(device_name) == 40 and all(c in "0123456789abcdefABCDEF" for c in device_name))
                )
            )
            if udid_is_valid:
                print("DEBUG: Explicit UDID provided — setting udid", file=sys.stderr)
                options.udid = udid
            elif device_name_looks_like_udid:
                print("DEBUG: Device name looks like UDID — assuming real device", file=sys.stderr)
                options.udid = device_name
            elif device_name.lower().startswith("iphone") or device_name.lower().startswith("ipad"):
                print("DEBUG: iOS Simulator detected", file=sys.stderr)
            else:
                print("⚠️ Unknown device_name format — not setting UDID", file=sys.stderr)

            if udid_is_valid or device_name_looks_like_udid:
                print(f"DEBUG: Real iOS device detected", file=sys.stderr)
                options.udid = udid or device_name
                options.platform_version = "17.0"

                if xcode_org_id and wda_bundle_id:
                    options.xcode_org_id = xcode_org_id
                    options.xcode_signing_id = xcode_signing_id or "iPhone Developer"
                    options.updated_wda_bundle_id = wda_bundle_id
                    options.use_new_wda = use_new_wda
                    options.use_prebuilt_wda = use_prebuilt_wda
                    options.skip_server_installation = skip_server_installation
                    options.show_xcode_log = show_xcode_log
                    options.no_reset = no_reset
                    options.start_iwdp = True
                    options.wda_launch_timeout = 60000
                    options.wda_connection_timeout = 60000
        
                else:
                    print("Real device detected but xcode_org_id or wda_bundle_id not provided", file=sys.stderr)
            elif udid:
                print(f"DEBUG: Simulator with explicit UDID: {udid}", file=sys.stderr)
                options.udid = udid
            else:
                print("DEBUG: iOS simulator without UDID — letting Appium choose", file=sys.stderr)

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
            if not platform_version:
                platform_version = get_latest_android_emulator_version()
            options.device_name = device_name
            options.automation_name = "UiAutomator2"
            options.chromedriver_autodownload = True

            is_real_device = len(device_name) > 8 and not device_name.startswith("emulator")

            if is_real_device:
                print("DEBUG: Real Android device detected", file=sys.stderr)
                options.udid = udid or device_name
                options.system_port = 8200
            elif udid:
                print(f"DEBUG: Android emulator with explicit UDID: {udid}", file=sys.stderr)
                options.udid = udid
            else:
                print("DEBUG: Android emulator without UDID — letting Appium choose", file=sys.stderr)

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
        options.no_reset = False
        port = ensure_appium_installed_and_running()

        driver = webdriver.Remote(f"http://localhost:{port}", options=options)
        active_session["driver"] = driver
        active_session["session_id"] = driver.session_id

        print(f"DEBUG: browser_name = {getattr(options, 'browser_name', None)}", file=sys.stderr)
        print(f"DEBUG: start_url = {start_url}", file=sys.stderr)
        print(f"DEBUG: Should navigate = {getattr(options, 'browser_name', None) and start_url}", file=sys.stderr)

        if getattr(options, "browser_name", None) and start_url:
            print(f"DEBUG: Starting URL navigation to {start_url}", file=sys.stderr)
            import time
            print(f"DEBUG: Waiting for Safari context before navigating to {start_url}", file=sys.stderr)
            time.sleep(3)  # Allow Safari to launch

            driver.implicitly_wait(10)
            max_wait = 15
            interval = 1
            found_webview = False

            for _ in range(max_wait):
                contexts = driver.contexts
                print(f"DEBUG: Available contexts: {contexts}", file=sys.stderr)
                for ctx in contexts:
                    if "WEBVIEW" in ctx or "Safari" in ctx:
                        print(f"DEBUG: Switching to context: {ctx}", file=sys.stderr)
                        driver.switch_to.context(ctx)
                        found_webview = True
                        break
                if found_webview:
                    break
                time.sleep(interval)

            if found_webview:
                print(f"DEBUG: Navigating to URL: {start_url}", file=sys.stderr)
                driver.get(start_url)
            else:
                print("❌ No webview context found. Cannot navigate to URL.", file=sys.stderr)

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
    


def extract_selectors_from_page_source(max_elements: int = 25) -> dict:
    try:
        driver = active_session.get("driver")
        if not driver:
            return {"status": "error", "message": "No active session"}

        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")

        preview = []
        for tag in soup.find_all(True):
            if len(preview) >= max_elements:
                break
            info = {
                "tag": tag.name,
                "id": tag.get("id"),
                "class": tag.get("class"),
                "accessibility": tag.get("aria-label") or tag.get("aria-labelledby")
            }
            preview.append({k: v for k, v in info.items() if v})

        return {
            "status": "success",
            "selectors": preview
        }

    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "message": f"Failed to extract selectors: {str(e)}"
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
            # 🔐 Tighter Claude-safe truncation
            source = source.encode("utf-8", errors="ignore").decode("utf-8")  # sanitize
            max_len = 10000  # much safer default
            if len(source) > max_len:
                source = source[:max_len] + "\n... [truncated]"

        return {
            "status": "success",
            "page_source": source
        }

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
    
def get_latest_ios_simulator_version() -> str:
    import subprocess
    import re
    try:
        output = subprocess.check_output(["xcrun", "simctl", "list", "runtimes"], text=True)
        versions = re.findall(r'iOS (\d+\.\d+)', output)
        versions = sorted({float(v) for v in versions}, reverse=True)
        return str(versions[0]) if versions else "17.0"
    except Exception as e:
        print(f"⚠️ Failed to detect iOS version from simctl: {e}", file=sys.stderr)
        return "17.0"
    
def get_latest_android_emulator_version() -> str:
    import subprocess
    import re
    try:
        output = subprocess.check_output(["emulator", "-list-avds"], text=True)
        avds = output.strip().splitlines()
        versions = [int(re.search(r'API_(\d+)', avd).group(1)) for avd in avds if "API_" in avd]
        return f"{max(versions)}.0" if versions else "14.0"
    except Exception as e:
        print(f"⚠️ Failed to detect Android version: {e}", file=sys.stderr)
        return "14.0"
    

def take_screenshot(filename: str = None) -> dict:
    driver = active_session.get("driver")
    if not driver:
        return {"status": "error", "message": "No active session"}

    # Auto-generate filename if not provided
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:6]
        filename = f"screenshot_{timestamp}_{unique_id}.png"

    # Save to user's Desktop in a cross-platform way
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    os.makedirs(desktop_path, exist_ok=True)  # Ensure directory exists
    save_path = os.path.join(desktop_path, filename)

    try:
        success = driver.save_screenshot(save_path)
        if not success:
            return {
                "status": "error",
                "message": "Appium driver failed to capture screenshot"
            }

        return {
            "status": "success",
            "filename": filename,
            "path": save_path,
            "message": f"📸 Screenshot saved at: {save_path}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to take screenshot: {str(e)}"
        }


DEFAULT_APPIUM_PORT = 4723

def ensure_appium_installed_and_running() -> int:
    port = DEFAULT_APPIUM_PORT
    print(f"🔧 Using fixed Appium port: {port}", file=sys.stderr)

    # Check if something is already running on the port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if sock.connect_ex(('localhost', port)) == 0:
            print(f"✅ Appium already running on port {port}", file=sys.stderr)
            return port

    # Check if Appium is installed
    try:
        subprocess.check_call(["npx", "appium", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        raise RuntimeError("❌ 'npx' not found. Please install Node.js and npm.")
    except subprocess.CalledProcessError:
        raise RuntimeError("❌ 'npx appium --version' failed. Is Appium installed? Try: npm install -g appium")

    # Try launching Appium
    print(f"🚀 Appium not running. Attempting to launch on port {port}...", file=sys.stderr)
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0

    try:
        process = subprocess.Popen(
            ["npx", "appium", "-p", str(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags
        )
    except Exception as e:
        raise RuntimeError(f"❌ Failed to launch Appium: {e}")

    # Wait for Appium to come up
    max_wait_time = 30
    wait_interval = 1
    elapsed_time = 0

    print("⏳ Waiting for Appium to start...", file=sys.stderr)
    while elapsed_time < max_wait_time:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(('localhost', port)) == 0:
                print(f"✅ Appium started successfully on port {port}", file=sys.stderr)
                return port
        time.sleep(wait_interval)
        elapsed_time += wait_interval
        print(f"⏳ Still waiting... ({elapsed_time}s)", file=sys.stderr)

    raise Exception(f"❌ Appium failed to start on port {port} within {max_wait_time} seconds")




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
    


def grant_ios_permissions(bundle_id: str, permissions: list[str]) -> dict:
    errors = []
    for perm in permissions:
        try:
            subprocess.run(
                ["xcrun", "simctl", "privacy", "booted", "grant", perm, bundle_id],
                check=True
            )
        except subprocess.CalledProcessError:
            errors.append(f"❌ Failed to grant {perm}")
    return {
        "status": "success" if not errors else "partial",
        "granted": [p for p in permissions if p not in errors],
        "errors": errors
    }


def handle_ios_alert():
    driver = active_session.get("driver")
    if not driver:
        return {"status": "error", "message": "❌ No active Appium session"}

    try:
        alert = driver.switch_to.alert
        alert_text = alert.text
        print(f"🔔 Alert detected: {alert_text}", file=sys.stderr)
        alert.accept()
        return {"status": "success", "message": "✅ Alert accepted"}
    except Exception:
        # Fallback: try tapping common alert buttons
        try:
            allow_button = driver.find_element(by=AppiumBy.ACCESSIBILITY_ID, value="Allow")
            allow_button.click()
            return {"status": "success", "message": "✅ Tapped 'Allow' button"}
        except Exception:
            return {"status": "error", "message": "⚠️ No system alert or 'Allow' button found"}
        



