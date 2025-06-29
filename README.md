# FDIC RDF Converter

A tool for converting FDIC CSV data to RDF format with semantic annotations.

## Overview

This tool converts CSV files into RDF. It merges the generated RDF with the data found in provided annotations file, and performs a simple linking of generated column data with annotation objects based on column name.


## Features

- **Simple RDF Structure**: Converts CSV to a clean RDF representation with Tables, Columns, Rows, and Cells
- **Semantic Annotations**: Enriches columns with provided semantic metadata
- **Automatic Output Organization**: Creates timestamped directories with all outputs by default
- **HTML Reports**: Generates processing reports with statistics and annotation details  
- **Interactive Viewer**: Creates a paginated web viewer for exploring the data
- **Efficient Processing**: Handles large CSV files with configurable row limits

## Installation

```bash
# Install in development mode
pip install -e .
```

## Usage

### Command Line Interface

```bash
# Basic conversion (creates timestamped output directory)
csv2rdf example/example1.csv
# Creates: fdic_output_20250623_143052/
#   ├── output.ttl      # RDF data
#   ├── report.html     # Processing report
#   └── viewer/         # Interactive viewer files

# Custom output directory
fdic-omg data.csv -d my_output

# Process limited rows
fdic-omg data.csv --max-rows 1000

# Skip viewer or report generation
fdic-omg data.csv --no-viewer --no-report

# All options
fdic-omg data.csv \
  -d custom_output \
  --max-rows 1000 \
  --base-uri http://mycompany.com/fdic/ \
  --rows-per-page 500 \
  --no-viewer \
  -v
```

### Python API

```python
from fdic_omg.core import FDICRDFGenerator

# Create generator
generator = FDICRDFGenerator(base_uri="http://example.org/fdic/data#")

# Process CSV
results = generator.process_csv(Path("data.csv"), max_rows=1000)

# Save RDF
results["graph"].serialize(destination="output.ttl", format="turtle")

# Generate report
generator.generate_html_report(Path("report.html"), "data.csv", results)

# Generate viewer
viewer_results = generator.generate_viewer_output(Path("viewer/"))
```

## RDF Structure

The converter creates a simple RDF structure:

- **Table**: The CSV file is represented as an `fdic:Table`
- **Columns**: Each CSV column becomes an `fdic:Column` with name and index
- **Rows**: Each CSV row becomes an `fdic:Row` with index
- **Cells**: Non-empty cells become `fdic:Cell` objects linking to their row and column

Column annotations are loaded from a separate TTL file and linked to columns by matching column names.

## Column Annotations

The system includes pre-defined annotations for common FDIC columns:

- **CERT**: FDIC Certificate Number
- **NAME**: Bank name (linked to FIBO Financial Institution)
- **X/LONGITUDE**: Geographic coordinates (linked to GeoSPARQL)
- **Y/LATITUDE**: Geographic coordinates (linked to GeoSPARQL)
- **ADDRESS**: Street address (linked to FIBO address ontology)
- **ZIP**: Postal code
- And more...

Each annotation includes:
- Human-readable description
- Data type (string, integer, decimal)
- Links to external ontologies via `rdfs:seeAlso`

## Output Structure

By default, the tool creates a timestamped directory containing:

```
fdic_output_YYYYMMDD_HHMMSS/
├── output.ttl          # RDF data in Turtle format
├── report.html         # HTML report with statistics
└── viewer/             # Interactive viewer
    ├── manifest.json   # Viewer configuration
    ├── page_0.json     # Paginated data
    ├── page_1.json
    └── ...
```

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=fdic_omg --cov-report=html
```

## Architecture

The simplified architecture consists of:

1. **`core.py`** - Main RDF generation logic
2. **`cli.py`** - Command-line interface
3. **`annotations/column_annotations.ttl`** - Semantic metadata for columns
4. **`job.py`** - Integration with Robust worker system (optional)

## Requirements

- Python 3.8+
- rdflib >= 7.0.0
- click >= 8.1.0

## License

Part of the Accounts Assessor (Robust) system by Lodgeit Labs.