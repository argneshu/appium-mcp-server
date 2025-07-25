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
        
        # ENHANCED: Handle Gemini's generic element ID patterns
        invalid_patterns = [
            "element_id_from_previous_step", 
            "previous_element_id", 
            "found_element_id",
            "current_element_id", 
            "last_element_id",
            "element_from_previous_step",
            "previous_element",
            None,
            "",
            "null"
        ]
    
        # If element_id is invalid or not provided, use the last found element
        if element_id in invalid_patterns:
            element_id = self.last_element_id
            print(f"🔄 Using last found element ID: {element_id}")
        elif not element_id:
            element_id = self.last_element_id
        
        if not element_id:
            return {"status": "error", "message": "No element ID available for tap"}
        
         # STEP 1: Get page fingerprint before tap
        print(f"📊 Getting page fingerprint before tap...")
        fingerprint_before = await self._get_page_fingerprint()
        
        # STEP 2: Attempt standard tap
        print(f"👆 Tapping element: {element_id}")
        result = await self.call_tool("appium_tap_element", {"element_id": element_id})
        parsed_result = self.parse_tool_result(result)
       
        if parsed_result.get('status') != 'success':
            print(f"❌ Standard tap failed: {parsed_result}")
            return parsed_result
        
        # STEP 3: Wait and check if tap actually worked
        print("⏰ Waiting for tap to take effect...")
        await asyncio.sleep(2)

        fingerprint_after = await self._get_page_fingerprint()
        tap_worked = self._did_page_change(fingerprint_before, fingerprint_after)

        if tap_worked:
            print("✅ Standard tap successful - page changed!")
            return {"status": "success", "message": "Standard tap successful"}

         # STEP 4: Standard tap didn't work, try alternative strategies
        print("⚠️ Standard tap didn't change page - trying alternative strategies...")
        return await self._try_alternative_tap_methods(element_id, fingerprint_before)

    async def smart_get_text(self, element_id: str = None) -> Dict[str, Any]:
        """Smart get text with automatic element resolution and stale element recovery."""

        # ENHANCED: Handle Gemini's generic element ID patterns
        invalid_patterns = [
            "element_id_from_previous_step", 
            "previous_element_id", 
            "found_element_id",
            "current_element_id",
            "last_element_id",
            "element_from_previous_step",
            "previous_element",
            None,
            "",
            "null"
        ]
    
        # If element_id is invalid or not provided, use the last found element
        if element_id in invalid_patterns:
            element_id = self.last_element_id
            print(f"🔄 Using last found element ID: {element_id}")
        elif not element_id:
            element_id = self.last_element_id

        if not element_id:
            return {"status": "error", "message": "No element ID available for get text"}

        print(f"📖 Getting text from element: {element_id}")
        result = await self.call_tool("appium_get_text", {"element_id": element_id})
        parsed_result = self.parse_tool_result(result)

        # ENHANCED: If stale, try smart recovery strategies
        if (parsed_result.get("status") == "error" and 
        "StaleElementReferenceException" in str(parsed_result.get("message", ""))):
        
            print("⚠️ Stale element detected, attempting recovery strategies...")
        
            # STRATEGY 1: Try to find Name cell and get its value
            recovery_result = await self.recover_name_cell_text()
            if recovery_result.get("status") == "success":
                return recovery_result
        
             # STRATEGY 2: Try XPath-based recovery
            xpath_result = await self.recover_text_via_xpath()
            if xpath_result.get("status") == "success":
                return xpath_result
        
            # STRATEGY 3: Page source parsing as last resort
            page_source_result = await self.recover_text_via_page_source()
            if page_source_result.get("status") == "success":
                return page_source_result
        
            # If all recovery failed, return helpful error
            return {
            "status": "error",
            "message": "Element became stale and recovery strategies failed. The UI may have changed significantly.",
            "error_type": "StaleElementReferenceException",
            "recovery_attempted": True
            }

        return parsed_result

    async def recover_name_cell_text(self) -> Dict[str, Any]:
        """Try to recover text by finding Name cell directly."""
        try:
            print("🔄 Attempting to find Name cell directly...")
        
            # Find Name cell using accessibility_id
            find_result = await self.call_tool("appium_find_element", {
                "strategy": "accessibility_id",
                "value": "Name"
            })
        
            parsed_find = self.parse_tool_result(find_result)
            if parsed_find.get("status") == "success":
                name_element_id = parsed_find.get("element_id")
            
                # Get text from Name cell
                text_result = await self.call_tool("appium_get_text", {
                "element_id": name_element_id
                })
            
                parsed_text = self.parse_tool_result(text_result)
                if parsed_text.get("status") == "success":
                    text = parsed_text.get("text", "")
                
                    # Return any non-empty text that's not just "Name"
                    if text and text.strip() != "Name":
                        return {
                        "status": "success",
                        "text": text,
                        "message": f"Recovered text via Name cell: {text}",
                        "method": "name_cell_recovery"
                        }
        
            return {"status": "error", "message": "Name cell recovery failed"}
        
        except Exception as e:
            print(f"⚠️ Name cell recovery error: {e}")
            return {"status": "error", "message": f"Name cell recovery failed: {str(e)}"}

    async def recover_text_via_xpath(self) -> Dict[str, Any]:
        """Try to recover text using XPath strategies."""
        try:
            print("🔄 Attempting XPath-based recovery...")
        
            xpath_strategies = [
            "//XCUIElementTypeCell[@name='Name']//XCUIElementTypeStaticText[2]",
            "//XCUIElementTypeStaticText[@name='Name']/following-sibling::XCUIElementTypeStaticText[1]",
            "//XCUIElementTypeCell[.//XCUIElementTypeStaticText[@name='Name']]//XCUIElementTypeStaticText[position()>1]",
            "//*[@name='Name']/..//XCUIElementTypeStaticText[not(@name='Name')]"
            ]
        
            for xpath in xpath_strategies:
                try:
                    print(f"🔄 Trying XPath: {xpath}")
                
                    find_result = await self.call_tool("appium_find_element", {
                    "strategy": "xpath",
                    "value": xpath
                    })
                
                    parsed_find = self.parse_tool_result(find_result)
                    if parsed_find.get("status") == "success":
                        xpath_element_id = parsed_find.get("element_id")
                    
                        text_result = await self.call_tool("appium_get_text", {
                        "element_id": xpath_element_id
                        })
                    
                        parsed_text = self.parse_tool_result(text_result)
                        if parsed_text.get("status") == "success":
                            text = parsed_text.get("text", "")
                            if text and text.strip() and text.strip() != "Name":
                                return {
                                 "status": "success",
                                "text": text,
                                "message": f"Recovered text via XPath: {text}",
                                "method": "xpath_recovery",
                                "xpath_used": xpath
                             }
                except Exception as e:
                    print(f"⚠️ XPath {xpath} failed: {e}")
                    continue
        
            return {"status": "error", "message": "All XPath strategies failed"}
        
        except Exception as e:
            print(f"⚠️ XPath recovery error: {e}")
            return {"status": "error", "message": f"XPath recovery failed: {str(e)}"}

    async def recover_text_via_page_source(self) -> Dict[str, Any]:
        """Try to recover text by parsing page source."""
        try:
            print("🔄 Attempting page source parsing recovery...")
        
            # Get current page source
            page_result = await self.call_tool("appium_get_page_source", {"full": False})
            parsed_page = self.parse_tool_result(page_result)
        
            if parsed_page.get("status") == "success":
                page_source = parsed_page.get("page_source", "")
            
                import re
            
                # Generic patterns to find Name cell value
                patterns = [
                r'name=["\']Name["\'][^>]*>.*?name=["\']([^"\']+)["\']',
                r'label=["\']Name["\'][^>]*>.*?value=["\']([^"\']+)["\']',
                r'<[^>]*name=["\']Name["\'][^>]*>.*?<[^>]*>([^<]+)</[^>]*>',
                r'Name.*?<[^>]*>([^<]+)</[^>]*>'
                ]
            
                for pattern in patterns:
                    try:
                        match = re.search(pattern, page_source, re.IGNORECASE | re.DOTALL)
                        if match:
                            found_text = match.group(1).strip()
                        
                            # Return any meaningful text that's not just "Name"
                            if found_text and found_text != "Name":
                                return {
                                "status": "success",
                                "text": found_text,
                                "message": f"Recovered text via page source: {found_text}",
                                "method": "page_source_recovery",
                                "pattern_used": pattern
                                }
                    except Exception as pattern_error:
                        print(f"⚠️ Pattern {pattern} failed: {pattern_error}")
                        continue
        
            return {"status": "error", "message": "Page source parsing failed"}
        
        except Exception as e:
            print(f"⚠️ Page source recovery error: {e}")
            return {"status": "error", "message": f"Page source recovery failed: {str(e)}"}


    
    async def smart_input_text(self, text: str, element_id: str = None) -> Dict[str, Any]:
        """Smart input text with automatic element resolution."""
        
        # ENHANCED: Handle Gemini's generic element ID patterns
        invalid_patterns = [
            "element_id_from_previous_step", 
            "previous_element_id", 
            "found_element_id",
            "current_element_id",
            "last_element_id",
            "element_from_previous_step",
            "previous_element",
            None,
            "",
            "null"
        ]
    
        # If element_id is invalid or not provided, use the last found element
        if element_id in invalid_patterns:
            element_id = self.last_element_id
            print(f"🔄 Using last found element ID: {element_id}")
        elif not element_id:
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
        """Intelligent web element finder that adapts to any website."""
        print(f"🌐 Web context detected, using intelligent strategies for: {value}")

        # Extract actual text content if value is an XPath
        target_text = self._extract_text_from_xpath_or_value(value)
        print(f"🎯 Extracted target text: '{target_text}'")
    
        # STEP 1: Try original strategy first (if provided)
        web_strategies = []
        if strategy and value and strategy != "xpath":
            web_strategies.append((strategy, value))
    
        # STEP 2: Intelligent semantic detection
        target_lower = target_text.lower().strip()
    
        # STEP 3: Build smart strategies based on semantic meaning
        smart_strategies = await self._build_smart_strategies(target_lower, target_text)
        web_strategies.extend(smart_strategies)
    
        # STEP 4: Add your original fallback strategies
        web_strategies.extend([
            ("link text", target_text),
            ("partial link text", target_text),
            ("xpath", f"//a[contains(text(), '{target_text}')]"),
            ("xpath", f"//*[contains(text(), '{target_text}')]"),
            ("xpath", value)  # Original XPath as final fallback
        ])
    
        # STEP 5: Try each strategy intelligently
        for i, (web_strategy, web_value) in enumerate(web_strategies):
            try:
                print(f"🔍 Trying intelligent strategy {i+1}/{len(web_strategies)}: {web_strategy}='{web_value}'")
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
                print(f"⚠️ Strategy {web_strategy} failed: {e}")
                continue

        # STEP 6: If all strategies fail, try page inspection approach
        print("🔍 All direct strategies failed, trying page inspection...")
        return await self._find_web_element_by_inspection(target_text, target_lower)
    

    def _analyze_html_for_candidates(self, html_source: str, target_text: str, target_lower: str) -> List[Tuple[str, str]]:
        """Analyze HTML source to find potential element candidates."""
        import re
        candidates = []
    
        # Look for input fields with relevant attributes
        input_patterns = [
            r'<input[^>]*id=["\']([^"\']*(?:' + re.escape(target_lower) + r')[^"\']*)["\']',
            r'<input[^>]*name=["\']([^"\']*(?:' + re.escape(target_lower) + r')[^"\']*)["\']',
            r'<input[^>]*class=["\']([^"\']*(?:' + re.escape(target_lower) + r')[^"\']*)["\']',
            r'<input[^>]*placeholder=["\']([^"\']*(?:' + re.escape(target_text) + r')[^"\']*)["\']',
        ]
    
        # Look for buttons with relevant attributes
        button_patterns = [
            r'<button[^>]*id=["\']([^"\']*(?:' + re.escape(target_lower) + r')[^"\']*)["\']',
            r'<button[^>]*class=["\']([^"\']*(?:' + re.escape(target_lower) + r')[^"\']*)["\']',
            r'<input[^>]*type=["\']submit["\'][^>]*value=["\']([^"\']*(?:' + re.escape(target_text) + r')[^"\']*)["\']',
        ]
    
        # Look for links with relevant attributes
        link_patterns = [
            r'<a[^>]*id=["\']([^"\']*(?:' + re.escape(target_lower) + r')[^"\']*)["\']',
            r'<a[^>]*class=["\']([^"\']*(?:' + re.escape(target_lower) + r')[^"\']*)["\']',
        ]
    
        # Search for input field candidates
        for pattern in input_patterns:
            matches = re.findall(pattern, html_source, re.IGNORECASE)
            for match in matches:
                if 'id=' in pattern:
                    candidates.append(("id", match))
                elif 'name=' in pattern:
                    candidates.append(("name", match))
                elif 'class=' in pattern:
                    candidates.append(("xpath", f"//*[contains(@class, '{match}')]"))
    
        # Search for button candidates
        for pattern in button_patterns:
            matches = re.findall(pattern, html_source, re.IGNORECASE)
            for match in matches:
                if 'id=' in pattern:
                    candidates.append(("id", match))
                elif 'class=' in pattern:
                    candidates.append(("xpath", f"//*[contains(@class, '{match}')]"))
                elif 'value=' in pattern:
                    candidates.append(("xpath", f"//input[@value='{match}']"))
    
        # Search for link candidates
        for pattern in link_patterns:
            matches = re.findall(pattern, html_source, re.IGNORECASE)
            for match in matches:
                if 'id=' in pattern:
                    candidates.append(("id", match))
                elif 'class=' in pattern:
                    candidates.append(("xpath", f"//*[contains(@class, '{match}')]"))
    
        print(f"🔍 Page analysis found {len(candidates)} potential candidates")
        return candidates
    
    async def _build_smart_strategies(self, target_lower: str, target_text: str) -> List[Tuple[str, str]]:
        """Build intelligent strategies based on semantic analysis."""
        strategies = []
    
        # USERNAME/EMAIL FIELD DETECTION
        username_keywords = ['username', 'user', 'email', 'login', 'account', 'userid', 'user_name', 'user-name']
        if any(keyword in target_lower for keyword in username_keywords):
            strategies.extend([
                # Common ID patterns
                ("id", "username"), ("id", "user"), ("id", "email"), ("id", "login"),
                ("id", "user-name"), ("id", "user_name"), ("id", "userid"), ("id", "account"),
                # Common name patterns
                ("name", "username"), ("name", "user"), ("name", "email"), ("name", "login"),
                ("name", "user-name"), ("name", "user_name"), ("name", "userid"),
                # Input type and placeholder patterns
                ("xpath", "//input[@type='text'][1]"),  # First text input
                ("xpath", "//input[@type='email']"),     # Email input type
                ("xpath", "//input[contains(@placeholder, 'username') or contains(@placeholder, 'user') or contains(@placeholder, 'email') or contains(@placeholder, 'login')]"),
                # Data attribute patterns
                ("xpath", "//input[contains(@data-test, 'username') or contains(@data-test, 'user') or contains(@data-test, 'login')]"),
                ("xpath", "//input[contains(@data-testid, 'username') or contains(@data-testid, 'user') or contains(@data-testid, 'login')]"),
                # Class patterns
                ("xpath", "//input[contains(@class, 'username') or contains(@class, 'user') or contains(@class, 'email') or contains(@class, 'login')]"),
            ])
    
        # PASSWORD FIELD DETECTION
        password_keywords = ['password', 'pass', 'pwd', 'passcode', 'passphrase']
        if any(keyword in target_lower for keyword in password_keywords):
            strategies.extend([
                # Common ID patterns
                ("id", "password"), ("id", "pass"), ("id", "pwd"), ("id", "passcode"),
                # Common name patterns  
                ("name", "password"), ("name", "pass"), ("name", "pwd"), ("name", "passcode"),
                # Password input type (most reliable)
                ("xpath", "//input[@type='password']"),
                # Placeholder patterns
                ("xpath", "//input[contains(@placeholder, 'password') or contains(@placeholder, 'pass')]"),
                # Data attribute patterns
                ("xpath", "//input[contains(@data-test, 'password') or contains(@data-test, 'pass')]"),
                ("xpath", "//input[contains(@data-testid, 'password') or contains(@data-testid, 'pass')]"),
                # Class patterns
                ("xpath", "//input[contains(@class, 'password') or contains(@class, 'pass')]"),
            ])
    
        # BUTTON/SUBMIT DETECTION
        button_keywords = ['login', 'submit', 'sign in', 'log in', 'continue', 'next', 'enter', 'go', 'send', 'confirm']
        if any(keyword in target_lower for keyword in button_keywords):
            # Try common button IDs first
            button_ids = ['login', 'submit', 'signin', 'login-button', 'submit-button', 'continue', 'next', 'send']
            for btn_id in button_ids:
                strategies.append(("id", btn_id))
                strategies.append(("name", btn_id))
        
            strategies.extend([
                #Submit input buttons
                ("xpath", "//input[@type='submit']"),
                ("xpath", "//button[@type='submit']"),
                # Value-based detection
                ("xpath", f"//input[@value='{target_text}' or contains(@value, '{target_lower}')]"),
                ("xpath", f"//button[text()='{target_text}' or contains(text(), '{target_text}')]"),
                # Generic button patterns
                ("xpath", "//button[contains(@class, 'btn') or contains(@class, 'button')]"),
                ("xpath", f"//button[contains(@class, '{target_lower}')]"),
                # Data attribute patterns
                ("xpath", f"//button[contains(@data-test, '{target_lower}') or contains(@data-testid, '{target_lower}')]"),
                ("xpath", f"//input[contains(@data-test, '{target_lower}') or contains(@data-testid, '{target_lower}')]"),
            ])
    
        # LINK DETECTION
        link_keywords = ['logout', 'sign out', 'log out', 'exit', 'quit', 'home', 'back', 'menu', 'settings']
        if any(keyword in target_lower for keyword in link_keywords):
            strategies.extend([
                # Direct link text
                ("link text", target_text),
                ("partial link text", target_text),
                # ID-based links
                ("id", target_lower), ("id", target_lower.replace(' ', '-')), ("id", target_lower.replace(' ', '_')),
                # Link patterns
                ("xpath", f"//a[contains(text(), '{target_text}') or @title='{target_text}']"),
                ("xpath", f"//a[contains(@href, '{target_lower}') or contains(@class, '{target_lower}')]"),
                # Data attribute patterns
                ("xpath", f"//a[contains(@data-test, '{target_lower}') or contains(@data-testid, '{target_lower}')]"),
            ])
    
        # MENU/NAVIGATION DETECTION
        menu_keywords = ['menu', 'hamburger', 'burger', 'nav', 'navigation', 'toggle']
        if any(keyword in target_lower for keyword in menu_keywords):
            strategies.extend([
                # Common menu IDs
                ("id", "menu"), ("id", "nav"), ("id", "hamburger"), ("id", "burger"), ("id", "toggle"),
                ("id", "menu-button"), ("id", "nav-button"), ("id", "menu-toggle"),
                # Class-based detection
                ("xpath", "//button[contains(@class, 'menu') or contains(@class, 'burger') or contains(@class, 'hamburger')]"),
                ("xpath", "//div[contains(@class, 'menu') or contains(@class, 'burger') or contains(@class, 'hamburger')]"),
                # Icon patterns (common in modern web)
                ("xpath", "//button[contains(@class, 'icon') and (contains(@class, 'menu') or contains(@aria-label, 'menu'))]"),
                # ARIA patterns
                ("xpath", "//button[@aria-label='Menu' or @aria-label='Open menu' or contains(@aria-label, 'menu')]"),
            ])
    
        # GENERIC TEXT/ELEMENT DETECTION (for anything else)
        else:
            # Try common patterns for any text
            safe_text = target_lower.replace(' ', '-')
            safe_text_underscore = target_lower.replace(' ', '_')
        
            strategies.extend([
                # ID patterns
                ("id", target_lower), ("id", safe_text), ("id", safe_text_underscore),
                # Name patterns
                ("name", target_lower), ("name", safe_text), ("name", safe_text_underscore),
                # Class patterns
                ("xpath", f"//*[contains(@class, '{target_lower}') or contains(@class, '{safe_text}')]"),
                # Data patterns
                ("xpath", f"//*[contains(@data-test, '{target_lower}') or contains(@data-testid, '{target_lower}')]"),
                # Generic text content
                ("xpath", f"//*[contains(text(), '{target_text}') or @title='{target_text}' or @alt='{target_text}']"),
            ])
    
        return strategies
    
    def _extract_text_from_xpath_or_value(self, value: str) -> str:
        """Intelligently extract meaningful text from any input format."""
        import re
    
        # STEP 1: If it's already clean text (no special characters), return as-is
        if not any(char in value for char in ['@', '/', '[', ']', '(', ')', '"', "'"]):
            return value.strip()
    
        # STEP 2: XPath and attribute patterns (ordered by reliability)
        patterns = [
            # Web-specific HTML attributes (most reliable for web)
            r"@id\s*=\s*['\"]([^'\"]+)['\"]",                 # @id='value'
            r"@name\s*=\s*['\"]([^'\"]+)['\"]",               # @name='value'  
            r"@class\s*=\s*['\"]([^'\"]+)['\"]",              # @class='value'
            r"@data-test\s*=\s*['\"]([^'\"]+)['\"]",          # @data-test='value'
            r"@data-testid\s*=\s*['\"]([^'\"]+)['\"]",        # @data-testid='value'
            r"@placeholder\s*=\s*['\"]([^'\"]+)['\"]",        # @placeholder='value'
            r"@value\s*=\s*['\"]([^'\"]+)['\"]",              # @value='value'
            r"@type\s*=\s*['\"]([^'\"]+)['\"]",               # @type='value'
            r"@href\s*=\s*['\"]([^'\"]+)['\"]",               # @href='value'
            r"@title\s*=\s*['\"]([^'\"]+)['\"]",              # @title='value'
            r"@alt\s*=\s*['\"]([^'\"]+)['\"]",                # @alt='value'
        
            # Mobile app attributes (for native contexts)
            r"@text\s*=\s*['\"]([^'\"]+)['\"]",               # @text='value'
            r"@label\s*=\s*['\"]([^'\"]+)['\"]",              # @label='value'
            r"@name\s*=\s*['\"]([^'\"]+)['\"]",               # @name='value' (iOS)
            r"@content-desc\s*=\s*['\"]([^'\"]+)['\"]",       # @content-desc='value' (Android)
            r"@resource-id\s*=\s*['\"]([^'\"]+)['\"]",        # @resource-id='value' (Android)
        
            # XPath text functions
            r"contains\(text\(\),\s*['\"]([^'\"]+)['\"]",     # contains(text(), 'value')
            r"text\(\)\s*=\s*['\"]([^'\"]+)['\"]",            # text()='value'
            r"normalize-space\(text\(\)\)\s*=\s*['\"]([^'\"]+)['\"]",  # normalize-space(text())='value'
        
            # XPath attribute contains functions
            r"contains\(@text,\s*['\"]([^'\"]+)['\"]",        # contains(@text, 'value')
            r"contains\(@label,\s*['\"]([^'\"]+)['\"]",       # contains(@label, 'value')
            r"contains\(@name,\s*['\"]([^'\"]+)['\"]",        # contains(@name, 'value')
            r"contains\(@class,\s*['\"]([^'\"]+)['\"]",       # contains(@class, 'value')
            r"contains\(@id,\s*['\"]([^'\"]+)['\"]",          # contains(@id, 'value')
            r"contains\(@data-test,\s*['\"]([^'\"]+)['\"]",   # contains(@data-test, 'value')
            r"contains\(@placeholder,\s*['\"]([^'\"]+)['\"]", # contains(@placeholder, 'value')
        
            # Generic quoted text (fallback)
            r"'([^']+)'",                                     # Any single-quoted text
            r'"([^"]+)"'                                      # Any double-quoted text
        ]

    # STEP 3: Try each pattern and return the first meaningful match
        for i, pattern in enumerate(patterns):
            matches = re.findall(pattern, value, re.IGNORECASE)
            print(f"📋 Pattern {i+1} ({pattern[:50]}...): {matches}")
    
            # Return the first non-empty, meaningful match
            for match in matches:
                clean_match = match.strip()
                if clean_match and len(clean_match) > 0:
                    # Filter out obviously non-meaningful matches
                    if not self._is_meaningful_text(clean_match):
                        continue
                    
                    print(f"✅ Pattern {i+1} extracted meaningful text: '{clean_match}'")
                    return clean_match

        # STEP 4: If no pattern worked, try intelligent parsing
        intelligent_result = self._intelligent_text_parsing(value)
        if intelligent_result != value:
            print(f"✅ Intelligent parsing extracted: '{intelligent_result}'")
            return intelligent_result

        print(f"❌ No extraction worked, using original value: '{value}'")
        return value

    def _is_meaningful_text(self, text: str) -> bool:
        """Check if extracted text is meaningful (not just technical IDs)."""
        text_lower = text.lower()
    
        # Filter out obviously technical/non-meaningful values
        technical_patterns = [
            r'^[a-f0-9]{8,}$',          # Long hex strings
            r'^[0-9]{8,}$',             # Long numeric IDs
            r'^[a-z0-9_-]{20,}$',       # Long technical identifiers
            r'^\w+\.\w+\.\w+',          # Package-like names (com.example.app)
        ]
    
        for pattern in technical_patterns:
            if re.match(pattern, text_lower):
                return False
    
        # Consider it meaningful if it contains common UI words
        meaningful_keywords = [
            'username', 'password', 'login', 'email', 'submit', 'button',
            'menu', 'logout', 'sign', 'user', 'pass', 'name', 'text',
            'search', 'click', 'tap', 'press', 'next', 'back', 'home',
            'settings', 'profile', 'account', 'continue', 'cancel', 'ok'
        ]
    
        return any(keyword in text_lower for keyword in meaningful_keywords) or len(text) <= 15

    def _intelligent_text_parsing(self, value: str) -> str:
        """Last resort: intelligent parsing of complex XPath or selectors."""
        import re
    
        # Try to extract the most meaningful part from complex expressions
    
        # 1. If it's a complex XPath, try to get the most specific part
        if '//' in value and '[' in value:
            # Extract text from the most specific selector part
            parts = value.split('//')[-1]  # Get the last part after //
            if '[' in parts:
                # Try to extract meaningful text from conditions
                condition_text = re.search(r'\[([^\]]+)\]', parts)
                if condition_text:
                    return self._extract_text_from_xpath_or_value(condition_text.group(1))
    
        # 2. If it contains equals signs, extract the value part
        if '=' in value:
            parts = value.split('=')
            if len(parts) >= 2:
                potential_value = parts[-1].strip().strip('\'"')
                if self._is_meaningful_text(potential_value):
                    return potential_value
    
        # 3. Extract words that look like UI elements
        words = re.findall(r'\b[a-zA-Z]{3,}\b', value)
        meaningful_words = [word for word in words if self._is_meaningful_text(word)]
    
        if meaningful_words:
            return meaningful_words[0]  # Return the first meaningful word
    
        return value  # Return original if nothing else works
    
    async def _get_page_fingerprint(self) -> Dict[str, Any]:
        """Get a generic fingerprint of the current page state."""
        try:
            result = await self.call_tool("appium_get_page_source", {"full": False})
            parsed_result = self.parse_tool_result(result)
        
            if parsed_result.get('status') == 'success':
                page_source = parsed_result.get('page_source', '')
            
                # Generic page fingerprint - not specific to any site
                fingerprint = {
                    'source_length': len(page_source),
                    'source_hash': hash(page_source),  # Simple content hash
                    'element_count': self._count_elements(page_source),
                    'form_count': page_source.lower().count('<form'),
                    'button_count': page_source.lower().count('<button') + page_source.lower().count('type="submit"'),
                    'link_count': page_source.lower().count('<a href'),
                    'input_count': page_source.lower().count('<input'),
                    'title': self._extract_title(page_source),
                    'has_forms': '<form' in page_source.lower(),
                    'has_navigation': any(nav in page_source.lower() for nav in ['nav', 'menu', 'header']),
                    'unique_ids': self._extract_unique_ids(page_source),
                    'unique_classes': self._extract_unique_classes(page_source),
                    'text_snippets': self._extract_text_snippets(page_source)
                }
            
                print(f"📊 Page fingerprint: elements={fingerprint['element_count']}, hash={abs(fingerprint['source_hash']) % 10000}")
                return fingerprint
        
        except Exception as e:
            print(f"⚠️ Error getting page fingerprint: {e}")
    
        return {}
    
    def _count_elements(self, page_source: str) -> int:
        """Count total HTML elements in page."""
        import re
        # Count opening tags
        tags = re.findall(r'<[^/!][^>]*>', page_source)
        return len(tags)

    def _extract_unique_ids(self, page_source: str) -> List[str]:
        """Extract unique element IDs from page."""
        import re
        ids = re.findall(r'id=["\']([^"\']+)["\']', page_source, re.IGNORECASE)
        return list(set(ids))[:10]  # Limit to first 10 unique IDs

    def _extract_unique_classes(self, page_source: str) -> List[str]:
        """Extract unique CSS classes from page."""
        import re
        classes = re.findall(r'class=["\']([^"\']+)["\']', page_source, re.IGNORECASE)
        all_classes = []
        for class_attr in classes:
            all_classes.extend(class_attr.split())
        return list(set(all_classes))[:10]  # Limit to first 10 unique classes
    
    def _extract_text_snippets(self, page_source: str) -> List[str]:
        """Extract meaningful text snippets from page."""
        import re
        # Remove scripts and styles
        clean_source = re.sub(r'<script[^>]*>.*?</script>', '', page_source, flags=re.DOTALL)
        clean_source = re.sub(r'<style[^>]*>.*?</style>', '', clean_source, flags=re.DOTALL)
    
        # Extract text content
        text_content = re.sub(r'<[^>]+>', ' ', clean_source)
        words = text_content.split()
    
        # Get meaningful words (longer than 2 chars, not all numbers)
        meaningful_words = [w for w in words if len(w) > 2 and not w.isdigit() and w.isalnum()]
        return meaningful_words[:20]  # Limit to first 20 words

    def _extract_title(self, page_source: str) -> str:
        """Extract page title."""
        import re
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', page_source, re.IGNORECASE)
        return title_match.group(1).strip() if title_match else ""

    def _did_page_change(self, before: Dict, after: Dict) -> bool:
        """Generic method to detect if page changed meaningfully."""
    
        if not before or not after:
            print("⚠️ Missing fingerprint data")
            return False
    
        # Check 1: Content hash changed significantly
        if before.get('source_hash') != after.get('source_hash'):
            print("🎯 Page content hash changed!")
            return True
    
        # Check 2: Element count changed significantly (>10% change)
        before_count = before.get('element_count', 0)
        after_count = after.get('element_count', 0)
    
        if before_count > 0:
            change_percent = abs(before_count - after_count) / before_count
            if change_percent > 0.1:  # 10% change in element count
                print(f"🎯 Element count changed significantly: {before_count} → {after_count}")
                return True
    
        # Check 3: Page title changed
        if before.get('title') != after.get('title'):
            print(f"🎯 Page title changed: '{before.get('title')}' → '{after.get('title')}'")
            return True
    
        # Check 4: Form count changed (forms appeared/disappeared)
        if before.get('form_count') != after.get('form_count'):
            print(f"🎯 Form count changed: {before.get('form_count')} → {after.get('form_count')}")
            return True
    
        # Check 5: Button count changed significantly
        before_buttons = before.get('button_count', 0)
        after_buttons = after.get('button_count', 0)
        if abs(before_buttons - after_buttons) > 2:  # More than 2 buttons difference
            print(f"🎯 Button count changed: {before_buttons} → {after_buttons}")
            return True
    
        # Check 6: Unique IDs changed
        before_ids = set(before.get('unique_ids', []))
        after_ids = set(after.get('unique_ids', []))
        new_ids = after_ids - before_ids
        removed_ids = before_ids - after_ids
    
        if len(new_ids) > 2 or len(removed_ids) > 2:
            print(f"🎯 Significant ID changes: +{len(new_ids)} -{len(removed_ids)}")
            return True
    
        # Check 7: Text content changed significantly
        before_text = set(before.get('text_snippets', []))
        after_text = set(after.get('text_snippets', []))
        text_changes = len(before_text.symmetric_difference(after_text))
    
        if text_changes > 5:  # More than 5 text snippets changed
            print(f"🎯 Significant text changes: {text_changes} snippets different")
            return True
    
        print("⚠️ No significant page changes detected")
        return False
    

    async def _try_alternative_tap_methods(self, element_id: str, original_fingerprint: Dict) -> Dict[str, Any]:
        """Try alternative tap methods - completely generic."""
    
        print("🔄 Trying alternative tap methods...")
    
        # Method 1: JavaScript click (for web contexts)
        if await self._is_web_context():
            print("🌐 Trying JavaScript-based alternatives...")
            js_result = await self._try_javascript_alternatives(element_id)
            if js_result.get('status') == 'success':
                # Verify it worked
                new_fingerprint = await self._get_page_fingerprint()
                if self._did_page_change(original_fingerprint, new_fingerprint):
                    return js_result
    
        # Method 2: Double tap
        print("🔄 Trying double tap...")
        try:
            await self.call_tool("appium_tap_element", {"element_id": element_id})
            await asyncio.sleep(0.5)
            result = await self.call_tool("appium_tap_element", {"element_id": element_id})
            parsed_result = self.parse_tool_result(result)
        
            if parsed_result.get('status') == 'success':
                await asyncio.sleep(2)
                new_fingerprint = await self._get_page_fingerprint()
                if self._did_page_change(original_fingerprint, new_fingerprint):
                    return {"status": "success", "message": "Double tap successful"}
        except Exception as e:
            print(f"⚠️ Double tap failed: {e}")
    
        # Method 3: Scroll and tap
        print("🔄 Trying scroll and tap...")
        try:
            await self.call_tool("appium_scroll", {"direction": "up"})
            await asyncio.sleep(1)
            result = await self.call_tool("appium_tap_element", {"element_id": element_id})
            parsed_result = self.parse_tool_result(result)
        
            if parsed_result.get('status') == 'success':
                await asyncio.sleep(2)
                new_fingerprint = await self._get_page_fingerprint()
                if self._did_page_change(original_fingerprint, new_fingerprint):
                    return {"status": "success", "message": "Scroll and tap successful"}
        except Exception as e:
            print(f"⚠️ Scroll and tap failed: {e}")
    
        # Method 4: Try finding similar elements
        print("🔄 Trying to find alternative elements...")
        try:
            alt_result = await self._find_and_tap_alternatives(element_id)
            if alt_result.get('status') == 'success':
                new_fingerprint = await self._get_page_fingerprint()
                if self._did_page_change(original_fingerprint, new_fingerprint):
                    return alt_result
        except Exception as e:
            print(f"⚠️ Alternative element search failed: {e}")
    
        return {"status": "error", "message": "All alternative tap methods failed"}
    
    async def _try_javascript_alternatives(self, element_id: str) -> Dict[str, Any]:
        """Try JavaScript alternatives - uses the generic method we created earlier."""
        return await self._try_javascript_click(element_id)

    async def _find_and_tap_alternatives(self, element_id: str) -> Dict[str, Any]:
        """Try to find alternative elements that might work better."""
    
        # Get element info to find similar elements
        element_info = await self._get_element_info(element_id)
    
        if element_info.get("text"):
            # Try to find other elements with same text
            text = element_info["text"]
            alternative_strategies = [
                ("xpath", f"//*[text()='{text}']"),
                ("xpath", f"//*[contains(text(), '{text}')]"),
                ("xpath", f"//button[text()='{text}']"),
                ("xpath", f"//a[text()='{text}']"),
            ]
        
            for strategy, value in alternative_strategies:
                try:
                    result = await self.call_tool("appium_find_element", {
                        "strategy": strategy,
                        "value": value
                    })
                    parsed_result = self.parse_tool_result(result)
                
                    if parsed_result.get('status') == 'success':
                        alt_element_id = parsed_result.get('element_id')
                        if alt_element_id != element_id:  # Different element
                            print(f"🔄 Trying alternative element: {alt_element_id}")
                            tap_result = await self.call_tool("appium_tap_element", {
                                "element_id": alt_element_id
                            })
                            tap_parsed = self.parse_tool_result(tap_result)
                        
                            if tap_parsed.get('status') == 'success':
                                return {"status": "success", "message": f"Alternative element tap successful via {strategy}"}
                except:
                    continue
    
        return {"status": "error", "message": "No alternative elements found"}
   
