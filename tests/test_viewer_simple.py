#!/usr/bin/env python3
"""
Simple test to verify rdftab viewer shows table and responds to clicks
"""
import subprocess
import time
from pathlib import Path
import sys

class SimpleViewerTest:
    def __init__(self):
        self.server_process = None
        
    def run(self):
        print("1. Generating test data...")
        result = subprocess.run([
            sys.executable, "-m", "fdic_omg.csv2rdf",
            "/d/sync/jj/fdic_omg/FDIC_Insured_Banks.csv",
            "--annotations", "fdic_omg/annotations/fdic_banks.ttl",
            "--max-rows", "5",
            "--output-dir", "test_simple"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            return False
            
        print("✓ Test data generated")
        
        # Start server
        print("2. Starting server...")
        self.server_process = subprocess.Popen([
            sys.executable, "-m", "http.server", "8888"
        ], cwd=Path("test_simple/viewer"))
        
        time.sleep(2)
        
        print("✓ Server started at http://localhost:8888/index-viewer.html")
        print("\n3. Manual verification steps:")
        print("   a) Open http://localhost:8888/index-viewer.html in a browser")
        print("   b) Verify you see a table with 5 rows of data")
        print("   c) Click on any cell - a modal should appear")
        print("   d) Click on a column header info icon - modal should show column metadata")
        print("\nPress Enter to stop the server...")
        
        input()
        
        # Cleanup
        if self.server_process:
            self.server_process.terminate()
            
        import shutil
        if Path("test_simple").exists():
            shutil.rmtree("test_simple")
            
        print("✓ Cleanup complete")
        return True

if __name__ == "__main__":
    tester = SimpleViewerTest()
    tester.run()