#!/usr/bin/env python3
"""
Simple HTTP Server for FDIC Viewer
Serves the generated viewer files with proper MIME types
"""

import os
import sys
import argparse
import webbrowser
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import quote


class ViewerHTTPRequestHandler(SimpleHTTPRequestHandler):
    """
    Custom HTTP request handler with proper MIME types for the viewer
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def end_headers(self):
        # Add CORS headers to allow cross-origin requests
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def guess_type(self, path):
        # Ensure proper MIME types for our files
        mime_type, encoding = super().guess_type(path)
        
        if path.endswith('.ttl'):
            return 'text/turtle', encoding
        elif path.endswith('.jsonld'):
            return 'application/ld+json', encoding
        elif path.endswith('.vue'):
            return 'text/plain', encoding
        
        return mime_type, encoding
    
    def log_message(self, format, *args):
        # Only log GET requests to reduce noise
        if 'GET' in format % args:
            super().log_message(format, *args)


def find_manifest_info(directory):
    """Find the manifest file and extract dataset info"""
    manifest_path = directory / "manifest.json"
    if manifest_path.exists():
        import json
        with open(manifest_path) as f:
            manifest = json.load(f)
        return manifest
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Serve FDIC viewer files with a simple HTTP server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ./viewer_output
  %(prog)s ./viewer_output --port 9000
  %(prog)s ./viewer_output --no-browser
        """
    )
    
    parser.add_argument(
        'directory',
        type=str,
        help='Directory containing the generated viewer files'
    )
    
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=8000,
        help='Port to serve on (default: 8000)'
    )
    
    parser.add_argument(
        '--host',
        type=str,
        default='localhost',
        help='Host to bind to (default: localhost)'
    )
    
    parser.add_argument(
        '--no-browser',
        action='store_true',
        help="Don't automatically open browser"
    )
    
    args = parser.parse_args()
    
    # Validate directory
    viewer_dir = Path(args.directory)
    if not viewer_dir.exists():
        print(f"Error: Directory '{args.directory}' does not exist")
        sys.exit(1)
    
    if not viewer_dir.is_dir():
        print(f"Error: '{args.directory}' is not a directory")
        sys.exit(1)
    
    # Check for required files
    required_files = ['manifest.json', 'index.html']
    missing_files = []
    for file in required_files:
        if not (viewer_dir / file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"Error: Missing required files in viewer directory: {', '.join(missing_files)}")
        print("Make sure you've generated the viewer with --generate-viewer flag")
        sys.exit(1)
    
    # Get manifest info
    manifest = find_manifest_info(viewer_dir)
    
    # Change to the viewer directory
    os.chdir(viewer_dir)
    
    # Create and start server
    try:
        server = HTTPServer((args.host, args.port), ViewerHTTPRequestHandler)
        
        # Construct URLs
        base_url = f"http://{args.host}:{args.port}"
        
        if manifest:
            dataset_uri = manifest.get('dataset_uri', 'unknown')
            table_url = f"{base_url}?node={quote('<' + dataset_uri + '>')}"
        else:
            table_url = base_url
        
        print(f"🌐 Starting FDIC Viewer server...")
        print(f"📂 Serving directory: {viewer_dir.absolute()}")
        print(f"🔗 Server URL: {base_url}")
        print(f"📊 Table Viewer: {table_url}")
        
        if manifest:
            print(f"📋 Dataset: {manifest.get('title', 'Unknown')}")
            print(f"📈 Total rows: {manifest.get('total_rows', 0):,}")
            print(f"📄 Pages: {manifest.get('total_pages', 0)}")
        
        print(f"\n✨ Press Ctrl+C to stop the server")
        
        # Open browser automatically unless disabled
        if not args.no_browser:
            print(f"🚀 Opening browser...")
            webbrowser.open(table_url)
        
        # Start serving
        server.serve_forever()
        
    except KeyboardInterrupt:
        print(f"\n🛑 Server stopped by user")
        server.socket.close()
        
    except OSError as e:
        if e.errno == 98:  # Address already in use
            print(f"Error: Port {args.port} is already in use")
            print(f"Try a different port with --port <number>")
        else:
            print(f"Error starting server: {e}")
        sys.exit(1)
    
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()