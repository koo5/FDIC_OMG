# FDIC OMG Semantic Augmentation Challenge

This package implements a solution for the 2025 OMG Semantic Augmentation Challenge, specifically designed to process FDIC bank data CSV files and transform them to semantic RDF with ontology mappings.

## Overview

The solution provides:
- **Machine-readable metadata format** using JSON-LD
- **Ontology mappings** to FIBO, GeoSPARQL, and GeoNames  
- **Multiple output formats** (Turtle, JSON-LD, N3, N-Triples)
- **Repeatable transformation** process
- **Provenance tracking** with PROV-O
- **Scalable processing** with configurable row limits

## Architecture

The package is split into three main components:

1. **`core.py`** - Core RDF generation logic (framework-agnostic)
2. **`cli.py`** - Command-line interface using Click
3. **`job.py`** - Integration wrapper for the Robust worker system

## Installation

```bash
# Install in development mode
pip install -e .

# Or install dependencies only
pip install rdflib click
```

## Usage

### Command Line Interface

```bash
# Basic usage
python -m fdic_omg.cli data.csv -o output.ttl

# Generate JSON-LD with row limit  
python -m fdic_omg.cli data.csv --format json-ld --max-rows 100

# Output mappings metadata only
python -m fdic_omg.cli data.csv --mappings-only -o mappings.json

# Verbose output to stdout
python -m fdic_omg.cli data.csv -v
```

### Programmatic Usage

```python
from fdic_omg import FDICRDFGenerator

# Generate RDF from CSV
generator = FDICRDFGenerator("http://example.com/result/")
results = generator.process_csv("data.csv", max_rows=100)

# Access the RDF graph
graph = results["graph"]
graph.serialize("output.ttl", format="turtle")
```

### Robust Integration

The package integrates with the Robust worker system through `job.py`:

```python
from fdic_omg.job import process_fdic_omg_job

result = process_fdic_omg_job(
    input_files=["data.csv"],
    output_path="/tmp/output",
    public_url="https://server.com",
    result_tmp_directory_name="job123"
)
```

## Challenge Requirements

✅ **Machine-readable metadata format** - Uses JSON-LD with embedded ontology mappings  
✅ **FIBO mappings** - Financial institution names, addresses, certificates, classifications  
✅ **GeoSPARQL mappings** - Coordinates and geographic geometries  
✅ **GeoNames mappings** - Cities, states, and location names  
✅ **Repeatable transformation** - Consistent URI generation allows re-processing  
✅ **Multiple output formats** - Turtle, JSON-LD, N3, N-Triples  
✅ **Provenance tracking** - Full PROV-O metadata for dataset generation  
✅ **Scalability** - Configurable row limits and streaming processing  

## Output Files

- **`fdic_semantic.ttl`** - Human-readable Turtle RDF
- **`fdic_semantic.jsonld`** - JSON-LD with linked data context  
- **`fdic_semantic.n3`** - Notation3 RDF format
- **`fdic_semantic.nt`** - N-Triples line-based format
- **`column_mappings.json`** - Complete metadata specification
- **`fdic_omg_report.html`** - Interactive HTML report with RDF browser links

## Ontology Mappings

The system maps FDIC CSV columns to standard ontologies:

| Column | Ontology | Mapping |
|--------|----------|---------|
| NAME | FIBO | Financial organization legal name |
| ADDRESS, CITY, ZIP | FIBO | Physical address components |
| CERT | FIBO | Corporate identifier |
| LONGITUDE, LATITUDE | GeoSPARQL | Geographic coordinates |
| STALP, STNAME | GeoNames | State codes and names |

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black .
isort .
```