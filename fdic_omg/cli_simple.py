#!/usr/bin/env python3
"""
FDIC OMG CLI - Simplified command line interface for FDIC RDF conversion

This module provides the Click-based CLI for the simplified FDIC RDF generator.
"""

import logging
from pathlib import Path

import click

from .core_simple import SimpleFDICRDFGenerator


def generate_fdic_rdf(csv_path: str, base_uri: str, max_rows: int = None):
    """
    Generate RDF from FDIC CSV file
    
    Args:
        csv_path: Path to FDIC CSV file
        base_uri: Base URI for the data
        max_rows: Maximum number of rows to process (None for all)
        
    Returns:
        Processing results including RDF graph
    """
    generator = SimpleFDICRDFGenerator(base_uri)
    return generator.process_csv(Path(csv_path), max_rows)


@click.command()
@click.argument('csv_file', type=click.Path(exists=True))
@click.option('--base-uri', default='http://example.org/fdic/data#', help='Base URI for the data')
@click.option('--output', '-o', type=click.Path(), help='Output file (RDF Turtle format)')
@click.option('--max-rows', type=int, help='Maximum number of rows to process')
@click.option('--generate-viewer', type=click.Path(), help='Generate interactive web viewer in specified directory')
@click.option('--rows-per-page', default=1000, help='Rows per page for viewer pagination (default: 1000)')
@click.option('--report', '-r', type=click.Path(), help='Generate HTML report')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def cli(csv_file, base_uri, output, max_rows, generate_viewer, rows_per_page, report, verbose):
    """
    FDIC OMG Semantic Augmentation CLI
    
    Convert FDIC CSV files to RDF with semantic annotations.
    
    Examples:
    
        # Generate RDF to file
        python -m fdic_omg.cli_simple data.csv -o output.ttl
        
        # Generate RDF with row limit
        python -m fdic_omg.cli_simple data.csv -o output.ttl --max-rows 100
        
        # Generate RDF with HTML report
        python -m fdic_omg.cli_simple data.csv -o output.ttl -r report.html
        
        # Generate interactive web viewer
        python -m fdic_omg.cli_simple data.csv --generate-viewer ./viewer_output
        
        # Generate viewer with custom pagination
        python -m fdic_omg.cli_simple data.csv --generate-viewer ./viewer --rows-per-page 500
        
        # Generate to stdout with verbose logging
        python -m fdic_omg.cli_simple data.csv -v
    """
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    
    # Initialize generator
    generator = SimpleFDICRDFGenerator(base_uri)
    
    # Generate RDF
    click.echo(f"Processing {csv_file}...")
    results = generator.process_csv(Path(csv_file), max_rows)
    
    # Output RDF (Turtle format)
    if output:
        results["graph"].serialize(destination=output, format='turtle')
        click.echo(f"✓ RDF written to {output} (Turtle format)")
    else:
        # Print to stdout
        click.echo(results["graph"].serialize(format='turtle'))
    
    # Generate HTML report if requested
    if report:
        generator.generate_html_report(Path(report), Path(csv_file).name, results)
        click.echo(f"✓ HTML report written to {report}")
    
    # Generate viewer if requested
    if generate_viewer:
        click.echo(f"Generating interactive viewer...")
        viewer_results = generator.generate_viewer_output(
            Path(generate_viewer), 
            rows_per_page
        )
        
        if 'error' not in viewer_results:
            click.echo(f"✓ Interactive viewer generated in {generate_viewer}")
            click.echo(f"✓ Processed {viewer_results['total_rows']} rows in {viewer_results['total_pages']} pages")
            click.echo(f"✓ Manifest file: {viewer_results['manifest_file']}")
            click.echo(f"\nTo view the table:")
            click.echo(f"1. Start a web server: python -m http.server 8000 -d {generate_viewer}")
            click.echo(f"2. Open browser: http://localhost:8000?node=<{results['table_uri']}>")
        else:
            click.echo(f"Error generating viewer: {viewer_results['error']}")
    
    # Print statistics to stderr so they don't interfere with RDF output
    if verbose or output or report:
        click.echo(f"\n--- Statistics ---", err=True)
        click.echo(f"✓ Generated {results['triples_generated']} RDF triples", err=True)
        click.echo(f"✓ Processed {results['rows_processed']} CSV rows", err=True)
        click.echo(f"✓ Table URI: {results['table_uri']}", err=True)


if __name__ == "__main__":
    cli()