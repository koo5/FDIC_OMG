#!/usr/bin/env python3
"""Simple test to check viewer loading"""
import subprocess
import time
import urllib.request

# Generate test data
print("Generating test data...")
subprocess.run([
    "python", "-m", "fdic_omg.cli",
    "example/example1.csv",
    "--output-dir", "test_viewer_output"
], check=True)

# Start server
print("Starting server...")
server = subprocess.Popen([
    "python", "-m", "http.server", "8080",
    "-d", "test_viewer_output/viewer"
])

time.sleep(2)

try:
    # Check if server is running
    with urllib.request.urlopen("http://localhost:8080/index.html") as response:
        print(f"Server response: {response.status}")
    
    # Check manifest
    with urllib.request.urlopen("http://localhost:8080/manifest.json") as response:
        print(f"Manifest response: {response.status}")
        if response.status == 200:
            import json
            manifest = json.loads(response.read().decode())
            print("Manifest content:", json.dumps(manifest, indent=2))
    
    print("\nServer is running. Visit http://localhost:8080/index.html")
    print("Press Ctrl+C to stop.")
    server.wait()
    
except KeyboardInterrupt:
    print("\nStopping server...")
finally:
    server.terminate()