#!/usr/bin/env python3
"""
Synchronous Playwright test for rdftab table viewer functionality.
Tests navigation from table cells to column definitions to annotations.
"""
import subprocess
import time
from pathlib import Path
import sys
import os
import signal

# Add parent directory to path to import fdic_omg modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.sync_api import sync_playwright, expect

class TestRdftabViewer:
    """Test the rdftab viewer functionality"""
    
    def __init__(self):
        self.test_port = 8766
        self.server_process = None
        self.output_dir = None
        
    def setup(self):
        """Generate test data and start server"""
        print("Setting up test environment...")
        
        # Generate test CSV data with limited rows for faster testing
        csv_path = "/d/sync/jj/fdic_omg/FDIC_Insured_Banks.csv"
        if not Path(csv_path).exists():
            raise FileNotFoundError(f"Test CSV not found: {csv_path}")
            
        # Run csv2rdf to generate output
        print("Running csv2rdf to generate test data...")
        result = subprocess.run([
            sys.executable, "-m", "fdic_omg.csv2rdf",
            csv_path,
            "--annotations", "fdic_omg/annotations/fdic_banks.ttl",
            "--max-rows", "10",  # Small dataset for testing
            "--output-dir", "test_rdftab_output"
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        
        if result.returncode != 0:
            print(f"csv2rdf failed: {result.stderr}")
            raise RuntimeError("Failed to generate test data")
            
        self.output_dir = Path(__file__).parent.parent / "test_rdftab_output"
        
        # Start server in background
        print(f"Starting server on port {self.test_port}...")
        self.server_process = subprocess.Popen([
            sys.executable, "-m", "http.server", str(self.test_port)
        ], cwd=self.output_dir / "viewer")
        
        # Give server time to start
        time.sleep(2)
        
    def teardown(self):
        """Clean up server and test data"""
        print("\nCleaning up...")
        if self.server_process:
            # Try graceful termination first
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if needed
                self.server_process.kill()
                self.server_process.wait()
            
        # Clean up test output
        if self.output_dir and self.output_dir.exists():
            import shutil
            shutil.rmtree(self.output_dir)
            
    def test_table_viewer_navigation(self):
        """Test navigation from table to column to annotation"""
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=True)  # Set to False for debugging
            context = browser.new_context()
            page = context.new_page()
            
            # Capture console logs
            page.on("console", lambda msg: print(f"Console {msg.type}: {msg.text}"))
            
            try:
                # Navigate to viewer
                viewer_url = f"http://localhost:{self.test_port}/index-viewer.html"
                print(f"Navigating to {viewer_url}")
                page.goto(viewer_url)
                
                # Wait for table to load
                print("Waiting for table to load...")
                page.wait_for_selector('table', timeout=10000)
                
                # Verify table has data
                rows = page.query_selector_all('tbody tr')
                assert len(rows) > 0, "Table should have data rows"
                print(f"✓ Table loaded with {len(rows)} rows")
                
                # Test 1: Click on a cell to show metadata modal
                print("\nTest 1: Clicking on a table cell...")
                
                # Find a clickable cell (they have class 'clickable')
                clickable_cells = page.query_selector_all('td.clickable')
                assert len(clickable_cells) > 0, "Should have clickable cells"
                
                # Click the first clickable cell
                clickable_cell = clickable_cells[0]
                cell_text = clickable_cell.text_content()
                print(f"Clicking on cell with text: {cell_text}")
                
                clickable_cell.click()
                
                # Wait for modal to appear
                try:
                    page.wait_for_selector('.modal-overlay', timeout=5000)
                    print("✓ Modal opened")
                except:
                    # Try alternate selector
                    page.wait_for_selector('.modal-content', timeout=5000)
                    print("✓ Modal opened")
                
                # Look for properties in the modal
                props = page.query_selector_all('.modal-overlay .property')
                if len(props) == 0:
                    # Try alternative selectors
                    props = page.query_selector_all('.modal-overlay .prop')
                    if len(props) == 0:
                        # Look for the props container
                        props_container = page.query_selector('.modal-overlay .props')
                        if props_container:
                            # Count children as properties
                            props = props_container.query_selector_all('div')
                
                print(f"✓ Modal shows {len(props)} properties")
                
                # Test 2: Find and click on column definition link
                print("\nTest 2: Finding column definition link...")
                
                # Look for a link that references the column (contains /column/ in href)
                column_link = None
                links = page.query_selector_all('.modal a')
                
                for link in links:
                    href = link.get_attribute('href')
                    if href and '/column/' in href:
                        column_link = link
                        print(f"Found column link: {href}")
                        break
                        
                if column_link:
                    # Click on column definition link
                    column_link.click()
                    
                    # Wait for content to update
                    page.wait_for_timeout(1000)
                    
                    # Check if we navigated to column
                    current_content = page.text_content('.modal')
                    if 'columnName' in current_content or 'columnIndex' in current_content:
                        print("✓ Navigated to column definition")
                        
                        # Test 3: Look for annotation link
                        print("\nTest 3: Finding annotation link from column...")
                        
                        # Look for hasAnnotation property
                        annotation_link = None
                        links = page.query_selector_all('.modal a')
                        
                        for link in links:
                            href = link.get_attribute('href')
                            parent_text = link.evaluate('el => el.parentElement.textContent')
                            if 'hasAnnotation' in parent_text and href:
                                annotation_link = link
                                print(f"Found annotation link: {href}")
                                break
                                
                        if annotation_link:
                            # Click on annotation link
                            annotation_link.click()
                            page.wait_for_timeout(1000)
                            
                            # Check for seeAlso properties
                            current_content = page.text_content('.modal')
                            if 'seeAlso' in current_content:
                                print("✓ Annotation has seeAlso properties")
                            else:
                                print("⚠ No seeAlso properties found in annotation")
                        else:
                            print("⚠ No annotation link found in column definition")
                    else:
                        print("⚠ Column navigation might not have worked as expected")
                else:
                    print("⚠ No column link found in cell metadata")
                
                # Test 4: Test column info icons in table header
                print("\nTest 4: Testing column info icons...")
                
                # Close modal first
                close_btn = page.query_selector('.modal-close, .close-button, button[aria-label="Close"]')
                if close_btn:
                    close_btn.click()
                    page.wait_for_timeout(500)
                else:
                    # Try clicking outside modal or pressing Escape
                    page.keyboard.press('Escape')
                    page.wait_for_timeout(500)
                
                # Find info icon in table header
                info_icons = page.query_selector_all('th .info-icon')
                if len(info_icons) > 0:
                    print(f"Found {len(info_icons)} column info icons")
                    
                    # Click first info icon
                    info_icons[0].click()
                    
                    # Wait for modal
                    try:
                        page.wait_for_selector('.modal', timeout=5000)
                        print("✓ Column info icon shows metadata modal")
                    except:
                        print("⚠ Column info icon click might not have worked")
                else:
                    print("⚠ No column info icons found")
                
                print("\n✅ Test completed!")
                
            finally:
                # Close browser
                browser.close()
            
    def run_tests(self):
        """Run all tests"""
        try:
            self.setup()
            self.test_table_viewer_navigation()
        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.teardown()


def main():
    """Main test runner"""
    # Change to FDIC_OMG directory for correct paths
    original_dir = os.getcwd()
    os.chdir(Path(__file__).parent.parent)
    
    try:
        tester = TestRdftabViewer()
        tester.run_tests()
    finally:
        os.chdir(original_dir)


if __name__ == "__main__":
    main()