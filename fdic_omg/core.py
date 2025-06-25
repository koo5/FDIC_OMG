"""
Streaming FDIC CSV to RDF converter that outputs RDF text directly
without building an in-memory graph.
"""
import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, TextIO, Dict, Any, List
from urllib.parse import quote
import json

log = logging.getLogger(__name__)


class FDICRDFGenerator:
    """Streaming RDF generator that outputs Turtle format directly"""
    
    def __init__(self):
        self.base_uri = "https://fdic.example.org/data/"
        self.prefixes = {
            "fdic": "https://fdic.example.org/ontology#",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            "dcterms": "http://purl.org/dc/terms/",
            "fibo-fbc-fct-usrga": "https://spec.edmcouncil.org/fibo/ontology/FBC/FunctionalEntities/RegistrationAuthorities/",
            "fibo-be-corp-corp": "https://spec.edmcouncil.org/fibo/ontology/BE/Corporations/Corporations/",
            "fibo-fbc-fi-fi": "https://spec.edmcouncil.org/fibo/ontology/FBC/FinancialInstruments/FinancialInstruments/",
            "fibo-fnd-plc-adr": "https://spec.edmcouncil.org/fibo/ontology/FND/Places/Addresses/",
            "fibo-fnd-plc-loc": "https://spec.edmcouncil.org/fibo/ontology/FND/Places/Locations/",
            "gn": "http://www.geonames.org/ontology#",
            "geosparql": "http://www.opengis.net/ont/geosparql#"
        }
        self.annotations = None
        self._load_annotations()
        
    def _load_annotations(self):
        """Load column annotations from TTL file"""
        annotations_file = Path(__file__).parent / "annotations" / "column_annotations.ttl"
        if annotations_file.exists():
            # Parse annotations file to extract column mappings
            self.annotations = {}
            with open(annotations_file, 'r', encoding='utf-8') as f:
                current_annotation = None
                current_column_name = None
                for line in f:
                    line = line.strip()
                    if line.startswith('fdic:') and 'a fdic:ColumnAnnotation' in line:
                        # Extract annotation ID
                        current_annotation = line.split()[0]
                    elif current_annotation and 'fdic:columnName' in line:
                        # Extract column name
                        start = line.find('"') + 1
                        end = line.rfind('"')
                        if start > 0 and end > start:
                            current_column_name = line[start:end]
                            self.annotations[current_column_name] = current_annotation
                            current_annotation = None
                            current_column_name = None
    
    def _write_prefixes(self, output: TextIO):
        """Write Turtle prefixes"""
        for prefix, uri in self.prefixes.items():
            output.write(f"@prefix {prefix}: <{uri}> .\n")
        output.write("\n")
    
    def _escape_literal(self, value: str) -> str:
        """Escape special characters in literals"""
        return value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
    
    def _make_uri(self, *parts) -> str:
        """Create a URI from parts"""
        return self.base_uri + "/".join(quote(str(p), safe='') for p in parts)
    
    def process_csv_streaming(self, csv_path: Path, output: TextIO, max_rows: Optional[int] = None, 
                            viewer_dir: Optional[Path] = None, rows_per_page: int = 1000) -> Dict[str, Any]:
        """Process CSV and stream RDF output directly, optionally generating viewer data"""
        rows_processed = 0
        triples_count = 0
        
        # Viewer data collection
        viewer_data = []
        current_page = 0
        
        # Write prefixes
        self._write_prefixes(output)
        
        # Table URI
        table_uri = self._make_uri("table", csv_path.stem)
        
        # Write table metadata
        output.write(f"<{table_uri}> a fdic:Table ;\n")
        output.write(f'    dcterms:title "FDIC Table: {csv_path.name}" ;\n')
        output.write(f'    dcterms:created "{datetime.now().isoformat()}"^^xsd:dateTime .\n\n')
        triples_count += 3
        
        # Count total rows if needed
        total_rows = None
        if max_rows:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                total_rows = sum(1 for line in f) - 1
                if total_rows > max_rows:
                    log.info(f"CSV has {total_rows:,} rows, processing first {max_rows:,} rows")
                else:
                    log.info(f"CSV has {total_rows:,} rows, processing all rows")
        
        with open(csv_path, 'r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            headers = reader.fieldnames
            
            # If viewer requested, write table metadata to separate file
            if viewer_dir:
                metadata_path = viewer_dir / "table_metadata.ttl"
                with open(metadata_path, 'w', encoding='utf-8') as metadata_file:
                    # Write prefixes
                    metadata_file.write("# Table and Column Metadata\n")
                    for prefix, uri in self.prefixes.items():
                        metadata_file.write(f"@prefix {prefix}: <{uri}> .\n")
                    metadata_file.write('\n')
                    
                    # Write table metadata
                    metadata_file.write(f"<{table_uri}> a fdic:Table ;\n")
                    metadata_file.write(f'    dcterms:title "FDIC Table: {csv_path.name}" ;\n')
                    metadata_file.write(f'    dcterms:created "{datetime.now().isoformat()}"^^xsd:dateTime .\n\n')
                    
                    # Write column definitions with annotations
                    metadata_file.write("# Column definitions\n")
                    for col_idx, header in enumerate(headers):
                        column_uri = self._make_uri("column", csv_path.stem, str(col_idx))
                        metadata_file.write(f"<{column_uri}> a fdic:Column ;\n")
                        metadata_file.write(f'    fdic:columnName "{self._escape_literal(header)}" ;\n')
                        metadata_file.write(f'    fdic:columnIndex {col_idx} .\n')
                        
                        # Add annotation if available
                        if self.annotations and header in self.annotations:
                            metadata_file.write(f"<{column_uri}> fdic:hasAnnotation {self.annotations[header]} .\n")
                        
                        metadata_file.write(f"<{table_uri}> fdic:hasColumn <{column_uri}> .\n\n")
                    
                    # Copy the full annotation definitions from the annotations file
                    annotations_file = Path(__file__).parent / "annotations" / "column_annotations.ttl"
                    if annotations_file.exists():
                        metadata_file.write("\n# Column Annotation Definitions\n")
                        with open(annotations_file, 'r', encoding='utf-8') as ann_file:
                            # Skip the prefix lines (they're already included)
                            content = ann_file.read()
                            # Find where the actual annotations start
                            start_marker = "# Simple column annotations"
                            if start_marker in content:
                                ann_start = content.find(start_marker)
                                metadata_file.write(content[ann_start:])
                            else:
                                # Just skip lines starting with @ (prefixes)
                                for line in content.split('\n'):
                                    if not line.strip().startswith('@') and line.strip():
                                        metadata_file.write(line + '\n')
            
            # Write column definitions to main output (basic info only)
            output.write("# Column definitions\n")
            for col_idx, header in enumerate(headers):
                column_uri = self._make_uri("column", csv_path.stem, str(col_idx))
                output.write(f"<{column_uri}> a fdic:Column ;\n")
                output.write(f'    fdic:columnName "{self._escape_literal(header)}" ;\n')
                output.write(f'    fdic:columnIndex {col_idx} .\n')
                triples_count += 3
                
                output.write(f"<{table_uri}> fdic:hasColumn <{column_uri}> .\n\n")
                triples_count += 1
            
            # Process rows
            output.write("# Data rows\n")
            for row_idx, row in enumerate(reader):
                row_uri = self._make_uri("row", csv_path.stem, str(row_idx))
                
                # Write row
                output.write(f"<{row_uri}> a fdic:Row ;\n")
                output.write(f"    fdic:rowIndex {row_idx} .\n")
                output.write(f"<{table_uri}> fdic:hasRow <{row_uri}> .\n")
                triples_count += 3
                
                # Collect viewer data if requested
                if viewer_dir:
                    viewer_row = {
                        "row_index": row_idx,
                        "row_uri": row_uri,
                        "cells": {},
                        "cell_uris": {},
                        "cell_rdf": {}
                    }
                    for col_idx, header in enumerate(headers):
                        value = row.get(header, "")
                        if value and value.strip():
                            viewer_row["cells"][header] = value
                            # Add cell URI and RDF data
                            cell_uri = self._make_uri("cell", csv_path.stem, str(row_idx), str(col_idx))
                            column_uri = self._make_uri("column", csv_path.stem, str(col_idx))
                            viewer_row["cell_uris"][header] = cell_uri
                            viewer_row["cell_rdf"][header] = {
                                "uri": cell_uri,
                                "type": "fdic:Cell",
                                "value": value,
                                "inRow": row_uri,
                                "inColumn": column_uri,
                                "columnName": header
                            }
                    viewer_data.append(viewer_row)
                    
                    # Write page when buffer is full
                    if len(viewer_data) >= rows_per_page:
                        self._write_viewer_page(viewer_dir, current_page, viewer_data)
                        viewer_data = []
                        current_page += 1
                
                # Write cells for non-empty values
                has_cells = False
                for col_idx, header in enumerate(headers):
                    value = row.get(header, "")
                    if value and value.strip():
                        cell_uri = self._make_uri("cell", csv_path.stem, str(row_idx), str(col_idx))
                        column_uri = self._make_uri("column", csv_path.stem, str(col_idx))
                        
                        output.write(f"<{cell_uri}> a fdic:Cell ;\n")
                        output.write(f'    fdic:value "{self._escape_literal(value)}" ;\n')
                        output.write(f"    fdic:inRow <{row_uri}> ;\n")
                        output.write(f"    fdic:inColumn <{column_uri}> .\n")
                        triples_count += 4
                        has_cells = True
                
                if has_cells:
                    output.write("\n")
                
                rows_processed += 1
                
                # Log progress
                if rows_processed % 1000 == 0:
                    if max_rows:
                        remaining = max_rows - rows_processed
                        log.info(f"Processed {rows_processed:,} rows, {remaining:,} remaining")
                    else:
                        log.info(f"Processed {rows_processed:,} rows")
                
                if max_rows and rows_processed >= max_rows:
                    log.info(f"Reached limit of {rows_processed:,} rows")
                    break
        
        # Write annotations at the end if they exist
        if self.annotations:
            output.write("\n# Column Annotations (loaded from column_annotations.ttl)\n")
            annotations_file = Path(__file__).parent / "annotations" / "column_annotations.ttl"
            if annotations_file.exists():
                with open(annotations_file, 'r', encoding='utf-8') as f:
                    # Skip prefix lines
                    for line in f:
                        if not line.strip().startswith('@prefix') and line.strip():
                            output.write(line)
        
        # Write final viewer page if there's remaining data
        if viewer_dir and viewer_data:
            self._write_viewer_page(viewer_dir, current_page, viewer_data)
            current_page += 1
        
        # Generate manifest if viewer was requested
        total_pages = current_page if viewer_dir else 0
        if viewer_dir:
            # Build column RDF data for viewer
            column_rdf = {}
            for col_idx, header in enumerate(headers):
                column_uri = self._make_uri("column", csv_path.stem, str(col_idx))
                column_rdf[header] = {
                    "uri": column_uri,
                    "type": "fdic:Column",
                    "columnName": header,
                    "columnIndex": col_idx
                }
                if self.annotations and header in self.annotations:
                    column_rdf[header]["hasAnnotation"] = self.annotations[header]
            
            self._write_viewer_manifest(viewer_dir, {
                "dataset_uri": table_uri,
                "rdf_type": ["http://www.w3.org/ns/csvw#Table"],
                "title": f"FDIC Table: {csv_path.name}",
                "headers": headers,
                "total_rows": rows_processed,
                "rows_per_page": rows_per_page,
                "total_pages": total_pages,
                "annotations": self.annotations if self.annotations else {},
                "column_rdf": column_rdf
            })
        
        log.info(f"Completed processing {rows_processed:,} rows")
        
        return {
            "table_uri": table_uri,
            "rows_processed": rows_processed,
            "triples_generated": triples_count,
            "viewer_pages": total_pages
        }
    
    def process_csv_to_file(self, csv_path: Path, output_path: Path, max_rows: Optional[int] = None,
                          viewer_dir: Optional[Path] = None, rows_per_page: int = 1000) -> Dict[str, Any]:
        """Process CSV and write RDF to file"""
        if viewer_dir:
            viewer_dir.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as output:
            return self.process_csv_streaming(csv_path, output, max_rows, viewer_dir, rows_per_page)
    
    
    def generate_html_report(self, results: Dict[str, Any], csv_name: str, output_path: Path) -> Path:
        """Generate HTML report for conversion results"""
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
        .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
        .stat-box {{ text-align: center; padding: 20px; background-color: #ecf0f1; border-radius: 5px; }}
        .stat-number {{ font-size: 36px; color: #3498db; font-weight: bold; }}
        .stat-label {{ color: #7f8c8d; margin-top: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>FDIC RDF Conversion Report</h1>
        
        <div class="success">
            <strong>✅ Success!</strong> FDIC CSV has been successfully converted to RDF using streaming processing
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
        </div>
        
        <div class="metadata">
            <h2>Dataset Information</h2>
            <p><strong>Source File:</strong> {csv_name}</p>
            <p><strong>Table URI:</strong> {results.get('table_uri', 'N/A')}</p>
            <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Processing Method:</strong> Streaming (memory-efficient)</p>
        </div>
        
        <h2>📥 Output</h2>
        <p>The RDF output has been generated in Turtle format (.ttl) using streaming processing for improved performance and memory efficiency.</p>
    </div>
</body>
</html>
"""
        
        report_path = output_path / "report.html"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return report_path
    
    def _write_viewer_page(self, viewer_dir: Path, page_num: int, rows: List[Dict]) -> None:
        """Write a page of viewer data to JSON file"""
        page_data = {
            "page": page_num,
            "start_row": rows[0]["row_index"] if rows else 0,
            "end_row": rows[-1]["row_index"] if rows else 0,
            "rows": rows
        }
        
        page_path = viewer_dir / f"page_{page_num}.json"
        with open(page_path, 'w', encoding='utf-8') as f:
            json.dump(page_data, f, indent=2)
    
    def _write_viewer_manifest(self, viewer_dir: Path, metadata: Dict) -> None:
        """Write viewer manifest file"""
        import shutil
        
        # Copy RDFtab viewer template files
        viewer_template_dir = Path(__file__).parent / "viewer_template"
        if viewer_template_dir.exists():
            # Copy all files from template
            for item in viewer_template_dir.rglob('*'):
                if item.is_file():
                    rel_path = item.relative_to(viewer_template_dir)
                    dest_path = viewer_dir / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest_path)
        else:
            # Fallback to old location
            rdftab_build_dir = Path(__file__).parent.parent.parent.parent.parent / "static" / "rdftab-sfc"
            if rdftab_build_dir.exists():
                for item in rdftab_build_dir.rglob('*'):
                    if item.is_file():
                        rel_path = item.relative_to(rdftab_build_dir)
                        if item.name == 'index-sfc.html':
                            dest_path = viewer_dir / 'index.html'
                        else:
                            dest_path = viewer_dir / rel_path
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dest_path)
        
        # Write manifest
        manifest_path = viewer_dir / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        # Also copy the TTL file to viewer directory for RDFtab access
        ttl_source = viewer_dir.parent / "output.ttl"
        if ttl_source.exists():
            shutil.copy2(ttl_source, viewer_dir / "data.ttl")
    
