#!/usr/bin/env python3
"""Manual test to open the viewer in a browser"""
import subprocess
import webbrowser
import time
from pathlib import Path

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
    "python", "-m", "http.server", "8888",
    "-d", "test_viewer_output/viewer"
])

time.sleep(2)

# Open browser
url = "http://localhost:8888/index.html"
print(f"Opening {url} in browser...")
webbrowser.open(url)

print("\nViewer should be open in your browser.")
print("Press Ctrl+C to stop the server.")

try:
    server.wait()
except KeyboardInterrupt:
    print("\nStopping server...")
    server.terminate()