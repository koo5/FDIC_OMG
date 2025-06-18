#!/usr/bin/env python3
"""
FDIC RDF Core - Core semantic augmentation logic

This module contains the core transformation logic for converting FDIC CSV data 
to RDF with ontology mappings, without any CLI or framework dependencies.
"""

import csv
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

import rdflib
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS, XSD, FOAF, DCTERMS

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
        """Load semantic mappings for FDIC CSV columns"""
        return {
            "X": {
                "type": "coordinate", 
                "ontology_ref": str(GEO.hasGeometry),
                "description": "Longitude coordinate",
                "data_type": "decimal"
            },
            "Y": {
                "type": "coordinate",
                "ontology_ref": str(GEO.hasGeometry), 
                "description": "Latitude coordinate",
                "data_type": "decimal"
            },
            "LONGITUDE": {
                "type": "coordinate",
                "ontology_ref": str(GEO.longitude),
                "description": "Geographic longitude",
                "data_type": "decimal"
            },
            "LATITUDE": {
                "type": "coordinate", 
                "ontology_ref": str(GEO.latitude),
                "description": "Geographic latitude",
                "data_type": "decimal"
            },
            "NAME": {
                "type": "bank_name",
                "ontology_ref": str(FIBO + "FormalOrganization/hasLegalName"),
                "description": "Legal name of financial institution",
                "data_type": "string"
            },
            "ADDRESS": {
                "type": "address",
                "ontology_ref": str(FIBO + "Places/Address"),
                "description": "Physical address",
                "data_type": "string"
            },
            "CITY": {
                "type": "location",
                "ontology_ref": str(GEONAMES.name),
                "description": "City name",
                "data_type": "string"
            },
            "STALP": {
                "type": "state_code",
                "ontology_ref": str(GEONAMES.stateCode),
                "description": "State abbreviation",
                "data_type": "string"
            },
            "STNAME": {
                "type": "state_name", 
                "ontology_ref": str(GEONAMES.name),
                "description": "State name",
                "data_type": "string"
            },
            "ZIP": {
                "type": "postal_code",
                "ontology_ref": str(FIBO + "Places/PostalCode"),
                "description": "ZIP postal code",
                "data_type": "string"
            },
            "CERT": {
                "type": "fdic_certificate",
                "ontology_ref": str(FIBO + "BusinessEntities/CorporateIdentifier"),
                "description": "FDIC Certificate Number",
                "data_type": "integer"
            },
            "BKCLASS": {
                "type": "bank_class",
                "ontology_ref": str(FIBO + "BusinessEntities/OrganizationClassification"),
                "description": "Bank classification code",
                "data_type": "string"
            },
            "SERVTYPE_DESC": {
                "type": "service_description",
                "ontology_ref": str(FIBO + "ProductsAndServices/Service"),
                "description": "Type of banking service provided",
                "data_type": "string"
            }
        }
    
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
            
            # Add column metadata
            for i, header in enumerate(headers):
                column_uri = URIRef(self.result_uri + f"column_{i}_{header}")
                self._add_column_metadata(column_uri, csv_uri, header, i)
                columns_found.add(header)
            
            # Process data rows
            for row_idx, row in enumerate(reader):
                row_uri = URIRef(self.result_uri + f"row_{row_idx}")
                self._add_row_metadata(row_uri, csv_uri, row, row_idx)
                rows_processed += 1
                
                if max_rows and rows_processed >= max_rows:
                    log.info(f"Limiting processing to first {rows_processed} rows")
                    break
        
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
    
    def _add_row_metadata(self, row_uri: URIRef, csv_uri: URIRef, row: Dict, index: int):
        """Add semantic metadata for a CSV row"""
        bank_record_class = URIRef(self.result_uri + "BankRecord")
        self.graph.add((row_uri, RDF.type, bank_record_class))
        self.graph.add((row_uri, URIRef(self.result_uri + "rowIndex"), Literal(index, datatype=XSD.integer)))
        self.graph.add((csv_uri, URIRef(self.result_uri + "hasRow"), row_uri))
        
        # Add cell values with semantic annotations
        for column, value in row.items():
            if value and value.strip():
                cell_uri = URIRef(self.result_uri + f"cell_{index}_{column}")
                self._add_cell_metadata(cell_uri, row_uri, column, value)
    
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