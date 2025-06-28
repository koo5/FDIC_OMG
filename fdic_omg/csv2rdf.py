#!/usr/bin/env python3
"""
CSV to RDF converter using rdflib for all RDF operations.
Streams CSV rows to avoid memory issues with large files.
"""
import argparse
import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, TextIO
from urllib.parse import quote

from rdflib import Graph, URIRef, Literal, RDF, RDFS, XSD
from rdflib.namespace import DCTERMS

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class CSV2RDF:
    """Convert CSV to RDF using rdflib"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize graphs
        self.graph = Graph()
        self.annotations_graph = Graph()
        self.column_annotations = {}
        
    def load_annotations(self, annotations_path: Path):
        """Load annotations from TTL file using rdflib"""
        log.info(f"Loading annotations from {annotations_path}")
        
        # Parse the TTL file
        self.annotations_graph.parse(annotations_path, format="turtle")
        
        # Copy all namespaces from annotations to main graph
        for prefix, namespace in self.annotations_graph.namespaces():
            if prefix:
                self.graph.bind(prefix, namespace)
        
        # Define the specific predicate we're looking for
        # This should match whatever is used in the annotations file
        column_name_pred = URIRef("http://example.org/fdic/ontology#columnName")
        
        # Find column annotations by looking for triples with the columnName predicate
        for subj, pred, obj in self.annotations_graph.triples((None, column_name_pred, None)):
            column_name = str(obj)
            self.column_annotations[column_name] = subj
            log.debug(f"Found annotation for column {column_name}: {subj}")
                
        log.info(f"Loaded {len(self.column_annotations)} column annotations")
        
    def create_table_metadata(self, csv_path: Path, headers: List[str]) -> URIRef:
        """Create table and column metadata in the graph"""
        table_name = csv_path.stem
        table_uri = URIRef(f"https://example.org/data/table/{table_name}")
        
        # Add table metadata
        self.graph.add((table_uri, RDF.type, URIRef("https://example.org/ontology#Table")))
        self.graph.add((table_uri, DCTERMS.title, Literal(f"Table: {csv_path.name}")))
        self.graph.add((table_uri, DCTERMS.created, Literal(datetime.now().isoformat(), datatype=XSD.dateTime)))
        
        # Add column metadata
        for idx, header in enumerate(headers):
            column_uri = URIRef(f"https://example.org/data/column/{table_name}/{idx}")
            
            # Basic column properties
            self.graph.add((column_uri, RDF.type, URIRef("https://example.org/ontology#Column")))
            self.graph.add((column_uri, URIRef("https://example.org/ontology#columnName"), Literal(header)))
            self.graph.add((column_uri, URIRef("https://example.org/ontology#columnIndex"), Literal(idx, datatype=XSD.integer)))
            self.graph.add((table_uri, URIRef("https://example.org/ontology#hasColumn"), column_uri))
            
            # Link to annotation if exists
            if header in self.column_annotations:
                annotation_uri = self.column_annotations[header]
                self.graph.add((column_uri, URIRef("https://example.org/ontology#hasAnnotation"), annotation_uri))
                
                # Copy annotation triples to main graph
                for s, p, o in self.annotations_graph.triples((annotation_uri, None, None)):
                    self.graph.add((s, p, o))
                    
        return table_uri
        
    def write_row_triple(self, file: TextIO, row_uri: URIRef, predicate: URIRef, value: Any, datatype=None):
        """Write a single triple in N-Triples format"""
        if value is None or (isinstance(value, str) and not value.strip()):
            return
            
        # Format the triple
        if isinstance(value, URIRef):
            # Value is already a URI reference
            obj = value.n3()
        elif datatype:
            obj = Literal(value, datatype=datatype).n3()
        else:
            obj = Literal(value).n3()
            
        file.write(f"{row_uri.n3()} {predicate.n3()} {obj} .\n")
        
    def process_csv(self, csv_path: Path, max_rows: Optional[int] = None, rows_per_chunk: int = 1000):
        """Process CSV file and generate RDF output"""
        table_name = csv_path.stem
        
        # Read CSV headers
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            
        # Create table metadata
        table_uri = self.create_table_metadata(csv_path, headers)
        
        # Write table metadata to table.ttl
        table_ttl_path = self.output_dir / "table.ttl"
        self.graph.serialize(table_ttl_path, format="turtle")
        log.info(f"Wrote table metadata to {table_ttl_path}")
        
        # Also write to full.ttl
        full_ttl_path = self.output_dir / "full.ttl"
        self.graph.serialize(full_ttl_path, format="turtle")
        
        # Process CSV rows and stream to files
        chunk_files = []
        current_chunk = 0
        rows_in_chunk = 0
        chunk_file = None
        full_file = open(full_ttl_path, 'a', encoding='utf-8')
        
        # Add comment to separate metadata from rows
        full_file.write("\n# CSV Row Data\n")
        
        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            row_count = 0
            
            for row_idx, row in enumerate(reader):
                if max_rows and row_idx >= max_rows:
                    break
                    
                # Start new chunk if needed
                if rows_in_chunk == 0:
                    if chunk_file:
                        chunk_file.close()
                    chunk_filename = f"chunk_{current_chunk:04d}.ttl"
                    chunk_path = self.output_dir / chunk_filename
                    chunk_files.append(chunk_filename)
                    chunk_file = open(chunk_path, 'w', encoding='utf-8')
                    
                    # Write prefixes to chunk file (for readability)
                    for prefix, ns in self.graph.namespaces():
                        if prefix:
                            chunk_file.write(f"@prefix {prefix}: <{ns}> .\n")
                    chunk_file.write("\n")
                    
                # Create row URI
                row_uri = URIRef(f"https://example.org/data/row/{table_name}/{row_idx}")
                
                # Write row type
                self.write_row_triple(full_file, row_uri, RDF.type, URIRef("https://example.org/ontology#Row"))
                self.write_row_triple(chunk_file, row_uri, RDF.type, URIRef("https://example.org/ontology#Row"))
                
                # Write row properties and cells
                for col_idx, (header, value) in enumerate(row.items()):
                    if value and value.strip():
                        # Create cell URI
                        cell_uri = URIRef(f"https://example.org/data/cell/{table_name}/{row_idx}/{col_idx}")
                        column_uri = URIRef(f"https://example.org/data/column/{table_name}/{col_idx}")
                        
                        # Write cell type
                        self.write_row_triple(full_file, cell_uri, RDF.type, URIRef("https://example.org/ontology#Cell"))
                        self.write_row_triple(chunk_file, cell_uri, RDF.type, URIRef("https://example.org/ontology#Cell"))
                        
                        # Link cell to row and column
                        self.write_row_triple(full_file, cell_uri, URIRef("https://example.org/ontology#hasRow"), row_uri)
                        self.write_row_triple(chunk_file, cell_uri, URIRef("https://example.org/ontology#hasRow"), row_uri)
                        self.write_row_triple(full_file, cell_uri, URIRef("https://example.org/ontology#hasColumn"), column_uri)
                        self.write_row_triple(chunk_file, cell_uri, URIRef("https://example.org/ontology#hasColumn"), column_uri)
                        
                        # Write cell value
                        value_prop = URIRef("https://example.org/ontology#hasValue")
                        try:
                            # Try integer
                            int_val = int(value)
                            self.write_row_triple(full_file, cell_uri, value_prop, int_val, XSD.integer)
                            self.write_row_triple(chunk_file, cell_uri, value_prop, int_val, XSD.integer)
                        except ValueError:
                            try:
                                # Try float
                                float_val = float(value)
                                self.write_row_triple(full_file, cell_uri, value_prop, float_val, XSD.decimal)
                                self.write_row_triple(chunk_file, cell_uri, value_prop, float_val, XSD.decimal)
                            except ValueError:
                                # Default to string
                                self.write_row_triple(full_file, cell_uri, value_prop, value)
                                self.write_row_triple(chunk_file, cell_uri, value_prop, value)
                        
                        # Also link row to cell (for easy navigation)
                        self.write_row_triple(full_file, row_uri, URIRef("https://example.org/ontology#hasCell"), cell_uri)
                        self.write_row_triple(chunk_file, row_uri, URIRef("https://example.org/ontology#hasCell"), cell_uri)
                
                row_count += 1
                rows_in_chunk += 1
                
                if rows_in_chunk >= rows_per_chunk:
                    rows_in_chunk = 0
                    current_chunk += 1
                    
                if row_count % 1000 == 0:
                    log.info(f"Processed {row_count} rows")
                    
        # Close files
        if chunk_file:
            chunk_file.close()
        full_file.close()
        
        log.info(f"Processed {row_count} rows into {len(chunk_files)} chunks")
        
        # Create manifest
        manifest = {
            "table_name": table_name,
            "table_uri": str(table_uri),
            "dataset_uri": str(table_uri),  # For compatibility with viewer
            "created": datetime.now().isoformat(),
            "row_count": row_count,
            "chunk_size": rows_per_chunk,
            "files": {
                "metadata": "table.ttl",
                "full": "full.ttl",
                "chunks": chunk_files
            }
        }
        
        manifest_path = self.output_dir / "table_manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
            
        log.info(f"Wrote manifest to {manifest_path}")
        
        # Generate viewer instance
        self.generate_viewer()
        
    def generate_viewer(self):
        """Generate rdftab viewer instance"""
        viewer_dir = self.output_dir / "viewer"
        viewer_dir.mkdir(exist_ok=True)
        
        # Copy viewer template files
        template_dir = Path(__file__).parent / "viewer_template"
        if template_dir.exists():
            import shutil
            # Copy all files and directories
            for item in template_dir.iterdir():
                if item.is_file():
                    shutil.copy2(item, viewer_dir / item.name)
                elif item.is_dir():
                    # Copy subdirectories (like assets)
                    shutil.copytree(item, viewer_dir / item.name, dirs_exist_ok=True)
                    
            log.info(f"Generated viewer in {viewer_dir}")
            
            # Copy manifest to viewer directory for easy access
            manifest_src = self.output_dir / "table_manifest.json"
            if manifest_src.exists():
                shutil.copy2(manifest_src, viewer_dir / "manifest.json")
                
            # Also copy table.ttl and first chunk for local access
            table_src = self.output_dir / "table.ttl"
            if table_src.exists():
                shutil.copy2(table_src, viewer_dir / "table.ttl")
                
            # Copy first chunk if it exists
            chunk_src = self.output_dir / "chunk_0000.ttl"
            if chunk_src.exists():
                shutil.copy2(chunk_src, viewer_dir / "chunk_0000.ttl")
        else:
            log.warning(f"Viewer template not found at {template_dir}")


def main():
    parser = argparse.ArgumentParser(description="Convert CSV to RDF using rdflib")
    parser.add_argument("csv_file", help="Path to input CSV file")
    parser.add_argument("--annotations", default="annotations/fdic_banks.ttl",
                       help="Path to annotations TTL file (default: annotations/fdic_banks.ttl)")
    parser.add_argument("--output-dir", "-o",
                       help="Output directory for RDF files (auto-generated if not specified)")
    parser.add_argument("--rows-per-chunk", type=int, default=1000,
                       help="Number of rows per chunk file (default: 1000)")
    parser.add_argument("--max-rows", type=int,
                       help="Maximum number of rows to process (for testing)")
    parser.add_argument("--server", action="store_true",
                       help="Start a local HTTP server for the viewer")
    parser.add_argument("--port", type=int, default=8000,
                       help="Port for the HTTP server (default: 8000)")
    
    args = parser.parse_args()
    
    # Convert paths
    csv_path = Path(args.csv_file)
    annotations_path = Path(args.annotations)
    
    # Auto-generate output directory if not specified
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        # Generate output directory name based on timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(f"fdic_output_{timestamp}")
    
    # Check input files exist
    if not csv_path.exists():
        log.error(f"CSV file not found: {csv_path}")
        return 1
        
    # Create converter
    converter = CSV2RDF(output_dir)
    
    # Load annotations if file exists
    if annotations_path.exists():
        converter.load_annotations(annotations_path)
    else:
        log.warning(f"Annotations file not found: {annotations_path}")
        
    # Process CSV
    converter.process_csv(csv_path, args.max_rows, args.rows_per_chunk)
    
    # Start server if requested
    if args.server:
        import http.server
        import socketserver
        import os
        import webbrowser
        
        viewer_dir = output_dir / "viewer"
        
        # Change to viewer directory
        os.chdir(viewer_dir)
        
        # Determine the URL
        url = f"http://localhost:{args.port}/index-viewer.html"
        
        # Create server
        Handler = http.server.SimpleHTTPRequestHandler
        with socketserver.TCPServer(("", args.port), Handler) as httpd:
            log.info(f"Starting server at http://localhost:{args.port}")
            log.info(f"Serving files from {viewer_dir}")
            log.info("")
            log.info(f"Table viewer URL: {url}")
            log.info("")
            log.info("Press Ctrl+C to stop the server")
            
            # Open browser
            try:
                webbrowser.open(url)
                log.info(f"Opening browser at {url}")
            except Exception as e:
                log.warning(f"Could not open browser: {e}")
            
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                log.info("\nServer stopped")
    
    return 0


if __name__ == "__main__":
    exit(main())