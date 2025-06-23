#!/usr/bin/env python3
"""
FDIC RDF Core - Simplified semantic conversion

This module converts FDIC CSV data to RDF with column annotations.
"""

import csv
import json
import math
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

import rdflib
from rdflib import Graph, URIRef, Literal, Namespace, BNode
from rdflib.namespace import RDF, RDFS, XSD, DCTERMS

# Setup logging
log = logging.getLogger(__name__)

# Define namespaces
FDIC = Namespace("http://example.org/fdic/ontology#")
DATA = Namespace("http://example.org/fdic/data#")


class SimpleFDICRDFGenerator:
    """Simplified RDF generation for FDIC CSV files"""
    
    def __init__(self, base_uri: str = "http://example.org/fdic/data#"):
        self.base_uri = base_uri
        self.graph = Graph()
        self._bind_namespaces()
        
    def _bind_namespaces(self):
        """Bind namespaces to the RDF graph"""
        self.graph.bind("fdic", FDIC)
        self.graph.bind("data", DATA)
        self.graph.bind("dcterms", DCTERMS)
        self.graph.bind("rdfs", RDFS)
        
    def process_csv(self, csv_path: Path, max_rows: Optional[int] = None) -> Dict[str, Any]:
        """Process FDIC CSV file and generate RDF"""
        log.info(f"Processing FDIC CSV: {csv_path}")
        
        # Step 1: Build basic table structure
        table_uri = URIRef(self.base_uri + f"table_{csv_path.stem}")
        rows_processed = self._build_table_structure(csv_path, table_uri, max_rows)
        
        # Step 2: Load and merge column annotations
        annotations_file = Path(__file__).parent / "annotations" / "column_annotations.ttl"
        if annotations_file.exists():
            annotation_graph = Graph()
            annotation_graph.parse(annotations_file, format="turtle")
            self.graph += annotation_graph
            
            # Step 3: Link columns to their annotations based on column name
            self._link_column_annotations()
        
        return {
            "table_uri": str(table_uri),
            "rows_processed": rows_processed,
            "triples_generated": len(self.graph),
            "graph": self.graph
        }
    
    def _build_table_structure(self, csv_path: Path, table_uri: URIRef, max_rows: Optional[int]) -> int:
        """Build basic RDF structure for the table"""
        rows_processed = 0
        
        # Table metadata
        self.graph.add((table_uri, RDF.type, FDIC.Table))
        self.graph.add((table_uri, DCTERMS.title, Literal(f"FDIC Table: {csv_path.name}")))
        self.graph.add((table_uri, DCTERMS.created, Literal(datetime.now().isoformat(), datatype=XSD.dateTime)))
        
        with open(csv_path, 'r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            headers = reader.fieldnames
            
            # Create columns and keep track of them
            column_refs = {}
            for col_idx, header in enumerate(headers):
                column_uri = BNode()  # Use blank node for column
                self.graph.add((column_uri, RDF.type, FDIC.Column))
                self.graph.add((column_uri, FDIC.columnName, Literal(header)))
                self.graph.add((column_uri, FDIC.columnIndex, Literal(col_idx, datatype=XSD.integer)))
                self.graph.add((table_uri, FDIC.hasColumn, column_uri))
                column_refs[header] = column_uri
            
            # Process rows
            for row_idx, row in enumerate(reader):
                row_uri = BNode()  # Use blank node for row
                self.graph.add((row_uri, RDF.type, FDIC.Row))
                self.graph.add((row_uri, FDIC.rowIndex, Literal(row_idx, datatype=XSD.integer)))
                self.graph.add((table_uri, FDIC.hasRow, row_uri))
                
                # Create cells
                for header in headers:
                    value = row.get(header, "")
                    if value and value.strip():
                        cell_uri = BNode()  # Use blank node for cell
                        self.graph.add((cell_uri, RDF.type, FDIC.Cell))
                        self.graph.add((cell_uri, FDIC.value, Literal(value)))
                        self.graph.add((cell_uri, FDIC.inRow, row_uri))
                        self.graph.add((cell_uri, FDIC.inColumn, column_refs[header]))
                
                rows_processed += 1
                if max_rows and rows_processed >= max_rows:
                    log.info(f"Limiting processing to first {rows_processed} rows")
                    break
        
        return rows_processed
    
    def _link_column_annotations(self):
        """Link columns to their annotation definitions based on column name"""
        # Find all columns
        columns = list(self.graph.subjects(RDF.type, FDIC.Column))
        
        # Find all column annotations
        annotations = list(self.graph.subjects(RDF.type, FDIC.ColumnAnnotation))
        
        # Link columns to annotations by matching column names
        for column in columns:
            column_name = self.graph.value(column, FDIC.columnName)
            if column_name:
                for annotation in annotations:
                    annotation_column_name = self.graph.value(annotation, FDIC.columnName)
                    if annotation_column_name and str(column_name) == str(annotation_column_name):
                        self.graph.add((column, FDIC.hasAnnotation, annotation))
                        log.debug(f"Linked column {column_name} to annotation {annotation}")
                        break
    
    def generate_html_report(self, output_path: Path, csv_name: str, results: Dict[str, Any]) -> Path:
        """Generate HTML report for FDIC RDF conversion results"""
        # Get annotation statistics
        columns_with_annotations = 0
        total_columns = 0
        annotation_details = []
        
        tables = list(self.graph.subjects(RDF.type, FDIC.Table))
        if tables:
            table = tables[0]  # Assume one table
            for col in self.graph.objects(table, FDIC.hasColumn):
                total_columns += 1
                col_name = self.graph.value(col, FDIC.columnName)
                annotation = self.graph.value(col, FDIC.hasAnnotation)
                if annotation:
                    columns_with_annotations += 1
                    desc = self.graph.value(annotation, DCTERMS.description)
                    annotation_details.append({
                        'column': str(col_name),
                        'description': str(desc) if desc else 'N/A',
                        'annotation_uri': str(annotation)
                    })
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>FDIC RDF Conversion Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .success {{ background-color: #d4edda; color: #155724; padding: 10px; border-radius: 5px; margin: 10px 0; }}
        .metadata {{ background-color: #f8f9fa; padding: 15px; margin: 15px 0; border-left: 4px solid #3498db; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 10px; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        th {{ background-color: #3498db; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
        .stat-box {{ text-align: center; padding: 20px; background-color: #ecf0f1; border-radius: 5px; }}
        .stat-number {{ font-size: 36px; color: #3498db; font-weight: bold; }}
        .stat-label {{ color: #7f8c8d; margin-top: 5px; }}
        .download-link {{ display: inline-block; margin: 10px 10px 10px 0; padding: 10px 20px; background-color: #3498db; color: white; text-decoration: none; border-radius: 5px; }}
        .download-link:hover {{ background-color: #2980b9; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>FDIC RDF Conversion Report</h1>
        
        <div class="success">
            <strong>✅ Success!</strong> FDIC CSV has been successfully converted to RDF with semantic annotations
        </div>
        
        <div class="stats">
            <div class="stat-box">
                <div class="stat-number">{results.get('triples_generated', 0):,}</div>
                <div class="stat-label">RDF Triples</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{results.get('rows_processed', 0):,}</div>
                <div class="stat-label">Rows Processed</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{columns_with_annotations}/{total_columns}</div>
                <div class="stat-label">Annotated Columns</div>
            </div>
        </div>
        
        <div class="metadata">
            <h2>Dataset Information</h2>
            <p><strong>Source File:</strong> {csv_name}</p>
            <p><strong>Table URI:</strong> {results.get('table_uri', 'N/A')}</p>
            <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <h2>📥 Output</h2>
        <p>The RDF output is available in Turtle format (.ttl), which is a human-readable RDF serialization.</p>
        
        <h2>📊 Column Annotations</h2>
        <p>The following columns have been enriched with semantic annotations:</p>
        <table>
            <tr>
                <th>Column Name</th>
                <th>Description</th>
                <th>Annotation URI</th>
            </tr>
"""
        
        for detail in sorted(annotation_details, key=lambda x: x['column']):
            html_content += f"""
            <tr>
                <td><strong>{detail['column']}</strong></td>
                <td>{detail['description']}</td>
                <td><code>{detail['annotation_uri']}</code></td>
            </tr>"""
        
        html_content += """
        </table>
        
        <div class="metadata">
            <h2>About This Conversion</h2>
            <p>This RDF conversion follows a simplified approach where:</p>
            <ul>
                <li>CSV structure is represented as Tables, Columns, Rows, and Cells</li>
                <li>Column annotations are loaded from a separate RDF file and linked by column name</li>
                <li>All annotations and external ontology references are preserved via rdfs:seeAlso links</li>
                <li>The output is a single, clean RDF graph in Turtle format</li>
            </ul>
        </div>
    </div>
</body>
</html>"""
        
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        return output_path
    
    def generate_viewer_output(self, output_dir: Path, rows_per_page: int = 1000) -> Dict[str, Any]:
        """Generate standalone tabular data viewer from RDF data"""
        log.info(f"Generating viewer output in {output_dir}")
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy pre-built Vue app files if they exist
        rdftab_build_dir = Path(__file__).parent.parent.parent.parent.parent / "static" / "rdftab"
        if rdftab_build_dir.exists():
            for item in rdftab_build_dir.rglob("*"):
                if item.is_file():
                    rel_path = item.relative_to(rdftab_build_dir)
                    dest_path = output_dir / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest_path)
        else:
            log.warning(f"RDFtab build directory not found: {rdftab_build_dir}")
        
        # Extract data from RDF graph
        table_data = self._extract_table_data_from_rdf()
        
        if not table_data:
            log.error("No table data found in RDF graph")
            return {"error": "No table data found"}
        
        headers = table_data['headers']
        rows = table_data['rows']
        total_rows = len(rows)
        total_pages = math.ceil(total_rows / rows_per_page)
        
        # Generate manifest
        manifest = {
            "dataset_uri": str(table_data['table_uri']),
            "title": table_data['title'],
            "description": "FDIC-Insured Institutions Dataset with semantic annotations",
            "total_rows": total_rows,
            "rows_per_page": rows_per_page,
            "total_pages": total_pages,
            "headers": headers,
            "column_annotations": self._get_column_annotations_for_viewer()
        }
        
        # Write manifest
        with open(output_dir / "manifest.json", 'w') as f:
            json.dump(manifest, f, indent=2)
        
        # Generate paginated data
        for page_num in range(total_pages):
            start_idx = page_num * rows_per_page
            end_idx = min(start_idx + rows_per_page, total_rows)
            
            page_data = {
                "page": page_num,
                "start_row": start_idx,
                "end_row": end_idx - 1,
                "rows": rows[start_idx:end_idx]
            }
            
            with open(output_dir / f"page_{page_num}.json", 'w') as f:
                json.dump(page_data, f, indent=2)
        
        log.info(f"Generated viewer with {total_pages} pages in {output_dir}")
        return {
            "output_dir": str(output_dir),
            "total_rows": total_rows,
            "total_pages": total_pages,
            "manifest_file": str(output_dir / "manifest.json")
        }
    
    def _extract_table_data_from_rdf(self) -> Optional[Dict[str, Any]]:
        """Extract table structure and data from RDF graph"""
        # Find the table
        tables = list(self.graph.subjects(RDF.type, FDIC.Table))
        if not tables:
            return None
        
        table = tables[0]
        title = self.graph.value(table, DCTERMS.title) or "FDIC Table"
        
        # Get columns in order
        columns = []
        for col in self.graph.objects(table, FDIC.hasColumn):
            col_name = self.graph.value(col, FDIC.columnName)
            col_idx = self.graph.value(col, FDIC.columnIndex)
            if col_name and col_idx is not None:
                columns.append((int(col_idx), str(col_name), col))
        
        columns.sort(key=lambda x: x[0])
        headers = [name for _, name, _ in columns]
        col_map = {name: col for _, name, col in columns}
        
        # Get rows
        rows_data = []
        for row in self.graph.objects(table, FDIC.hasRow):
            row_idx = self.graph.value(row, FDIC.rowIndex)
            if row_idx is not None:
                # Get cells for this row
                row_values = [""] * len(headers)  # Initialize with empty strings
                
                for cell in self.graph.subjects(FDIC.inRow, row):
                    col = self.graph.value(cell, FDIC.inColumn)
                    value = self.graph.value(cell, FDIC.value)
                    
                    # Find column index
                    for i, (_, name, col_ref) in enumerate(columns):
                        if col == col_ref:
                            row_values[i] = str(value) if value else ""
                            break
                
                rows_data.append((int(row_idx), row_values))
        
        # Sort by row index
        rows_data.sort(key=lambda x: x[0])
        rows = [values for _, values in rows_data]
        
        return {
            'table_uri': table,
            'title': str(title),
            'headers': headers,
            'rows': rows
        }
    
    def _get_column_annotations_for_viewer(self) -> Dict[str, Dict]:
        """Get simplified column annotations for the viewer"""
        viewer_annotations = {}
        
        # Find all column annotations in the graph
        for annotation in self.graph.subjects(RDF.type, FDIC.ColumnAnnotation):
            col_name = self.graph.value(annotation, FDIC.columnName)
            if col_name:
                desc = self.graph.value(annotation, DCTERMS.description)
                data_type = self.graph.value(annotation, FDIC.dataType)
                
                viewer_annotations[str(col_name)] = {
                    "label": str(col_name).replace("_", " ").title(),
                    "description": str(desc) if desc else "",
                    "dataType": str(data_type) if data_type else "string",
                    "annotationUri": str(annotation)
                }
        
        return viewer_annotations