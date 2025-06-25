#!/usr/bin/env python3
"""
FDIC OMG CLI - Streamlined command line interface for FDIC RDF conversion
"""

import logging
from pathlib import Path
from datetime import datetime
import http.server
import socketserver
import threading
import webbrowser
import click
from .core import FDICRDFGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)


@click.command()
@click.argument('csv_file', type=click.Path(exists=True))
@click.option('--output-dir', '-d', type=click.Path(), help='Output directory (default: fdic_output_YYYYMMDD_HHMMSS)')
@click.option('--max-rows', type=int, help='Maximum number of rows to process')
@click.option('--no-report', is_flag=True, help='Skip generating HTML report')
@click.option('--no-viewer', is_flag=True, help='Skip generating viewer data files')
@click.option('--rows-per-page', default=1000, help='Rows per page for viewer (default: 1000)')
@click.option('--server', is_flag=True, help='Start web server to serve the viewer')
@click.option('--port', default=8000, help='Port for the web server (default: 8000)')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def cli(csv_file, output_dir, max_rows, no_report, no_viewer, rows_per_page, server, port, verbose):
    """
    FDIC CSV to RDF Converter
    
    Convert FDIC CSV files to RDF with semantic annotations.
    
    Examples:
        # Basic usage (generates RDF, report, and viewer)
        fdic-omg data.csv
        
        # Process and serve viewer
        fdic-omg data.csv --server
        
        # Custom output directory
        fdic-omg data.csv -d my_output
        
        # Process limited rows
        fdic-omg data.csv --max-rows 1000
        
        # Skip report and viewer
        fdic-omg data.csv --no-report --no-viewer
        
        # Custom pagination and port
        fdic-omg data.csv --rows-per-page 500 --server --port 8080
    """
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    
    # Create output directory
    if not output_dir:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path(f"fdic_output_{timestamp}")
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    click.echo(f"Output directory: {output_dir}")
    
    # Initialize generator
    generator = FDICRDFGenerator()
    
    # Generate RDF
    click.echo(f"Processing {csv_file}...")
    rdf_path = output_dir / "output.ttl"
    viewer_dir = output_dir / "viewer" if not no_viewer else None
    results = generator.process_csv_to_file(Path(csv_file), rdf_path, max_rows, viewer_dir, rows_per_page)
    click.echo(f"✓ RDF written to {rdf_path}")
    
    # Generate HTML report if requested
    if not no_report:
        report_path = generator.generate_html_report(results, Path(csv_file).name, output_dir)
        click.echo(f"✓ HTML report written to {report_path}")
    
    # Print statistics
    click.echo(f"\n--- Summary ---")
    click.echo(f"✓ Generated {results['triples_generated']:,} RDF triples")
    click.echo(f"✓ Processed {results['rows_processed']:,} CSV rows")
    click.echo(f"✓ Table URI: {results['table_uri']}")
    if not no_viewer:
        click.echo(f"✓ Generated {results['viewer_pages']} viewer pages")
    click.echo(f"✓ All outputs in: {output_dir}")
    
    # List generated files
    click.echo(f"\n--- Generated Files ---")
    for item in sorted(output_dir.iterdir()):
        if item.is_file():
            size_mb = item.stat().st_size / (1024 * 1024)
            click.echo(f"  • {item.name} ({size_mb:.2f} MB)")
        elif item.is_dir() and item.name == "viewer":
            # Count all viewer files recursively
            viewer_files = list(item.rglob("*"))
            file_count = sum(1 for f in viewer_files if f.is_file())
            if file_count:
                click.echo(f"  • {item.name}/ ({file_count} files)")
    
    # Start server if requested and viewer was generated
    if server and not no_viewer and viewer_dir:
        click.echo(f"\n--- Starting Web Server ---")
        
        # Create custom handler to serve from viewer directory
        class CustomHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(viewer_dir), **kwargs)
        
        # Start server
        with socketserver.TCPServer(("", port), CustomHandler) as httpd:
            url = f"http://localhost:{port}"
            click.echo(f"Server running at: {url}")
            click.echo(f"Viewer available at: {url}/index.html")
            click.echo("Press Ctrl+C to stop the server")
            
            # Try to open browser
            try:
                webbrowser.open(f"{url}/index.html")
            except:
                pass
            
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                click.echo("\nShutting down server...")
    elif server and no_viewer:
        click.echo("\n⚠️  Cannot start server: viewer generation was disabled (--no-viewer)")
    elif not no_viewer and viewer_dir:
        click.echo(f"\nTo view the data:")
        click.echo(f"1. Start a web server: python -m http.server {port} -d {viewer_dir}")
        click.echo(f"2. Open browser: http://localhost:{port}/index.html")


if __name__ == '__main__':
    cli()