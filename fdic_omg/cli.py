#!/usr/bin/env python3
"""
FDIC OMG CLI - Command line interface for FDIC semantic augmentation

This module provides the Click-based CLI for the FDIC RDF generator.
"""

import json
import logging
from pathlib import Path

import click

from .core import FDICRDFGenerator


def generate_fdic_rdf(csv_path: str, result_uri: str, max_rows: int = None):
    """
    Generate RDF from FDIC CSV file
    
    Args:
        csv_path: Path to FDIC CSV file
        result_uri: Base URI for the result dataset
        max_rows: Maximum number of rows to process (None for all)
        
    Returns:
        Processing results including RDF graph
    """
    generator = FDICRDFGenerator(result_uri)
    return generator.process_csv(Path(csv_path), max_rows)


def generate_challenge_metadata(column_mappings):
    """Generate OMG Challenge metadata"""
    return {
        "schema_version": "1.0",
        "challenge": "OMG Semantic Augmentation Challenge 2025",
        "submission": {
            "processor": "Accounts Assessor - Robust System",
            "organization": "Lodgeit Labs"
        },
        "mappings": column_mappings,
        "ontologies_used": [
            {
                "name": "FIBO",
                "url": "https://github.com/edmcouncil/fibo",
                "description": "Financial Industry Business Ontology",
                "columns_mapped": ["NAME", "ADDRESS", "ZIP", "CERT", "BKCLASS", "SERVTYPE_DESC"]
            },
            {
                "name": "GeoSPARQL", 
                "url": "https://opengeospatial.github.io/ogc-geosparql/geosparql11/geo.html",
                "description": "OGC GeoSPARQL geographic ontology",
                "columns_mapped": ["X", "Y", "LONGITUDE", "LATITUDE"]
            },
            {
                "name": "GeoNames",
                "url": "https://www.geonames.org/ontology/documentation.html", 
                "description": "GeoNames geographical database ontology",
                "columns_mapped": ["CITY", "STALP", "STNAME"]
            }
        ],
        "features": {
            "machine_readable": True,
            "repeatable_transformation": True,
            "multiple_output_formats": True,
            "provenance_tracking": True,
            "dataset_versioning": True,
            "scalable": True
        }
    }


@click.command()
@click.argument('csv_file', type=click.Path(exists=True))
@click.option('--result-uri', default='http://localhost/fdic/', help='Base URI for the result dataset')
@click.option('--output', '-o', type=click.Path(), help='Output file for RDF')
@click.option('--format', '-f', type=click.Choice(['turtle', 'n3', 'nt', 'json-ld', 'xml']), default='turtle', help='RDF output format')
@click.option('--max-rows', type=int, help='Maximum number of rows to process')
@click.option('--mappings-only', is_flag=True, help='Only output column mappings as JSON')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def cli(csv_file, result_uri, output, format, max_rows, mappings_only, verbose):
    """
    FDIC OMG Semantic Augmentation CLI
    
    Convert FDIC CSV files to RDF with semantic mappings for the OMG Challenge.
    
    Examples:
    
        # Generate RDF to file
        python fdic_omg_cli.py data.csv -o output.ttl
        
        # Generate JSON-LD with row limit
        python fdic_omg_cli.py data.csv --format json-ld --max-rows 100
        
        # Output mappings metadata only
        python fdic_omg_cli.py data.csv --mappings-only -o mappings.json
        
        # Generate to stdout with verbose logging
        python fdic_omg_cli.py data.csv -v
    """
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    
    if mappings_only:
        # Just output the column mappings metadata
        generator = FDICRDFGenerator(result_uri)
        metadata = generate_challenge_metadata(generator.column_mappings)
        
        if output:
            with open(output, 'w') as f:
                json.dump(metadata, f, indent=2)
            click.echo(f"✓ Mappings metadata written to {output}")
        else:
            click.echo(json.dumps(metadata, indent=2))
        return
    
    # Generate RDF
    click.echo(f"Processing {csv_file}...")
    results = generate_fdic_rdf(csv_file, result_uri, max_rows)
    
    # Output results
    if output:
        results["graph"].serialize(destination=output, format=format)
        click.echo(f"✓ RDF written to {output} ({format} format)")
    else:
        # Print to stdout
        click.echo(results["graph"].serialize(format=format))
    
    # Print statistics to stderr so they don't interfere with RDF output
    click.echo(f"\n--- OMG Challenge Statistics ---", err=True)
    click.echo(f"✓ Generated {results['triples_generated']} RDF triples", err=True)
    click.echo(f"✓ Processed {results['rows_processed']} CSV rows", err=True)
    click.echo(f"✓ Mapped {results['columns_mapped']}/{len(results['column_mappings'])} columns to ontologies", err=True)
    click.echo(f"✓ Dataset URI: {results['dataset_uri']}", err=True)


if __name__ == "__main__":
    cli()