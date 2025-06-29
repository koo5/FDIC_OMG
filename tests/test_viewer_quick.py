#!/usr/bin/env python3
"""
Quick test to generate data and print URL for manual testing
"""
import subprocess
import sys
from pathlib import Path

# Generate test data
print("Generating test data...")
result = subprocess.run([
    sys.executable, "-m", "fdic_omg.csv2rdf",
    "/d/sync/jj/fdic_omg/FDIC_Insured_Banks.csv",
    "--annotations", "fdic_omg/annotations/fdic_banks.ttl",
    "--max-rows", "10",
    "--output-dir", "test_quick",
    "--server", "--port", "8889"
], capture_output=True, text=True)

if result.returncode != 0:
    print(f"Error: {result.stderr}")
else:
    print("✓ Test viewer is now running at: http://localhost:8889/index-viewer.html")
    print("\nTo test:")
    print("1. Open the URL in a browser")
    print("2. Click on any cell to see row metadata")
    print("3. In the modal, look for properties with URIs (they should be clickable)")
    print("4. Click on a column URI to navigate to column metadata")
    print("5. Look for 'hasAnnotation' property and click to see annotation")
    print("\nPress Ctrl+C to stop the server")