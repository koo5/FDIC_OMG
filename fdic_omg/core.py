#!/usr/bin/env python3
"""
FDIC RDF Core - Core semantic augmentation logic

This module contains the core transformation logic for converting FDIC CSV data 
to RDF with ontology mappings, without any CLI or framework dependencies.
"""

import csv
import json
import math
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

import rdflib
from rdflib import Graph, URIRef, Literal, Namespace, BNode
from rdflib.namespace import RDF, RDFS, XSD, FOAF, DCTERMS
from rdflib.collection import Collection

# Setup logging
log = logging.getLogger(__name__)

# Define namespaces
FIBO = Namespace("https://spec.edmcouncil.org/fibo/ontology/")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")
GEONAMES = Namespace("http://www.geonames.org/ontology#")
PROV = Namespace("http://www.w3.org/ns/prov#")
DCAT = Namespace("http://www.w3.org/ns/dcat#")


class FDICRDFGenerator:
    """Core RDF generation logic for FDIC CSV files"""
    
    def __init__(self, result_uri: str):
        self.result_uri = result_uri
        self.graph = Graph()
        self._bind_namespaces()
        self.column_mappings = self._load_column_mappings()
        
    def _bind_namespaces(self):
        """Bind common namespaces to the RDF graph"""
        self.graph.bind("fibo", FIBO)
        self.graph.bind("geo", GEO)
        self.graph.bind("geonames", GEONAMES)
        self.graph.bind("prov", PROV)
        self.graph.bind("dcat", DCAT)
        self.graph.bind("foaf", FOAF)
        self.graph.bind("dcterms", DCTERMS)
        
    def _load_column_mappings(self) -> Dict[str, Dict]:
        """Load semantic mappings for FDIC CSV columns from TTL file"""
        mappings = {}
        
        # Load the TTL file
        mappings_file = Path(__file__).parent / "column_mappings.ttl"
        if not mappings_file.exists():
            log.error(f"Column mappings file not found: {mappings_file}")
            return {}
            
        mapping_graph = Graph()
        mapping_graph.parse(mappings_file, format="turtle")
        
        # Define namespace for FDIC mappings
        FDIC_NS = Namespace("http://example.org/fdic/ontology#")
        
        # Query for all column mappings
        query = """
        PREFIX fdic: <http://example.org/fdic/ontology#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dcterms: <http://purl.org/dc/terms/>
        
        SELECT ?column ?columnName ?semanticType ?dataType ?description ?seeAlso
        WHERE {
            ?column a fdic:ColumnMapping ;
                    fdic:columnName ?columnName ;
                    fdic:semanticType ?semanticType ;
                    fdic:dataType ?dataType .
            OPTIONAL { ?column dcterms:description ?description }
            OPTIONAL { ?column rdfs:seeAlso ?seeAlso }
        }
        """
        
        results = mapping_graph.query(query)
        for row in results:
            column_name = str(row.columnName)
            mappings[column_name] = {
                "type": str(row.semanticType),
                "data_type": str(row.dataType),
                "description": str(row.description) if row.description else "",
                "ontology_ref": str(row.seeAlso) if row.seeAlso else ""
            }
        
        log.info(f"Loaded {len(mappings)} column mappings from {mappings_file}")
        return mappings
    
    def process_csv(self, csv_path: Path, max_rows: Optional[int] = None) -> Dict[str, Any]:
        """Process FDIC CSV file and generate RDF"""
        log.info(f"Processing FDIC CSV: {csv_path}")
        
        dataset_uri = URIRef(self.result_uri + "dataset")
        csv_file_uri = URIRef(self.result_uri + f"csv_file_{csv_path.stem}")
        
        self._add_dataset_metadata(dataset_uri, csv_file_uri, csv_path)
        results = self._process_csv_data(csv_path, csv_file_uri, max_rows)
        
        return {
            "dataset_uri": str(dataset_uri),
            "csv_uri": str(csv_file_uri), 
            "rows_processed": results["rows_processed"],
            "columns_mapped": results["columns_mapped"],
            "triples_generated": len(self.graph),
            "graph": self.graph,
            "column_mappings": self.column_mappings
        }
    
    def _add_dataset_metadata(self, dataset_uri: URIRef, csv_uri: URIRef, csv_path: Path):
        """Add dataset-level metadata to RDF graph"""
        self.graph.add((dataset_uri, RDF.type, DCAT.Dataset))
        self.graph.add((dataset_uri, DCTERMS.title, Literal("FDIC Insured Banks Dataset")))
        self.graph.add((dataset_uri, DCTERMS.description, 
                       Literal("Dataset containing information about FDIC-insured banks in the United States")))
        self.graph.add((dataset_uri, DCTERMS.source, Literal("Federal Deposit Insurance Corporation (FDIC)")))
        self.graph.add((dataset_uri, DCTERMS.created, Literal(datetime.now().isoformat(), datatype=XSD.dateTime)))
        
        # CSV file metadata  
        self.graph.add((csv_uri, RDF.type, DCAT.Distribution))
        self.graph.add((csv_uri, DCTERMS.title, Literal(f"CSV File: {csv_path.name}")))
        self.graph.add((csv_uri, DCAT.mediaType, Literal("text/csv")))
        self.graph.add((dataset_uri, DCAT.distribution, csv_uri))
        
        # Provenance
        activity_uri = URIRef(self.result_uri + "semantic_augmentation")
        self.graph.add((activity_uri, RDF.type, PROV.Activity))
        self.graph.add((activity_uri, PROV.startedAtTime, Literal(datetime.now().isoformat(), datatype=XSD.dateTime)))
        self.graph.add((activity_uri, PROV.used, csv_uri))
        self.graph.add((dataset_uri, PROV.wasGeneratedBy, activity_uri))
        
    def _process_csv_data(self, csv_path: Path, csv_uri: URIRef, max_rows: Optional[int]) -> Dict[str, int]:
        """Process CSV rows and add semantic annotations"""
        rows_processed = 0
        columns_found = set()
        
        with open(csv_path, 'r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            headers = reader.fieldnames
            
            # Create ordered list of columns
            column_list = []
            column_uris = {}
            for i, header in enumerate(headers):
                column_uri = URIRef(self.result_uri + f"column_{i}_{header}")
                self._add_column_metadata(column_uri, csv_uri, header, i)
                columns_found.add(header)
                column_list.append(column_uri)
                column_uris[header] = column_uri
            
            # Create RDF list for columns
            columns_collection = Collection(self.graph, BNode())
            for col_uri in column_list:
                columns_collection.append(col_uri)
            self.graph.add((csv_uri, URIRef(self.result_uri + "hasColumnList"), columns_collection.uri))
            
            # Create ordered list of rows
            row_list = []
            for row_idx, row in enumerate(reader):
                row_uri = URIRef(self.result_uri + f"row_{row_idx}")
                self._add_row_metadata(row_uri, csv_uri, row, row_idx, column_uris)
                row_list.append(row_uri)
                rows_processed += 1
                
                if max_rows and rows_processed >= max_rows:
                    log.info(f"Limiting processing to first {rows_processed} rows")
                    break
            
            # Create RDF list for rows
            rows_collection = Collection(self.graph, BNode())
            for row_uri in row_list:
                rows_collection.append(row_uri)
            self.graph.add((csv_uri, URIRef(self.result_uri + "hasRowList"), rows_collection.uri))
        
        mapped_columns = len([h for h in headers if h in self.column_mappings])
        return {"rows_processed": rows_processed, "columns_mapped": mapped_columns}
    
    def _add_column_metadata(self, column_uri: URIRef, csv_uri: URIRef, header: str, index: int):
        """Add semantic metadata for a CSV column"""
        column_class = URIRef(self.result_uri + "Column")
        self.graph.add((column_uri, RDF.type, column_class))
        self.graph.add((column_uri, DCTERMS.title, Literal(header)))
        self.graph.add((column_uri, URIRef(self.result_uri + "columnIndex"), Literal(index, datatype=XSD.integer)))
        self.graph.add((csv_uri, URIRef(self.result_uri + "hasColumn"), column_uri))
        
        # Add ontology mapping if available
        if header in self.column_mappings:
            mapping = self.column_mappings[header]
            self.graph.add((column_uri, RDFS.seeAlso, URIRef(mapping["ontology_ref"])))
            self.graph.add((column_uri, DCTERMS.description, Literal(mapping["description"])))
            self.graph.add((column_uri, URIRef(self.result_uri + "dataType"), Literal(mapping["data_type"])))
            self.graph.add((column_uri, URIRef(self.result_uri + "semanticType"), Literal(mapping["type"])))
    
    def _add_row_metadata(self, row_uri: URIRef, csv_uri: URIRef, row: Dict, index: int, column_uris: Dict[str, URIRef]):
        """Add semantic metadata for a CSV row"""
        bank_record_class = URIRef(self.result_uri + "BankRecord")
        self.graph.add((row_uri, RDF.type, bank_record_class))
        self.graph.add((row_uri, URIRef(self.result_uri + "rowIndex"), Literal(index, datatype=XSD.integer)))
        self.graph.add((csv_uri, URIRef(self.result_uri + "hasRow"), row_uri))
        
        # Create ordered list of cells matching column order
        cell_list = []
        for column, value in row.items():
            if column in column_uris:
                cell_uri = URIRef(self.result_uri + f"cell_{index}_{column}")
                cell_list.append((column, cell_uri, value))
                if value and value.strip():
                    self._add_cell_metadata(cell_uri, row_uri, column, value)
                else:
                    # Add empty cell
                    cell_class = URIRef(self.result_uri + "Cell")
                    self.graph.add((cell_uri, RDF.type, cell_class))
                    self.graph.add((cell_uri, URIRef(self.result_uri + "columnName"), Literal(column)))
                    self.graph.add((cell_uri, URIRef(self.result_uri + "rawValue"), Literal("")))
                    self.graph.add((row_uri, URIRef(self.result_uri + "hasCell"), cell_uri))
    
    def _add_cell_metadata(self, cell_uri: URIRef, row_uri: URIRef, column: str, value: str):
        """Add semantic metadata for individual cell values"""
        cell_class = URIRef(self.result_uri + "Cell")
        self.graph.add((cell_uri, RDF.type, cell_class))
        self.graph.add((cell_uri, URIRef(self.result_uri + "columnName"), Literal(column)))
        self.graph.add((cell_uri, URIRef(self.result_uri + "rawValue"), Literal(value)))
        self.graph.add((row_uri, URIRef(self.result_uri + "hasCell"), cell_uri))
        
        # Apply semantic typing based on column mappings
        if column in self.column_mappings:
            mapping = self.column_mappings[column]
            typed_value = self._convert_value_type(value, mapping["data_type"])
            if typed_value is not None:
                self.graph.add((cell_uri, URIRef(self.result_uri + "typedValue"), typed_value))
                
            # Add specific semantic properties
            if mapping["type"] == "coordinate" and column in ["X", "LONGITUDE"]:
                self.graph.add((cell_uri, GEO.longitude, typed_value))
            elif mapping["type"] == "coordinate" and column in ["Y", "LATITUDE"]:
                self.graph.add((cell_uri, GEO.latitude, typed_value))
            elif mapping["type"] == "bank_name":
                self.graph.add((cell_uri, FOAF.name, Literal(value)))
    
    def _convert_value_type(self, value: str, data_type: str) -> Optional[Literal]:
        """Convert string value to appropriate RDF literal type"""
        try:
            if data_type == "decimal":
                return Literal(float(value), datatype=XSD.decimal)
            elif data_type == "integer":
                return Literal(int(value), datatype=XSD.integer)
            else:
                return Literal(value, datatype=XSD.string)
        except ValueError:
            log.warning(f"Could not convert '{value}' to {data_type}")
            return None
    
    def generate_viewer_output(self, csv_path: Path, output_dir: Path, rows_per_page: int = 1000) -> Dict[str, Any]:
        """Generate standalone tabular data viewer with pagination"""
        log.info(f"Generating viewer output for {csv_path} in {output_dir}")
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy pre-built Vue app files
        rdftab_build_dir = Path(__file__).parent.parent.parent.parent.parent / "static" / "rdftab"
        if rdftab_build_dir.exists():
            # Copy all built files
            for item in rdftab_build_dir.rglob("*"):
                if item.is_file():
                    rel_path = item.relative_to(rdftab_build_dir)
                    dest_path = output_dir / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest_path)
        else:
            log.warning(f"RDFtab build directory not found: {rdftab_build_dir}")
        
        # Process CSV and generate data files
        with open(csv_path, 'r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            headers = list(reader.fieldnames)
            rows = list(reader)
        
        total_rows = len(rows)
        total_pages = math.ceil(total_rows / rows_per_page)
        
        # Generate manifest
        manifest = {
            "dataset_uri": self.result_uri + "dataset",
            "title": f"FDIC Dataset: {csv_path.name}",
            "description": "FDIC-Insured Institutions Dataset with semantic annotations",
            "total_rows": total_rows,
            "rows_per_page": rows_per_page,
            "total_pages": total_pages,
            "headers": headers,
            "column_mappings": self._get_column_mappings_for_viewer()
        }
        
        # Write manifest
        with open(output_dir / "manifest.json", 'w') as f:
            json.dump(manifest, f, indent=2)
        
        # Generate paginated data and cell metadata
        for page_num in range(total_pages):
            start_idx = page_num * rows_per_page
            end_idx = min(start_idx + rows_per_page, total_rows)
            
            # Generate page data (simplified array format for efficiency)
            page_data = {
                "page": page_num,
                "start_row": start_idx,
                "end_row": end_idx - 1,
                "rows": []
            }
            
            # Generate cell metadata
            cells_data = {}
            
            for i in range(start_idx, end_idx):
                row = rows[i]
                row_index = i
                
                # Add row data as array (more compact)
                page_data["rows"].append([row.get(col, "") for col in headers])
                
                # Generate cell metadata for non-empty cells
                for col_idx, col in enumerate(headers):
                    value = row.get(col, "")
                    if value and value.strip():
                        cell_key = f"row_{row_index}/col_{col}"
                        cells_data[cell_key] = self._generate_cell_metadata(row_index, col, value, col_idx)
            
            # Write page data
            with open(output_dir / f"page_{page_num}.json", 'w') as f:
                json.dump(page_data, f, indent=2)
            
            # Write cell metadata
            with open(output_dir / f"cells_{page_num}.json", 'w') as f:
                json.dump(cells_data, f, indent=2)
        
        log.info(f"Generated viewer with {total_pages} pages in {output_dir}")
        return {
            "output_dir": str(output_dir),
            "total_rows": total_rows,
            "total_pages": total_pages,
            "manifest_file": str(output_dir / "manifest.json")
        }
    
    def _get_column_mappings_for_viewer(self) -> Dict[str, Dict]:
        """Get simplified column mappings for the viewer"""
        viewer_mappings = {}
        for col, mapping in self.column_mappings.items():
            viewer_mappings[col] = {
                "label": col.replace("_", " ").title(),
                "description": mapping.get("description", ""),
                "dataType": mapping.get("data_type", "string"),
                "semanticType": mapping.get("type", ""),
                "ontologyRef": mapping.get("ontology_ref", ""),
                "seeAlso": [mapping.get("ontology_ref")] if mapping.get("ontology_ref") else []
            }
        return viewer_mappings
    
    def _generate_cell_metadata(self, row_index: int, column: str, value: str, col_index: int) -> Dict[str, Any]:
        """Generate metadata for a specific cell"""
        cell_uri = f"{self.result_uri}#row_{row_index}/col_{column}"
        
        # Get column mapping if available
        mapping = self.column_mappings.get(column, {})
        
        # Generate basic cell metadata
        metadata = {
            "uri": cell_uri,
            "value": value,
            "row_index": row_index,
            "column_name": column,
            "column_index": col_index,
            "data_type": mapping.get("data_type", "string")
        }
        
        # Add typed value if possible
        typed_value = self._convert_value_type(value, mapping.get("data_type", "string"))
        if typed_value is not None:
            if mapping.get("data_type") == "decimal":
                metadata["typed_value"] = float(value)
            elif mapping.get("data_type") == "integer":
                metadata["typed_value"] = int(value)
            else:
                metadata["typed_value"] = value
        
        # Add semantic information
        if mapping:
            metadata["semantic_type"] = mapping.get("type", "")
            metadata["description"] = mapping.get("description", "")
            metadata["ontology_ref"] = mapping.get("ontology_ref", "")
        
        # Add external links based on column type and value
        metadata["links"] = self._generate_external_links(column, value, mapping)
        
        # Add properties specific to the column type
        metadata["properties"] = self._generate_cell_properties(column, value, mapping)
        
        return metadata
    
    def _generate_external_links(self, column: str, value: str, mapping: Dict) -> List[Dict[str, str]]:
        """Generate external links for a cell based on its type and value"""
        links = []
        
        # Add ontology reference link
        if mapping.get("ontology_ref"):
            links.append({
                "url": mapping["ontology_ref"],
                "label": "Ontology Reference",
                "type": "ontology"
            })
        
        # Add specific links based on column type
        if column == "CERT" and value.isdigit():
            links.append({
                "url": f"https://www.fdic.gov/bank/individual/failed/cert/{value}.html",
                "label": "FDIC Bank Profile",
                "type": "external_data"
            })
        
        elif column in ["NAME"]:
            links.append({
                "url": f"https://en.wikipedia.org/wiki/{value.replace(' ', '_')}",
                "label": "Wikipedia",
                "type": "reference"
            })
        
        elif column in ["CITY", "STNAME"]:
            links.append({
                "url": f"https://www.geonames.org/search.html?q={value.replace(' ', '+')}",
                "label": "GeoNames",
                "type": "geographic"
            })
        
        return links
    
    def _generate_cell_properties(self, column: str, value: str, mapping: Dict) -> Dict[str, Any]:
        """Generate additional properties for a cell"""
        properties = {}
        
        # Add validation status
        properties["is_valid"] = self._validate_cell_value(column, value, mapping)
        
        # Add column-specific properties
        if column == "CERT":
            properties["issuer"] = "Federal Deposit Insurance Corporation"
            properties["identifier_type"] = "FDIC Certificate Number"
        
        elif column in ["LONGITUDE", "X"]:
            try:
                lon = float(value)
                properties["coordinate_type"] = "longitude"
                properties["hemisphere"] = "East" if lon >= 0 else "West"
                properties["decimal_degrees"] = lon
            except ValueError:
                pass
        
        elif column in ["LATITUDE", "Y"]:
            try:
                lat = float(value)
                properties["coordinate_type"] = "latitude"
                properties["hemisphere"] = "North" if lat >= 0 else "South"
                properties["decimal_degrees"] = lat
            except ValueError:
                pass
        
        elif column == "ZIP":
            properties["postal_system"] = "United States Postal Service"
            properties["format"] = "5-digit ZIP code"
        
        return properties
    
    def _validate_cell_value(self, column: str, value: str, mapping: Dict) -> bool:
        """Validate a cell value against its expected type and constraints"""
        if not value or not value.strip():
            return False
        
        data_type = mapping.get("data_type", "string")
        
        try:
            if data_type == "integer":
                int(value)
            elif data_type == "decimal":
                float(value)
            # String values are always valid if not empty
            return True
        except ValueError:
            return False