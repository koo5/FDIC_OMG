#!/usr/bin/env python3
"""
Playwright test for rdftab table viewer functionality.
Tests navigation from table cells to column definitions to annotations.
"""
import asyncio
import subprocess
import time
from pathlib import Path
import sys
import os

# Add parent directory to path to import fdic_omg modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright, expect

class TestRdftabViewer:
    """Test the rdftab viewer functionality"""
    
    def __init__(self):
        self.test_port = 8765
        self.server_process = None
        self.output_dir = None
        
    async def setup(self):
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
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"csv2rdf failed: {result.stderr}")
            raise RuntimeError("Failed to generate test data")
            
        self.output_dir = Path("test_rdftab_output")
        
        # Start server in background
        print(f"Starting server on port {self.test_port}...")
        self.server_process = subprocess.Popen([
            sys.executable, "-m", "http.server", str(self.test_port)
        ], cwd=self.output_dir / "viewer")
        
        # Give server time to start
        time.sleep(2)
        
    async def teardown(self):
        """Clean up server and test data"""
        print("Cleaning up...")
        if self.server_process:
            self.server_process.terminate()
            self.server_process.wait()
            
        # Clean up test output
        if self.output_dir and self.output_dir.exists():
            import shutil
            shutil.rmtree(self.output_dir)
            
    async def test_table_viewer_navigation(self):
        """Test navigation from table to column to annotation"""
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Navigate to viewer
            viewer_url = f"http://localhost:{self.test_port}/index-viewer.html"
            print(f"Navigating to {viewer_url}")
            await page.goto(viewer_url)
            
            # Wait for table to load
            print("Waiting for table to load...")
            await page.wait_for_selector('table', timeout=10000)
            
            # Verify table has data
            rows = await page.query_selector_all('tbody tr')
            assert len(rows) > 0, "Table should have data rows"
            print(f"✓ Table loaded with {len(rows)} rows")
            
            # Test 1: Click on a cell to show metadata modal
            print("\nTest 1: Clicking on a table cell...")
            
            # Find a clickable cell (they have class 'clickable')
            clickable_cell = await page.query_selector('td.clickable')
            assert clickable_cell, "Should have clickable cells"
            
            cell_text = await clickable_cell.text_content()
            print(f"Clicking on cell with text: {cell_text}")
            
            # Click the cell
            await clickable_cell.click()
            
            # Wait for modal to appear
            await page.wait_for_selector('.modal-content', timeout=5000)
            print("✓ Modal opened")
            
            # Verify modal shows quads
            quads = await page.query_selector_all('.quad')
            assert len(quads) > 0, "Modal should show RDF quads"
            print(f"✓ Modal shows {len(quads)} quads")
            
            # Test 2: Find and click on column definition link
            print("\nTest 2: Finding column definition link...")
            
            # Look for a quad that references the column (contains /column/ in href)
            column_link = None
            links = await page.query_selector_all('.quad a')
            
            for link in links:
                href = await link.get_attribute('href')
                if href and '/column/' in href:
                    column_link = link
                    break
                    
            assert column_link, "Should find a link to column definition"
            
            column_href = await column_link.get_attribute('href')
            print(f"Found column link: {column_href}")
            
            # Click on column definition link
            await column_link.click()
            
            # Wait for navigation/update
            await page.wait_for_timeout(1000)
            
            # Verify we're now viewing column metadata
            await page.wait_for_selector('.node-header', timeout=5000)
            node_header = await page.query_selector('.node-header')
            header_text = await node_header.text_content()
            assert '/column/' in header_text, "Should be viewing column definition"
            print(f"✓ Navigated to column: {header_text}")
            
            # Test 3: Find annotation link from column
            print("\nTest 3: Finding annotation link from column...")
            
            # Look for hasAnnotation property
            annotation_link = None
            props = await page.query_selector_all('.property')
            
            for prop in props:
                prop_text = await prop.text_content()
                if 'hasAnnotation' in prop_text:
                    # Find the link in this property
                    links = await prop.query_selector_all('a')
                    if links:
                        annotation_link = links[-1]  # Object is usually last
                        break
                        
            assert annotation_link, "Column should have annotation link"
            
            annotation_href = await annotation_link.get_attribute('href')
            print(f"Found annotation link: {annotation_href}")
            
            # Click on annotation link
            await annotation_link.click()
            
            # Wait for navigation
            await page.wait_for_timeout(1000)
            
            # Verify we're viewing annotation
            await page.wait_for_selector('.node-header', timeout=5000)
            node_header = await page.query_selector('.node-header')
            header_text = await node_header.text_content()
            assert 'annotation' in header_text.lower(), "Should be viewing annotation"
            print(f"✓ Navigated to annotation: {header_text}")
            
            # Test 4: Verify annotation has seeAlso links
            print("\nTest 4: Checking for seeAlso links...")
            
            # Look for rdfs:seeAlso properties
            seealso_found = False
            props = await page.query_selector_all('.property')
            
            for prop in props:
                prop_text = await prop.text_content()
                if 'seeAlso' in prop_text:
                    seealso_found = True
                    # Find links in this property
                    links = await prop.query_selector_all('a')
                    if links:
                        link_href = await links[-1].get_attribute('href')
                        print(f"  Found seeAlso link: {link_href}")
                        
            assert seealso_found, "Annotation should have seeAlso properties"
            print("✓ Annotation has seeAlso properties")
            
            # Test 5: Test column info icons in table header
            print("\nTest 5: Testing column info icons...")
            
            # Close modal first
            close_btn = await page.query_selector('.modal-close')
            if close_btn:
                await close_btn.click()
                await page.wait_for_timeout(500)
            
            # Find info icon in table header
            info_icon = await page.query_selector('th .info-icon')
            assert info_icon, "Table headers should have info icons"
            
            # Click info icon
            await info_icon.click()
            
            # Wait for modal
            await page.wait_for_selector('.modal-content', timeout=5000)
            
            # Verify it shows column metadata
            modal_content = await page.query_selector('.modal-content')
            modal_text = await modal_content.text_content()
            assert 'columnName' in modal_text or 'Column' in modal_text, "Should show column metadata"
            print("✓ Column info icon shows metadata")
            
            # Close browser
            await browser.close()
            
            print("\n✅ All tests passed!")
            
    async def run_tests(self):
        """Run all tests"""
        try:
            await self.setup()
            await self.test_table_viewer_navigation()
        finally:
            await self.teardown()


async def main():
    """Main test runner"""
    tester = TestRdftabViewer()
    await tester.run_tests()


if __name__ == "__main__":
    # Change to FDIC_OMG directory for correct paths
    os.chdir(Path(__file__).parent.parent)
    asyncio.run(main())