#!/usr/bin/env python3
# enhanced_mcp_client.py - Fixed Enhanced Client with Working XML Parser

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
        
        # Add the appropriate app identifier based on your server's expectations
        if platform == "ios":
            if bundle_id:
                normalized["bundle_id"] = bundle_id
                # Special handling for Safari - add start URL to open to blank page
                if bundle_id == "com.apple.mobilesafari":
                    normalized["start_url"] = "about:blank"  # Start with blank page instead of homepage
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

    async def find_element_with_inspection(self, target_text: str, description: str = None) -> Tuple[Optional[str], Dict[str, Any]]:
        """Find element by inspecting available elements using enhanced XML parsing."""
        print(f"🔍 Inspecting page to find: {description or target_text}")
        
        # Use enhanced XML parser instead of server's extract_selectors_from_page_source
        parsed_selectors = await self.enhanced_extract_selectors(max_elements=50)
        
        if parsed_selectors.get('status') != 'success':
            # Fallback to server's method if enhanced parser fails
            print("⚠️  Enhanced parser failed, falling back to server's method...")
            selectors_result = await self.call_tool("extract_selectors_from_page_source", {
                "max_elements": 50
            })
            parsed_selectors = self.parse_tool_result(selectors_result)
            
            if parsed_selectors.get('status') != 'success':
                return None, {"status": "error", "message": "Failed to inspect page"}
        
        # Handle both enhanced format and server's format
        if parsed_selectors.get('source') == 'enhanced_xml_parser':
            # Enhanced format with better element structure
            elements = parsed_selectors.get('elements', [])
            print(f"📋 Enhanced parser found {len(elements)} elements on page")
        else:
            # Server's format (fallback)
            elements = parsed_selectors.get('elements', []) or parsed_selectors.get('selectors', [])
            print(f"📋 Server parser found {len(elements)} elements on page")
            
            # Convert server format to enhanced format
            standardized_elements = []
            for element in elements:
                if 'tag' in element:
                    # Server returns tag-based format
                    standardized = {
                        'text': element.get('tag', ''),
                        'accessibility_id': element.get('accessibility') or element.get('id'),
                        'id': element.get('id'),
                        'class_name': element.get('class')
                    }
                else:
                    standardized = element
                standardized_elements.append(standardized)
            elements = standardized_elements
        
        # Try different matching strategies
        candidates = self._find_element_candidates(elements, target_text)
        
        if not candidates:
            print(f"❌ No candidates found for '{target_text}'")
            self._print_available_elements(elements)
            return None, {"status": "error", "message": f"Element '{target_text}' not found"}
        
        # Try candidates in order of match quality
        return await self._try_element_candidates(candidates, target_text, description)
    
    async def smart_find_element(self, strategy: str, value: str, description: str = None) -> Tuple[Optional[str], Dict[str, Any]]:
        """Enhanced find element with multiple strategies and fallbacks."""
        print(f"🔍 Looking for element: {description or value} using {strategy}")
        
        # First, try the direct approach using your existing server
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
        return await self.find_element_with_inspection(value, description)
    
    def _find_element_candidates(self, elements: List[Dict], target_text: str) -> List[Tuple[str, Dict]]:
        """Find potential element candidates using various matching strategies."""
        candidates = []
        target_lower = target_text.lower().strip()
        
        for element in elements:
            element_text = str(element.get('text') or '').lower().strip()
            accessibility_id = str(element.get('accessibility_id') or '').lower().strip()
            label = str(element.get('label') or '').lower().strip()
            
            # Exact match (highest priority) - check text, accessibility_id, and label
            if (element_text == target_lower or 
                accessibility_id == target_lower or
                label == target_lower):
                candidates.append(("exact", element))
            
            # Special handling for iOS settings - match against both name and label
            elif target_lower == "general":
                if ("com.apple.settings.general" in accessibility_id or 
                    "general" in accessibility_id or
                    "general" in element_text or
                    "general" in label):
                    candidates.append(("ios_special", element))
            
            # Word boundary match
            elif (f" {target_lower} " in f" {element_text} " or 
                  f" {target_lower} " in f" {accessibility_id} " or
                  f" {target_lower} " in f" {label} "):
                candidates.append(("word", element))
            
            # Contains match
            elif (target_lower in element_text or 
                  target_lower in accessibility_id or
                  target_lower in label):
                candidates.append(("contains", element))
            
            # Partial word match (for typos or partial matches)
            elif any(word in element_text or word in accessibility_id or word in label 
                    for word in target_lower.split() if len(word) > 2):
                candidates.append(("partial", element))
            
            # Fuzzy match (remove spaces, special chars)
            clean_text = re.sub(r'[^\w]', '', element_text)
            clean_id = re.sub(r'[^\w]', '', accessibility_id)
            clean_label = re.sub(r'[^\w]', '', label)
            clean_target = re.sub(r'[^\w]', '', target_lower)
            if clean_target and len(clean_target) > 2 and (
                clean_target in clean_text or 
                clean_target in clean_id or 
                clean_target in clean_label):
                candidates.append(("fuzzy", element))
        
        # Sort by match quality - iOS special handling gets high priority
        priority = {"exact": 0, "ios_special": 1, "word": 2, "contains": 3, "partial": 4, "fuzzy": 5}
        candidates.sort(key=lambda x: priority.get(x[0], 99))
        
        return candidates
    
    async def _try_element_candidates(self, candidates: List[Tuple[str, Dict]], target_text: str, description: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """Try to find elements from candidates using different strategies."""
        for match_type, element in candidates:
            print(f"🎯 Trying {match_type} match: '{element.get('text', 'No text')}' (ID: {element.get('accessibility_id', 'No ID')})")
            
            # Try different locator strategies with your server
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
                                self.last_find_result = parsed_result
                                
                                key = description or target_text
                                self.element_store[key] = element_id
                                
                                print(f"✅ Found using {strategy}='{value}': {element_id}")
                                return element_id, parsed_result
                    except Exception as e:
                        print(f"⚠️  Failed {strategy}='{value}': {e}")
                        continue
        
        return None, {"status": "error", "message": f"Could not find element '{target_text}' with any strategy"}
    
    def _print_available_elements(self, elements: List[Dict], max_show: int = 15):
        """Print available elements for debugging."""
        print("Available elements:")
        for i, element in enumerate(elements[:max_show]):
            text = element.get('text', 'No text')
            acc_id = element.get('accessibility_id', 'No ID')
            label = element.get('label', '')
            display_text = text or label or acc_id
            print(f"  {i+1:2d}. '{display_text}' (ID: {acc_id})")
        if len(elements) > max_show:
            print(f"  ... and {len(elements) - max_show} more elements")
    
    async def smart_tap_element(self, element_id: str = None, find_args: Dict = None) -> Dict[str, Any]:
        """Smart tap using your existing server."""
        
        # Handle placeholder element IDs
        if element_id == "__element_id_returned_by_previous_step__":
            element_id = self.last_element_id
            print(f"🔄 Using last element ID: {element_id}")
        
        # If no element_id provided, use the last found element
        if not element_id:
            element_id = self.last_element_id
            print(f"🔄 No element_id provided, using last found element: {element_id}")
        
        # If still no element_id and find_args provided, try to find it
        if not element_id and find_args:
            element_id, find_result = await self.smart_find_element(
                find_args.get('strategy', 'accessibility_id'),
                find_args.get('value'),
                find_args.get('description')
            )
        
        if not element_id:
            return {"status": "error", "message": "No element ID available for tap"}
        
        print(f"👆 Tapping element: {element_id}")
        result = await self.call_tool("appium_tap_element", {"element_id": element_id})
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
    
    async def input_text(self, text: str, element_id: str = None, find_args: Dict = None) -> Dict[str, Any]:
        """Input text using your existing server."""
        
        # Handle placeholder element IDs
        if element_id == "__element_id_returned_by_previous_step__":
            element_id = self.last_element_id
            print(f"🔄 Using last element ID for input: {element_id}")
        
        # If no element_id provided, try to find it
        if not element_id and find_args:
            element_id, find_result = await self.smart_find_element(
                find_args.get('strategy', 'accessibility_id'),
                find_args.get('value'),
                find_args.get('description')
            )
        
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
    
    async def get_element_text(self, element_id: str) -> Dict[str, Any]:
        """Get text from element using your existing server."""
        if element_id == "__element_id_returned_by_previous_step__":
            element_id = self.last_element_id
            print(f"🔄 Using last element ID for text: {element_id}")
        
        print(f"📖 Getting text from element: {element_id}")
        result = await self.call_tool("appium_get_text", {"element_id": element_id})
        return self.parse_tool_result(result)
    
    async def smart_get_text(self, element_id: str = None) -> Dict[str, Any]:
        """Smart get text with automatic element resolution."""
        
        # Handle placeholder element IDs
        if element_id == "__element_id_returned_by_previous_step__":
            element_id = self.last_element_id
            print(f"🔄 Using last element ID for text: {element_id}")
        
        # If no element_id provided, use the last found element
        if not element_id:
            element_id = self.last_element_id
            print(f"🔄 No element_id provided, using last found element: {element_id}")
        
        if not element_id:
            return {"status": "error", "message": "No element ID available for get text"}
        
        print(f"📖 Getting text from element: {element_id}")
        result = await self.call_tool("appium_get_text", {"element_id": element_id})
        return self.parse_tool_result(result)
    
    async def smart_input_text(self, text: str, element_id: str = None) -> Dict[str, Any]:
        """Smart input text with automatic element resolution."""
        
        # Handle placeholder element IDs
        if element_id == "__element_id_returned_by_previous_step__":
            element_id = self.last_element_id
            print(f"🔄 Using last element ID for input: {element_id}")
        
        # If no element_id provided, use the last found element
        if not element_id:
            element_id = self.last_element_id
            print(f"🔄 No element_id provided, using last found element: {element_id}")
        
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
    
    async def get_page_source(self, full: bool = True) -> Dict[str, Any]:
        """Get page source using your existing server."""
        print(f"📄 Getting page source (full={full})")
        result = await self.call_tool("appium_get_page_source", {"full": full})
        return self.parse_tool_result(result)
    
    async def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: int = 1000) -> Dict[str, Any]:
        """Perform swipe gesture using your existing server."""
        print(f"👉 Swiping from ({start_x}, {start_y}) to ({end_x}, {end_y}) in {duration}ms")
        result = await self.call_tool("appium_swipe", {
            "start_x": start_x,
            "start_y": start_y,
            "end_x": end_x,
            "end_y": end_y,
            "duration": duration
        })
        return self.parse_tool_result(result)
    
    async def smart_swipe(self, direction: str = "up", distance: str = "medium") -> Dict[str, Any]:
        """Smart swipe with predefined directions and distances."""
        # Define common swipe patterns for different screen sizes
        screen_width = 430  # iPhone 15 Pro Max width
        screen_height = 932  # iPhone 15 Pro Max height
        
        # Adjust for different distances
        distance_multipliers = {
            "short": 0.2,
            "medium": 0.4, 
            "long": 0.6,
            "full": 0.8
        }
        
        multiplier = distance_multipliers.get(distance, 0.4)
        
        # Calculate swipe coordinates based on direction
        center_x = screen_width // 2
        center_y = screen_height // 2
        
        if direction.lower() == "up":
            start_x, start_y = center_x, int(screen_height * (0.7))
            end_x, end_y = center_x, int(screen_height * (0.7 - multiplier))
        elif direction.lower() == "down":
            start_x, start_y = center_x, int(screen_height * (0.3))
            end_x, end_y = center_x, int(screen_height * (0.3 + multiplier))
        elif direction.lower() == "left":
            start_x, start_y = int(screen_width * (0.7)), center_y
            end_x, end_y = int(screen_width * (0.7 - multiplier)), center_y
        elif direction.lower() == "right":
            start_x, start_y = int(screen_width * (0.3)), center_y
            end_x, end_y = int(screen_width * (0.3 + multiplier)), center_y
        else:
            return {"status": "error", "message": f"Invalid swipe direction: {direction}"}
        
        return await self.swipe(start_x, start_y, end_x, end_y)
    
    async def tap_coordinates(self, x: int, y: int) -> Dict[str, Any]:
        """Tap at specific coordinates."""
        print(f"👆 Tapping at coordinates ({x}, {y})")
        result = await self.call_tool("appium_tap_coordinates", {"x": x, "y": y})
        return self.parse_tool_result(result)
    
    async def long_press(self, element_id: str = None, x: int = None, y: int = None, duration: int = 2000) -> Dict[str, Any]:
        """Perform long press on element or coordinates."""
        if element_id:
            if element_id == "__element_id_returned_by_previous_step__":
                element_id = self.last_element_id
            print(f"👆 Long pressing element: {element_id} for {duration}ms")
            result = await self.call_tool("appium_long_press", {
                "element_id": element_id,
                "duration": duration
            })
        elif x is not None and y is not None:
            print(f"👆 Long pressing at ({x}, {y}) for {duration}ms")
            result = await self.call_tool("appium_long_press", {
                "x": x,
                "y": y, 
                "duration": duration
            })
        else:
            return {"status": "error", "message": "Either element_id or coordinates (x,y) must be provided"}
        
        return self.parse_tool_result(result)
    
    async def double_tap(self, element_id: str = None, x: int = None, y: int = None) -> Dict[str, Any]:
        """Perform double tap on element or coordinates."""
        if element_id:
            if element_id == "__element_id_returned_by_previous_step__":
                element_id = self.last_element_id
            print(f"👆👆 Double tapping element: {element_id}")
            result = await self.call_tool("appium_double_tap", {"element_id": element_id})
        elif x is not None and y is not None:
            print(f"👆👆 Double tapping at ({x}, {y})")
            result = await self.call_tool("appium_double_tap", {"x": x, "y": y})
        else:
            return {"status": "error", "message": "Either element_id or coordinates (x,y) must be provided"}
        
        return self.parse_tool_result(result)
    
    async def pinch(self, scale: float = 0.5) -> Dict[str, Any]:
        """Perform pinch gesture (zoom out)."""
        print(f"👌 Pinching with scale: {scale}")
        result = await self.call_tool("appium_pinch", {"scale": scale})
        return self.parse_tool_result(result)
    
    async def zoom(self, scale: float = 2.0) -> Dict[str, Any]:
        """Perform zoom gesture (zoom in)."""
        print(f"🔍 Zooming with scale: {scale}")
        result = await self.call_tool("appium_zoom", {"scale": scale})
        return self.parse_tool_result(result)
    
    async def wait_for_element(self, strategy: str, value: str, timeout: int = 10) -> Tuple[Optional[str], Dict[str, Any]]:
        """Wait for element to appear with timeout."""
        print(f"⏰ Waiting for element '{value}' (timeout: {timeout}s)")
        
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            element_id, result = await self.smart_find_element(strategy, value)
            if element_id:
                print(f"✅ Element found after {time.time() - start_time:.1f}s")
                return element_id, result
            
            await asyncio.sleep(1)  # Wait 1 second before retrying
        
        return None, {"status": "error", "message": f"Element '{value}' not found within {timeout}s"}
    
    async def get_element_attribute(self, element_id: str, attribute: str) -> Dict[str, Any]:
        """Get attribute value from element."""
        if element_id == "__element_id_returned_by_previous_step__":
            element_id = self.last_element_id
        
        print(f"📋 Getting attribute '{attribute}' from element: {element_id}")
        result = await self.call_tool("appium_get_attribute", {
            "element_id": element_id,
            "attribute": attribute
        })
        return self.parse_tool_result(result)
    
    async def is_element_displayed(self, element_id: str) -> Dict[str, Any]:
        """Check if element is displayed."""
        if element_id == "__element_id_returned_by_previous_step__":
            element_id = self.last_element_id
        
        print(f"👁️  Checking if element is displayed: {element_id}")
        result = await self.call_tool("appium_is_displayed", {"element_id": element_id})
        return self.parse_tool_result(result)
    
    async def clear_text(self, element_id: str = None) -> Dict[str, Any]:
        """Clear text from element."""
        if not element_id:
            element_id = self.last_element_id
        
        if element_id == "__element_id_returned_by_previous_step__":
            element_id = self.last_element_id
        
        print(f"🧹 Clearing text from element: {element_id}")
        result = await self.call_tool("appium_clear", {"element_id": element_id})
        return self.parse_tool_result(result)
    
    async def hide_keyboard(self) -> Dict[str, Any]:
        """Hide the keyboard."""
        print("⌨️ Hiding keyboard")
        result = await self.call_tool("appium_hide_keyboard", {})
        return self.parse_tool_result(result)
    
    async def get_device_info(self) -> Dict[str, Any]:
        """Get device information."""
        print("📱 Getting device info")
        result = await self.call_tool("appium_get_device_info", {})
        return self.parse_tool_result(result)
    
    async def rotate_device(self, orientation: str) -> Dict[str, Any]:
        """Rotate device to specified orientation."""
        print(f"🔄 Rotating device to: {orientation}")
        result = await self.call_tool("appium_rotate", {"orientation": orientation})
        return self.parse_tool_result(result)
    
    async def write_file(self, path: str, content: str) -> Dict[str, Any]:
        """Write content to a file."""
        print(f"📝 Writing file: {path}")
        result = await self.call_tool("write_file", {"path": path, "content": content})
        return self.parse_tool_result(result)
    
    async def write_files_batch(self, files: List[Dict[str, str]]) -> Dict[str, Any]:
        """Write multiple files at once."""
        print(f"📝 Writing {len(files)} files in batch")
        result = await self.call_tool("write_files_batch", {"files": files})
        return self.parse_tool_result(result)
    
    async def create_project(self, project_name: str, package: str = None, pages: List[str] = None, tests: List[str] = None) -> Dict[str, Any]:
        """Create a new automation project structure."""
        args = {"project_name": project_name}
        if package:
            args["package"] = package
        if pages:
            args["pages"] = pages
        if tests:
            args["tests"] = tests
        
        print(f"🏗️  Creating project: {project_name}")
        result = await self.call_tool("create_project", args)
        return self.parse_tool_result(result)
    
    async def grant_ios_permissions(self, bundle_id: str, permissions: List[str]) -> Dict[str, Any]:
        """Grant permissions to iOS app."""
        print(f"🔓 Granting iOS permissions for {bundle_id}: {permissions}")
        result = await self.call_tool("grant_ios_permissions", {
            "bundle_id": bundle_id,
            "permissions": permissions
        })
        return self.parse_tool_result(result)
    
    async def handle_ios_alert(self) -> Dict[str, Any]:
        """Handle iOS system alerts by tapping Allow/OK."""
        print("🚨 Handling iOS alert")
        result = await self.call_tool("appium_handle_ios_alert", {})
        return self.parse_tool_result(result)
    
    # Add any other methods that might be missing from your server's tool list
    async def get_current_activity(self) -> Dict[str, Any]:
        """Get current Android activity (if supported by server)."""
        print("📱 Getting current activity")
        result = await self.call_tool("appium_get_current_activity", {})
        return self.parse_tool_result(result)
    
    async def get_window_size(self) -> Dict[str, Any]:
        """Get window size."""
        print("📐 Getting window size")
        result = await self.call_tool("appium_get_window_size", {})
        return self.parse_tool_result(result)
    
    async def set_network_connection(self, connection_type: int) -> Dict[str, Any]:
        """Set network connection type (Android)."""
        print(f"📶 Setting network connection: {connection_type}")
        result = await self.call_tool("appium_set_network_connection", {"connection_type": connection_type})
        return self.parse_tool_result(result)
    
    async def install_app(self, app_path: str) -> Dict[str, Any]:
        """Install app on device."""
        print(f"📲 Installing app: {app_path}")
        result = await self.call_tool("appium_install_app", {"app_path": app_path})
        return self.parse_tool_result(result)
    
    async def remove_app(self, bundle_id: str) -> Dict[str, Any]:
        """Remove app from device."""
        print(f"🗑️ Removing app: {bundle_id}")
        result = await self.call_tool("appium_remove_app", {"bundle_id": bundle_id})
        return self.parse_tool_result(result)
    
    async def activate_app(self, bundle_id: str) -> Dict[str, Any]:
        """Activate (launch) app."""
        print(f"▶️ Activating app: {bundle_id}")
        result = await self.call_tool("appium_activate_app", {"bundle_id": bundle_id})
        return self.parse_tool_result(result)
    
    async def terminate_app(self, bundle_id: str) -> Dict[str, Any]:
        """Terminate app."""
        print(f"⏹️ Terminating app: {bundle_id}")
        result = await self.call_tool("appium_terminate_app", {"bundle_id": bundle_id})
        return self.parse_tool_result(result)
    
    async def background_app(self, duration: int = 5) -> Dict[str, Any]:
        """Put app in background for specified duration."""
        print(f"📱 Backgrounding app for {duration} seconds")
        result = await self.call_tool("appium_background_app", {"duration": duration})
        return self.parse_tool_result(result)
    
    # Convenience methods that match your exact server tool names
    async def extract_selectors_from_page_source(self, max_elements: int = 25) -> Dict[str, Any]:
        """Extract selectors using server's method (fallback for enhanced parser)."""
        print(f"🔍 Using server's extract_selectors_from_page_source (max: {max_elements})")
        result = await self.call_tool("extract_selectors_from_page_source", {"max_elements": max_elements})
        return self.parse_tool_result(result)
    
    # Enhanced method that combines server method with enhanced parsing
    async def smart_extract_selectors(self, max_elements: int = 25, prefer_enhanced: bool = True) -> Dict[str, Any]:
        """Smart selector extraction with fallback."""
        if prefer_enhanced:
            try:
                # Try enhanced parser first
                result = await self.enhanced_extract_selectors(max_elements)
                if result.get('status') == 'success':
                    return result
                print("⚠️ Enhanced parser failed, falling back to server method...")
            except Exception as e:
                print(f"⚠️ Enhanced parser error: {e}, falling back to server method...")
        
        # Fallback to server's method
        return await self.extract_selectors_from_page_source(max_elements)
    
    # Method aliases to match your server's exact tool names
    async def appium_start_session(self, **kwargs) -> Dict[str, Any]:
        """Alias for start_session to match server tool name."""
        return await self.start_session(kwargs)
    
    async def appium_find_element(self, strategy: str, value: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """Alias for smart_find_element to match server tool name."""
        return await self.smart_find_element(strategy, value)
    
    async def appium_tap_element(self, element_id: str = None) -> Dict[str, Any]:
        """Alias for smart_tap_element to match server tool name."""
        return await self.smart_tap_element(element_id)
    
    async def appium_input_text(self, text: str, element_id: str = None, strategy: str = None, value: str = None) -> Dict[str, Any]:
        """Input text using server's exact parameters."""
        args = {"text": text}
        
        # Handle different parameter combinations
        if element_id:
            args["element_id"] = element_id
            print(f"⌨️ Inputting text to element {element_id}: '{text}'")
        elif strategy and value:
            args["strategy"] = strategy
            args["value"] = value
            print(f"⌨️ Inputting text using {strategy}='{value}': '{text}'")
        elif self.last_element_id:
            # Use last found element if no other targeting provided
            args["element_id"] = self.last_element_id
            print(f"⌨️ Inputting text to last found element {self.last_element_id}: '{text}'")
        else:
            # Try direct text input (some servers support this)
            print(f"⌨️ Inputting text directly: '{text}'")
        
        result = await self.call_tool("appium_input_text", args)
        return self.parse_tool_result(result)
    
    async def appium_get_text(self, element_id: str) -> Dict[str, Any]:
        """Alias for get_element_text to match server tool name."""
        return await self.get_element_text(element_id)
    
    async def appium_scroll(self, direction: str = "down") -> Dict[str, Any]:
        """Alias for scroll to match server tool name."""
        return await self.scroll(direction)
    
    async def appium_get_page_source(self, full: bool = True) -> Dict[str, Any]:
        """Alias for get_page_source to match server tool name."""
        return await self.get_page_source(full)
    
    async def appium_take_screenshot(self, filename: str = None) -> Dict[str, Any]:
        """Alias for take_screenshot to match server tool name."""
        return await self.take_screenshot(filename)
    
    async def appium_quit_session(self) -> Dict[str, Any]:
        """Alias for quit_session to match server tool name."""
        return await self.quit_session()
    
    async def appium_handle_ios_alert(self) -> Dict[str, Any]:
        """Alias for handle_ios_alert to match server tool name."""
        return await self.handle_ios_alert()
    
    # Additional utility methods
    async def wait(self, duration: float) -> Dict[str, Any]:
        """Simple wait/sleep method."""
        print(f"⏰ Waiting {duration} seconds...")
        await asyncio.sleep(duration)
        return {"status": "success", "message": f"Waited {duration} seconds"}
    
    async def assert_element_exists(self, strategy: str, value: str) -> Dict[str, Any]:
        """Assert that an element exists on the page."""
        element_id, result = await self.smart_find_element(strategy, value)
        if element_id:
            return {"status": "success", "message": f"Element '{value}' exists", "element_id": element_id}
        else:
            return {"status": "error", "message": f"Element '{value}' does not exist"}
    
    async def assert_text_contains(self, element_id: str, expected_text: str) -> Dict[str, Any]:
        """Assert that element text contains expected text."""
        result = await self.get_element_text(element_id)
        if result.get('status') == 'success':
            actual_text = result.get('text', '')
            if expected_text.lower() in actual_text.lower():
                return {"status": "success", "message": f"Text contains '{expected_text}'"}
            else:
                return {"status": "error", "message": f"Text '{actual_text}' does not contain '{expected_text}'"}
        else:
            return {"status": "error", "message": "Failed to get element text"}
    
    async def get_all_available_methods(self) -> List[str]:
        """Get list of all available methods in this client."""
        methods = [method for method in dir(self) if not method.startswith('_') and callable(getattr(self, method))]
        return sorted(methods)
    
    async def scroll(self, direction: str = "down") -> Dict[str, Any]:
        """Scroll using your existing server."""
        print(f"📜 Scrolling {direction}")
        result = await self.call_tool("appium_scroll", {"direction": direction})
        return self.parse_tool_result(result)
    
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