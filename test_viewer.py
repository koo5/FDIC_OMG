#!/usr/bin/env python3
"""
Playwright tests for FDIC viewer with console message capture
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import subprocess
import time
import signal
import sys


class ViewerTest:
    def __init__(self):
        self.server_process = None
        self.port = 9001  # Different port
        
    def find_free_port(self):
        """Find a free port"""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
        
    async def setup(self):
        """Generate test data and start server"""
        print("Generating test data...")
        subprocess.run([
            sys.executable, "-m", "fdic_omg.cli",
            "example/example1.csv",
            "--output-dir", "test_viewer_output"
        ], check=True)
        
        # Find a free port
        self.port = self.find_free_port()
        
        print(f"Starting server on port {self.port}...")
        self.server_process = subprocess.Popen([
            sys.executable, "-m", "http.server", str(self.port)
        ], cwd="test_viewer_output/viewer")
        
        # Wait for server to start
        time.sleep(2)
        
    def teardown(self):
        """Stop the server"""
        if self.server_process:
            print("Stopping server...")
            self.server_process.terminate()
            self.server_process.wait()
            
    async def test_viewer(self):
        """Test the viewer and capture console messages"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Collect all console messages
            console_messages = []
            console_errors = []
            
            # Capture console messages
            page.on("console", lambda msg: self._handle_console(msg, console_messages, console_errors))
            
            # Capture page errors
            page.on("pageerror", lambda error: console_errors.append(f"PAGE ERROR: {error}"))
            
            # Also capture uncaught exceptions
            await page.evaluate("""
                window.addEventListener('error', (e) => {
                    console.error('Uncaught error:', e.message, 'at', e.filename, ':', e.lineno, ':', e.colno);
                    if (e.error && e.error.stack) {
                        console.error('Stack:', e.error.stack);
                    }
                });
            """)
            
            # Navigate to viewer
            url = f"http://localhost:{self.port}/index-viewer.html"
            print(f"Navigating to {url}")
            await page.goto(url)
            
            # Wait for page to fully load
            await page.wait_for_load_state("networkidle")
            
            # Print any early console messages/errors
            if console_errors:
                print("\n=== Early Console Errors ===")
                for err in console_errors:
                    print(f"ERROR: {err}")
            
            # Check what's on the page
            body_text = await page.inner_text("body")
            print(f"Page body text: {body_text[:200]}...")
            
            # Check if there are any error messages
            error_msgs = await page.query_selector_all(".error")
            if error_msgs:
                for msg in error_msgs:
                    text = await msg.inner_text()
                    print(f"Error on page: {text}")
            
            # Wait for table to load
            print("Waiting for table to appear...")
            try:
                await page.wait_for_selector("table", timeout=5000)
            except:
                # If table doesn't appear, check what elements are present
                print("Table did not appear. Checking page structure...")
                elements = await page.query_selector_all("*")
                print(f"Total elements on page: {len(elements)}")
                
                # Check for specific Vue app elements
                app_el = await page.query_selector("#app")
                if app_el:
                    app_html = await app_el.inner_html()
                    print(f"App element HTML: {app_html[:200]}...")
                    
                # Take screenshot for debugging
                await page.screenshot(path="viewer_debug.png")
                print("Debug screenshot saved to viewer_debug.png")
                raise
            
            # Give time for metadata to load
            await page.wait_for_timeout(2000)
            
            # Check if table_metadata.ttl was requested
            print("\nChecking metadata loading...")
            metadata_loaded = False
            for msg in console_messages:
                if 'table metadata' in msg.lower():
                    print(f"  Metadata message: {msg}")
                    metadata_loaded = True
            
            # Also check network requests
            print("  Checking for table_metadata.ttl request...")
            
            # Test 1: Check if table is displayed
            table = await page.query_selector("table")
            assert table is not None, "Table should be visible"
            print("✓ Table is displayed")
            
            # Test 2: Click on a cell
            print("Clicking on first cell...")
            first_cell = await page.query_selector("tbody tr:first-child td:first-child")
            if first_cell:
                await first_cell.click()
                # Wait a bit for modal to appear
                await page.wait_for_timeout(1000)
                
                # Check if modal appeared
                modal = await page.query_selector(".modal-overlay")
                if modal:
                    print("✓ Modal appeared after clicking cell")
                    
                    # Check if RDF properties are shown
                    properties = await page.query_selector_all(".modal-content table tr")
                    print(f"  Found {len(properties)} properties displayed")
                    
                    # Test 2a: Click on column property expansion
                    print("\nTesting column property expansion...")
                    
                    # Find the fdic:inColumn property row
                    column_prop_found = False
                    for prop_row in properties:
                        prop_text = await prop_row.inner_text()
                        if 'inColumn' in prop_text:
                            print(f"  Found column property: {prop_text}")
                            column_prop_found = True
                            
                            # Find the expand button in this row - look in the value cell
                            value_cell = await prop_row.query_selector("td:nth-child(2)")
                            if value_cell:
                                # Get all buttons and select the one with '+' text
                                buttons = await value_cell.query_selector_all("button")
                                expand_btn = None
                                for btn in buttons:
                                    btn_text = await btn.inner_text()
                                    if '+' in btn_text:
                                        expand_btn = btn
                                        break
                            else:
                                expand_btn = None
                                
                            if expand_btn:
                                btn_text = await expand_btn.inner_text()
                                print(f"  Found expand button with text: '{btn_text}'")
                                
                                # Debug: Check parent structure
                                parent_html = await value_cell.inner_html()
                                print(f"  Value cell HTML: {parent_html[:200]}...")
                                
                                # Click expand button
                                print(f"  Clicking expand button...")
                                
                                # Check current state before click
                                btn_classes_before = await expand_btn.get_attribute("class")
                                print(f"  Button classes before: {btn_classes_before}")
                                
                                await expand_btn.click()
                                await page.wait_for_timeout(500)
                                
                                # Check console for the "expanded:" log
                                console_logs = [msg for msg in console_messages if "expanded:" in msg]
                                if console_logs:
                                    print(f"  Console log: {console_logs[-1]}")
                                
                                await page.wait_for_timeout(1500)
                                
                                # Check for loadNodeDataAll console logs
                                load_logs = [msg for msg in console_messages if "loadNodeDataAll" in msg]
                                if load_logs:
                                    print(f"  Load logs found: {len(load_logs)}")
                                    for log in load_logs[-3:]:  # Show last 3
                                        print(f"    {log[:100]}...")
                                
                                # Check if button state changed
                                btn_classes_after = await expand_btn.get_attribute("class")
                                print(f"  Button classes after: {btn_classes_after}")
                                
                                # Look for expanded content in various ways
                                # 1. Check if TermExpandable component rendered an expanded view
                                expanded_term = await value_cell.query_selector(".term-expandable.expanded")
                                if expanded_term:
                                    print("✓ TermExpandable component expanded")
                                
                                # 2. Check for nested node-outer  
                                # Get the full HTML to see what's rendered
                                value_cell_html_after = await value_cell.inner_html()
                                if "node-outer" in value_cell_html_after:
                                    print("  Found 'node-outer' in HTML after expansion")
                                else:
                                    # Print part of the HTML to debug
                                    print(f"  Value cell HTML after click: {value_cell_html_after[:300]}...")
                                    if "<!---->" in value_cell_html_after:
                                        print("  Found Vue comments (<!---->), component may not be rendering")
                                
                                # Check different selectors for the expanded content
                                expanded_selectors = [
                                    "table",  # Node component renders a table
                                    ".expanded table",
                                    "div table",
                                    ".expandable.expanded table"
                                ]
                                
                                nested_node = None
                                for selector in expanded_selectors:
                                    nested_node = await value_cell.query_selector(selector)
                                    if nested_node:
                                        print(f"✓ Found nested node with selector: {selector}")
                                        break
                                
                                if nested_node:
                                    nested_props = await nested_node.query_selector_all(".property")
                                    print(f"  Found {len(nested_props)} properties in expanded column node")
                                    for prop in nested_props[:3]:  # Show first 3
                                        prop_text = await prop.inner_text()
                                        print(f"    - {prop_text}")
                                
                                # 3. Check if the expand button text changed
                                btn_text_after = await expand_btn.inner_text()
                                if btn_text_after != btn_text:
                                    print(f"  Button text changed from '{btn_text}' to '{btn_text_after}'")
                                
                                # 4. Count total node-outers on page
                                all_node_outers = await page.query_selector_all(".node-outer")
                                print(f"  Total node-outers on page: {len(all_node_outers)}")
                                
                                # Final determination
                                if nested_node or expanded_term or len(all_node_outers) > 1:
                                    print("✓ Column properties expanded successfully")
                                else:
                                    print("✗ Column properties did not expand")
                            else:
                                print("✗ No expand button found for column property")
                            break
                    
                    if not column_prop_found:
                        print("✗ Column property (fdic:inColumn) not found in cell metadata")
                    
                    # Close modal
                    close_btn = await page.query_selector(".close-button")
                    if close_btn:
                        await close_btn.click()
                        await page.wait_for_timeout(1000)  # Wait longer for modal to close
                else:
                    print("✗ Modal did not appear")
            
            # Test 3: Click on column header
            print("Clicking on column header...")
            
            # First check if headers have click handlers
            headers = await page.query_selector_all("th")
            print(f"  Found {len(headers)} column headers")
            
            # Check for info icon in header
            info_icons = await page.query_selector_all("th .info-icon")
            print(f"  Found {len(info_icons)} info icons in headers")
            
            if info_icons:
                # Click info icon
                print("  Clicking info icon...")
                await info_icons[0].click()
                await page.wait_for_timeout(3000)  # Wait longer
                
                # Try to wait for modal specifically
                try:
                    await page.wait_for_selector(".modal-overlay", timeout=2000)
                    print("  Modal appeared!")
                except:
                    print("  Modal did not appear within timeout")
            else:
                # Try clicking header text directly
                header = await page.query_selector("th:first-child")
                if header:
                    print("  Clicking header directly...")
                    await header.click()
                    await page.wait_for_timeout(1000)
                
            # Check if modal appeared for column
            modal = await page.query_selector(".modal-overlay")
            if modal:
                print("✓ Modal appeared after clicking column header")
                
                # Check content
                modal_content = await modal.inner_text()
                print(f"  Modal content preview: {modal_content[:200]}...")
                
                # Get the first property row HTML to see what's being rendered
                first_prop_row = await modal.query_selector("table tbody tr:first-child")
                if first_prop_row:
                    prop_html = await first_prop_row.inner_html()
                    print(f"  First property row HTML: {prop_html[:500]}...")
                
                # Check for RDF properties in modal
                props_in_modal = await modal.query_selector_all("table tr")
                if props_in_modal:
                    print(f"  Found {len(props_in_modal)} properties in modal")
                
                # Close modal
                close_btn = await page.query_selector(".close-button")
                if close_btn:
                    await close_btn.click()
            else:
                print("✗ Modal did not appear for column")
                
                # Debug: check console for errors when clicking
                print("  Checking for click handler errors...")
            
            # Print all console messages
            print("\n=== Console Messages ===")
            for msg in console_messages:
                print(msg)
                
            # Print all errors
            if console_errors:
                print("\n=== Console Errors ===")
                for error in console_errors:
                    print(f"ERROR: {error}")
            else:
                print("\n✓ No console errors detected")
            
            # Take screenshot for debugging
            await page.screenshot(path="viewer_test_screenshot.png")
            print("\nScreenshot saved to viewer_test_screenshot.png")
            
            await browser.close()
            
    def _handle_console(self, msg, messages, errors):
        """Handle console messages"""
        msg_type = msg.type
        text = msg.text
        
        # Format message with type
        formatted = f"[{msg_type.upper()}] {text}"
        
        # Add to appropriate list
        messages.append(formatted)
        if msg_type in ['error', 'warning']:
            errors.append(text)
            
        # Also get detailed error info if available
        if msg_type == 'error':
            # Try to get stack trace
            for arg in msg.args:
                try:
                    value = arg.json_value()
                    if value and isinstance(value, dict) and 'stack' in value:
                        errors.append(f"Stack trace: {value['stack']}")
                except:
                    pass

async def main():
    """Run the tests"""
    test = ViewerTest()
    
    try:
        await test.setup()
        await test.test_viewer()
    finally:
        test.teardown()

if __name__ == "__main__":
    asyncio.run(main())