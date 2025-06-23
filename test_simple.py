#!/usr/bin/env python3
"""Test the simplified FDIC RDF converter"""

import csv
from pathlib import Path
from fdic_omg.core_simple import SimpleFDICRDFGenerator

# Create a sample CSV file
sample_data = """CERT,NAME,ADDRESS,CITY,STALP,ZIP,X,Y
57,First National Bank,123 Main St,Springfield,IL,62701,-89.6501,39.7817
628,Second State Bank,456 Oak Ave,Chicago,IL,60601,-87.6298,41.8781
"""

csv_path = Path("sample_fdic.csv")
with open(csv_path, 'w') as f:
    f.write(sample_data)

# Test the converter
generator = SimpleFDICRDFGenerator()
results = generator.process_csv(csv_path, max_rows=10)

print(f"Processed {results['rows_processed']} rows")
print(f"Generated {results['triples_generated']} triples")
print(f"Table URI: {results['table_uri']}")

# Save the output
output_path = Path("output_simple.ttl")
results["graph"].serialize(destination=output_path, format='turtle')
print(f"\nRDF output saved to {output_path}")

# Generate HTML report
report_path = Path("report.html")
generator.generate_html_report(report_path, csv_path.name, results)
print(f"HTML report saved to {report_path}")

# Clean up
csv_path.unlink()