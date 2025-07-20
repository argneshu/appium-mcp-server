#!/usr/bin/env python3
# enhanced_mcp_client.py - Enhanced Client with Safari URL Fix

import asyncio
import json
import re
import time
from typing import Optional, Tuple, Dict, Any, List

class EnhancedMCPClient:
    def __init__(self, process):
        self.process = process
        self.request_id = 0
        self.element_store = {}  
        self.last_element_id = None
        self.last_find_result = None
        self.last_result = None  # Store last tool result for variable substitution
        self.session_active = False
        self.current_platform = None
        
    def get_next_id(self):
        self.request_id += 1
        return self.request_id
        
    async def send_request(self, method, params=None):
        request = {
            "jsonrpc": "2.0",
            "id": self.get_next_id(),
            "method": method,
            "params": params or {}
        }
        
        request_str = json.dumps(request) + "\n"
        print(f"📤 Sending: {request_str.strip()}")
        
        self.process.stdin.write(request_str)
        self.process.stdin.flush()
        
        response_line = self.process.stdout.readline()
        if not response_line:
            raise Exception("No response from MCP server")
            
        print(f"📥 Received: {response_line.strip()}")
        
        try:
            response = json.loads(response_line)
            if "error" in response:
                raise Exception(f"MCP Error: {response['error']}")
            return response.get("result")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response: {e}")
    
    async def send_notification(self, method, params=None):
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        
        notification_str = json.dumps(notification) + "\n"
        print(f"📤 Sending notification: {notification_str.strip()}")
        
        self.process.stdin.write(notification_str)
        self.process.stdin.flush()
    
    async def initialize(self):
        init_result = await self.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "clientInfo": {"name": "generic-mobile-automation-client", "version": "1.0.0"}
        })
        
        await self.send_notification("notifications/initialized")
        return init_result
    
    async def list_tools(self):
        return await self.send_request("tools/list")
    
    async def call_tool(self, name, arguments):
        return await self.send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })
    
    def parse_tool_result(self, result) -> Dict[str, Any]:
        """Parse tool result and extract meaningful data."""
        if isinstance(result, dict) and result.get('content'):
            content_text = result['content'][0]['text']
            try:
                return json.loads(content_text)
            except json.JSONDecodeError:
                return {"status": "error", "message": "Invalid JSON in response"}
        return {"status": "error", "message": "No content in response"}
    
    def normalize_app_identifier(self, app_info: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize app identifiers for different platforms and apps."""
        platform = app_info.get("platform", "").lower()
        
        # Common app bundle ID mappings for your existing server
        common_apps = {
            "ios": {
                "settings": "com.apple.Preferences",
                "safari": "com.apple.mobilesafari", 
                "notes": "com.apple.mobilenotes",
                "photos": "com.apple.mobileslideshow",
                "messages": "com.apple.MobileSMS",
                "phone": "com.apple.mobilephone",
                "calculator": "com.apple.calculator",
                "calendar": "com.apple.mobilecal",
                "contacts": "com.apple.MobileAddressBook",
                "music": "com.apple.Music",
                "maps": "com.apple.Maps",
                "weather": "com.apple.weather",
                "clock": "com.apple.mobiletimer",
                "reminder": "com.apple.reminders",
                "mail": "com.apple.mobilemail",
                "files": "com.apple.DocumentsApp",
                "facetime": "com.apple.facetime",
                "podcasts": "com.apple.podcasts"
            },
            "android": {
                "settings": "com.android.settings",
                "chrome": "com.android.chrome",
                "contacts": "com.android.contacts",
                "phone": "com.android.dialer",
                "messages": "com.google.android.apps.messaging",
                "gallery": "com.google.android.apps.photos",
                "calculator": "com.google.android.calculator",
                "calendar": "com.google.calendar",
                "gmail": "com.google.android.gm",
                "maps": "com.google.android.apps.maps",
                "youtube": "com.google.android.youtube",
                "play": "com.android.vending"
            }
        }
        
        # Extract app information from different possible keys
        app_name = None
        bundle_id = None
        app_path = None
        
        # Handle various app identifier formats
        for key in ["app", "bundle_id", "bundleId", "app_package", "appPackage", "app_path", "appPath"]:
            if key in app_info and app_info[key]:
                value = str(app_info[key]).lower().strip()
                
                # If it looks like a bundle ID, use it directly
                if "." in value and (value.startswith("com.") or value.startswith("org.") or value.startswith("io.")):
                    bundle_id = app_info[key]  # Keep original case
                # If it's a file path
                elif value.endswith(".app") or "/" in value:
                    app_path = app_info[key]
                # Otherwise treat as app name
                else:
                    app_name = value
        
        # If we have an app name but no bundle ID, try to resolve it
        if app_name and not bundle_id and platform in common_apps:
            bundle_id = common_apps[platform].get(app_name)
        
        # Build the normalized app info to match your existing server expectations
        normalized = {
            "platform": app_info.get("platform"),
            "device_name": app_info.get("device_name") or app_info.get("deviceName")
        }
        
        # Add platform version if provided
        if app_info.get("platform_version") or app_info.get("platformVersion"):
            normalized["platform_version"] = app_info.get("platform_version") or app_info.get("platformVersion")
        
        # Add any other optional parameters that your server supports
        optional_fields = [
            "app_activity", "appActivity", "start_url", "startUrl",
            "udid", "xcode_org_id", "xcodeOrgId", "wda_bundle_id", "wdaBundleId",
            "xcode_signing_id", "xcodeSigningId"
        ]
        
        for field in optional_fields:
            if field in app_info and app_info[field]:
                # Normalize field names to snake_case to match your server
                normalized_field = re.sub(r'([A-Z])', r'_\1', field).lower()
                normalized[normalized_field] = app_info[field]
        
        # Add the appropriate app identifier based on your server's expectations
        if platform == "ios":
            if bundle_id:
                # Special handling for Safari - for URL navigation, don't send bundle_id
                # unless it's a real device (which might need bundle_id)
                if bundle_id == "com.apple.mobilesafari":
                    # Check if this looks like a real device configuration
                    has_real_device_params = any(param in app_info for param in 
                        ["udid", "xcode_org_id", "wda_bundle_id"])
                    
                    if has_real_device_params:
                        # Real device - send both bundle_id and browser_name
                        normalized["bundle_id"] = bundle_id
                        normalized["browser_name"] = "Safari"  # Force browser_name for URL navigation
                    else:
                        # Simulator - don't send bundle_id, let server set browser_name automatically
                        pass  # This makes server go to else branch and set browser_name = "Safari"
                else:
                    normalized["bundle_id"] = bundle_id
            elif app_path:
                normalized["app_path"] = app_path
        elif platform == "android":
            if bundle_id:
                normalized["app_package"] = bundle_id
                # For Android, we might need to infer the activity
                if not app_info.get("app_activity") and not app_info.get("appActivity"):
                    normalized["app_activity"] = f"{bundle_id}.MainActivity"  # Common pattern
            elif app_path:
                normalized["app_path"] = app_path
        
        return normalized
    
    async def start_session(self, session_args: Dict[str, Any]) -> Dict[str, Any]:
        """Start an Appium session using your existing server."""
        print(f"🚀 Starting session for {session_args.get('platform')} app...")
        
        # Normalize the session arguments
        normalized_args = self.normalize_app_identifier(session_args)
        
        # Remove any None values
        clean_args = {k: v for k, v in normalized_args.items() if v is not None}
        
        print(f"📋 Normalized session args: {json.dumps(clean_args, indent=2)}")
        
        result = await self.call_tool("appium_start_session", clean_args)
        parsed_result = self.parse_tool_result(result)
        
        if parsed_result.get('status') == 'success':
            self.session_active = True
            self.current_platform = clean_args.get('platform', '').lower()
            print(f"✅ Session started successfully for {self.current_platform}")
        else:
            print(f"❌ Session failed: {parsed_result}")
            
        return parsed_result
    
    async def enhanced_extract_selectors(self, max_elements: int = 50) -> Dict[str, Any]:
        """
        Fixed XML parser that works with standard ElementTree - no getparent() used
        """
        print(f"🔍 Using enhanced XML parser to extract elements...")
        
        # First get the raw page source from your existing server
        page_source_result = await self.call_tool("appium_get_page_source", {"full": True})
        parsed_page_source = self.parse_tool_result(page_source_result)
        
        if parsed_page_source.get('status') != 'success':
            return {"status": "error", "message": "Failed to get page source"}
        
        xml_source = parsed_page_source.get('page_source', '')
        if not xml_source:
            return {"status": "error", "message": "Empty page source"}
        
        # Parse mobile XML properly
        import xml.etree.ElementTree as ET
        
        try:
            root = ET.fromstring(xml_source)
        except ET.ParseError as e:
            return {"status": "error", "message": f"Failed to parse XML: {str(e)}"}

        elements = []
        count = 0
        
        # Simple recursive traversal - NO getparent() used
        def traverse_element(elem):
            nonlocal count
            if count >= max_elements:
                return
                
            attribs = elem.attrib
            
            # Extract element information
            element_info = {
                "tag": elem.tag,
                "text": None,
                "accessibility_id": None,
                "id": None,
                "class_name": None,
                "xpath": f"//{elem.tag}",
                "clickable": False,
                "enabled": True,
                "label": None
            }
            
            # Extract text content
            if elem.text and elem.text.strip():
                element_info["text"] = elem.text.strip()
            
            # iOS attributes - extract both name and label
            if 'name' in attribs:
                element_info["accessibility_id"] = attribs['name']
            if 'label' in attribs:
                element_info["label"] = attribs['label']
                # Use label as text if no text content exists
                if not element_info["text"]:
                    element_info["text"] = attribs['label']
            if 'value' in attribs and not element_info["text"]:
                element_info["text"] = attribs['value']
            if 'accessible' in attribs:
                element_info["clickable"] = attribs['accessible'].lower() == 'true'
            if 'enabled' in attribs:
                element_info["enabled"] = attribs['enabled'].lower() == 'true'
                
            # Android attributes  
            if 'content-desc' in attribs:
                element_info["accessibility_id"] = attribs['content-desc']
            if 'resource-id' in attribs:
                element_info["id"] = attribs['resource-id']
            if 'class' in attribs:
                element_info["class_name"] = attribs['class']
            if 'text' in attribs and not element_info["text"]:
                element_info["text"] = attribs['text']
            if 'clickable' in attribs:
                element_info["clickable"] = attribs['clickable'].lower() == 'true'
            if 'enabled' in attribs:
                element_info["enabled"] = attribs['enabled'].lower() == 'true'
                
            # Only include elements that have useful information
            has_useful_info = (
                element_info["text"] or 
                element_info["accessibility_id"] or 
                element_info["id"] or
                element_info["label"] or
                (element_info["tag"] and element_info["tag"] not in [
                    'hierarchy', 'android.widget.FrameLayout', 
                    'XCUIElementTypeApplication', 'XCUIElementTypeWindow', 'XCUIElementTypeOther'
                ])
            )
            
            if has_useful_info:
                # Clean up the element info - remove None and False values
                clean_element = {k: v for k, v in element_info.items() if v is not None and v != False}
                elements.append(clean_element)
                count += 1
            
            # Recursively process children
            for child in elem:
                if count >= max_elements:
                    break
                traverse_element(child)
        
        # Start traversal
        traverse_element(root)
        
        print(f"✅ Enhanced parser found {len(elements)} useful elements")
        
        return {
            "status": "success",
            "elements": elements,
            "total_found": len(elements),
            "source": "enhanced_xml_parser"
        }

    async def smart_find_element(self, strategy: str, value: str, description: str = None) -> Tuple[Optional[str], Dict[str, Any]]:
        """Enhanced find element with multiple strategies and fallbacks."""
        print(f"🔍 Looking for element: {description or value} using {strategy}")
    
        # NEW: Detect if we're in Safari web context
        if await self._is_web_context():
            return await self._find_web_element(strategy, value, description)
    
        # EXISTING: Native app logic - keep everything as it was
        result = await self.call_tool("appium_find_element", {
            "strategy": strategy,
            "value": value
        })
    
        parsed_result = self.parse_tool_result(result)
    
        if parsed_result.get('status') == 'success':
            element_id = parsed_result.get('element_id')
            if element_id:
                self.last_element_id = element_id
                self.last_find_result = parsed_result
            
                # Store element for future reference
                key = description or value
                self.element_store[key] = element_id
            
                print(f"✅ Found element: {element_id}")
                print(f"🔄 Stored as last_element_id: {self.last_element_id}")
                return element_id, parsed_result
    
        # If direct approach failed, try with page inspection using enhanced parser
        print(f"❌ Direct search failed, trying with enhanced page inspection...")
        element_id, result = await self.find_element_with_inspection(value, description)
        return element_id, result
    
    async def find_element_with_inspection(self, target_text: str, description: str = None) -> Tuple[Optional[str], Dict[str, Any]]:
        """Find element by inspecting available elements using enhanced XML parsing."""
        print(f"🔍 Inspecting page to find: {description or target_text}")
        
        # Use enhanced XML parser
        parsed_selectors = await self.enhanced_extract_selectors(max_elements=50)
        
        if parsed_selectors.get('status') != 'success':
            return None, {"status": "error", "message": "Failed to inspect page"}
        
        elements = parsed_selectors.get('elements', [])
        
        # Try different matching strategies
        candidates = self._find_element_candidates(elements, target_text)
        
        if not candidates:
            print(f"❌ No candidates found for '{target_text}'")
            return None, {"status": "error", "message": f"Element '{target_text}' not found"}
        
        # Try candidates in order of match quality
        return await self._try_element_candidates(candidates, target_text, description)
    
    def _find_element_candidates(self, elements: List[Dict], target_text: str) -> List[Tuple[str, Dict]]:
        """Find potential element candidates using various matching strategies."""
        candidates = []
        target_lower = target_text.lower().strip()
        
        for element in elements:
            element_text = str(element.get('text') or '').lower().strip()
            accessibility_id = str(element.get('accessibility_id') or '').lower().strip()
            label = str(element.get('label') or '').lower().strip()
            
            # Exact match (highest priority)
            if (element_text == target_lower or 
                accessibility_id == target_lower or
                label == target_lower):
                candidates.append(("exact", element))
            
            # Contains match
            elif (target_lower in element_text or 
                  target_lower in accessibility_id or
                  target_lower in label):
                candidates.append(("contains", element))
        
        return candidates
    
    async def _try_element_candidates(self, candidates: List[Tuple[str, Dict]], target_text: str, description: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """Try to find elements from candidates using different strategies."""
        for match_type, element in candidates:
            print(f"🎯 Trying {match_type} match: '{element.get('text', 'No text')}'")
            
            # Try different locator strategies
            strategies = [
                ("accessibility_id", element.get('accessibility_id')),
                ("xpath", element.get('xpath')),
                ("id", element.get('id')),
                ("class_name", element.get('class_name'))
            ]
            
            for strategy, value in strategies:
                if value and str(value).strip():
                    try:
                        result = await self.call_tool("appium_find_element", {
                            "strategy": strategy,
                            "value": str(value)
                        })
                        
                        parsed_result = self.parse_tool_result(result)
                        
                        if parsed_result.get('status') == 'success':
                            element_id = parsed_result.get('element_id')
                            if element_id:
                                self.last_element_id = element_id
                                print(f"✅ Found using {strategy}='{value}': {element_id}")
                                return element_id, parsed_result
                    except Exception as e:
                        continue
        
        return None, {"status": "error", "message": f"Could not find element '{target_text}' with any strategy"}
    
    async def smart_tap_element(self, element_id: str = None) -> Dict[str, Any]:
        """Smart tap using your existing server."""
        
        # If no element_id provided, use the last found element
        if not element_id:
            element_id = self.last_element_id
        
        if not element_id:
            return {"status": "error", "message": "No element ID available for tap"}
        
        print(f"👆 Tapping element: {element_id}")
        result = await self.call_tool("appium_tap_element", {"element_id": element_id})
        return self.parse_tool_result(result)
    
    async def smart_get_text(self, element_id: str = None) -> Dict[str, Any]:
        """Smart get text with automatic element resolution."""
        
        # If no element_id provided, use the last found element
        if not element_id:
            element_id = self.last_element_id
        
        if not element_id:
            return {"status": "error", "message": "No element ID available for get text"}
        
        print(f"📖 Getting text from element: {element_id}")
        result = await self.call_tool("appium_get_text", {"element_id": element_id})
        return self.parse_tool_result(result)
    
    async def smart_input_text(self, text: str, element_id: str = None) -> Dict[str, Any]:
        """Smart input text with automatic element resolution."""
        
        # If no element_id provided, use the last found element
        if not element_id:
            element_id = self.last_element_id
        
        if element_id:
            print(f"⌨️  Inputting text to element {element_id}: '{text}'")
            result = await self.call_tool("appium_input_text", {
                "element_id": element_id,
                "text": text
            })
        else:
            print(f"⌨️  Inputting text directly: '{text}'")
            result = await self.call_tool("appium_input_text", {"text": text})
        
        return self.parse_tool_result(result)
    
    async def scroll_to_find_element(self, strategy: str, value: str, max_scrolls: int = 5) -> Tuple[Optional[str], Dict[str, Any]]:
        """Scroll and try to find element."""
        for i in range(max_scrolls):
            print(f"🔄 Scroll attempt {i+1}/{max_scrolls}")
            
            # Try to find element first
            element_id, result = await self.smart_find_element(strategy, value)
            if element_id:
                return element_id, result
            
            # Scroll down
            await self.call_tool("appium_scroll", {"direction": "down"})
            await asyncio.sleep(1)  # Wait for scroll to complete
        
        return None, {"status": "error", "message": f"Element '{value}' not found after {max_scrolls} scrolls"}
    
    async def take_screenshot(self, filename: str = None) -> Dict[str, Any]:
        """Take screenshot using your existing server."""
        args = {}
        if filename:
            args["filename"] = filename
        
        print(f"📸 Taking screenshot{f': {filename}' if filename else ''}")
        result = await self.call_tool("appium_take_screenshot", args)
        return self.parse_tool_result(result)
    
    async def quit_session(self) -> Dict[str, Any]:
        """Quit session using your existing server."""
        print("🔚 Quitting session")
        result = await self.call_tool("appium_quit_session", {})
        self.session_active = False
        self.current_platform = None
        self.element_store.clear()
        return self.parse_tool_result(result)
    
    async def _is_web_context(self) -> bool:
        """Check if we're in Safari web context by looking at page source."""
        try:
            page_source_result = await self.call_tool("appium_get_page_source", {"full": False})
            parsed_result = self.parse_tool_result(page_source_result)
            if parsed_result.get('status') == 'success':
                source = parsed_result.get('page_source', '')
            # If it contains HTML tags, we're in web context
                return '<html' in source or '<body' in source
        except:
            pass
        return False
    
    async def _find_web_element(self, strategy: str, value: str, description: str = None) -> Tuple[Optional[str], Dict[str, Any]]:
        """Find element using web-specific strategies."""
        print(f"🌐 Web context detected, using web strategies for: {value}")

        # Extract actual text content if value is an XPath
        target_text = self._extract_text_from_xpath_or_value(value)
        print(f"🎯 Extracted target text: '{target_text}'")
    
        # For web elements, try link text strategies first
        web_strategies = [
            ("link text", target_text),
            ("partial link text", target_text),
            ("xpath", f"//a[contains(text(), '{target_text}')]"),
            ("xpath", f"//*[contains(text(), '{target_text}')]"),
            ("xpath", value)
        ]
    
        for web_strategy, web_value in web_strategies:
            try:
                print(f"🔍 Trying web strategy: {web_strategy}='{web_value}'")
                result = await self.call_tool("appium_find_element", {
                    "strategy": web_strategy,
                    "value": web_value
                })
            
                parsed_result = self.parse_tool_result(result)
                if parsed_result.get('status') == 'success':
                    element_id = parsed_result.get('element_id')
                    if element_id:
                        self.last_element_id = element_id
                        print(f"✅ Found web element using {web_strategy}: {element_id}")
                        return element_id, parsed_result
            except Exception as e:
                print(f"⚠️ Web strategy {web_strategy} failed: {e}")
                continue
    
        return None, {"status": "error", "message": f"Web element '{value}' not found"}
    
    def _extract_text_from_xpath_or_value(self, value: str) -> str:
        """Extract actual text content from XPath or return the value as-is."""
        # If it looks like an XPath with contains(text(), '...'), extract the text
        import re
    
        # Pattern to match: contains(text(), 'some text')
        match = re.search(r"contains\(text\(\),\s*['\"]([^'\"]+)['\"]", value)
        if match:
            extracted_text = match.group(1)
            print(f"📝 Extracted text from XPath: '{extracted_text}'")
            return extracted_text
    
    # If it's not an XPath, return as-is
        return value
    