#!/usr/bin/env python3
"""
Format Converter for FDIC Column Mappings

Converts between different mapping format representations:
- TTL (Turtle RDF)
- JSON-LD
- YAML
"""

import json
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, XSD, OWL, DCTERMS, FOAF

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Define namespaces
FDIC = Namespace("http://example.org/fdic/ontology#")
FIBO = Namespace("https://spec.edmcouncil.org/fibo/ontology/")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")
GEONAMES = Namespace("http://www.geonames.org/ontology#")
SCHEMA = Namespace("https://schema.org/")
VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
PROV = Namespace("http://www.w3.org/ns/prov#")


class FDICMappingConverter:
    """Converter between different FDIC column mapping formats"""
    
    def __init__(self):
        self.graph = Graph()
        self._bind_namespaces()
        
    def _bind_namespaces(self):
        """Bind common namespaces to the RDF graph"""
        self.graph.bind("fdic", FDIC)
        self.graph.bind("fibo", FIBO)
        self.graph.bind("geo", GEO)
        self.graph.bind("geonames", GEONAMES)
        self.graph.bind("schema", SCHEMA)
        self.graph.bind("vcard", VCARD)
        self.graph.bind("dcat", DCAT)
        self.graph.bind("prov", PROV)
        self.graph.bind("dcterms", DCTERMS)
        self.graph.bind("foaf", FOAF)
        self.graph.bind("owl", OWL)
        
    def ttl_to_dict(self, ttl_path: Path) -> Dict[str, Any]:
        """Convert TTL file to dictionary representation"""
        log.info(f"Converting TTL to dict: {ttl_path}")
        
        # Parse TTL
        self.graph.parse(ttl_path, format="turtle")
        
        # Extract dataset metadata
        dataset_info = self._extract_dataset_metadata()
        
        # Extract resource documentation
        resources = self._extract_resources()
        
        # Extract column mappings
        columns = self._extract_column_mappings()
        
        # Build result dictionary
        result = {
            "dataset": dataset_info,
            "resources": resources,
            "columns": columns,
            "metadata": {
                "format_version": "1.0",
                "created": "2025-06-20",
                "creator": "FDIC OMG Semantic Augmentation System",
                "license": "https://creativecommons.org/licenses/by/4.0/"
            }
        }
        
        return result
        
    def _extract_dataset_metadata(self) -> Dict[str, Any]:
        """Extract dataset metadata from RDF graph"""
        dataset_uri = URIRef("http://example.org/fdic/ontology#FDICBankDataset")
        
        dataset = {
            "title": self._get_literal(dataset_uri, DCTERMS.title),
            "description": self._get_literal(dataset_uri, DCTERMS.description),
            "keywords": self._get_literals(dataset_uri, DCAT.keyword),
            "spatial": self._get_literal(dataset_uri, DCTERMS.spatial),
            "temporal": "Continuously updated"
        }
        
        # Extract publisher info
        publisher_node = self.graph.value(dataset_uri, DCTERMS.publisher)
        if publisher_node:
            dataset["publisher"] = {
                "name": self._get_literal(publisher_node, FOAF.name),
                "homepage": str(self.graph.value(publisher_node, FOAF.homepage, default=""))
            }
            
        return dataset
        
    def _extract_resources(self) -> Dict[str, Dict[str, Any]]:
        """Extract cited resources from RDF graph"""
        resources = {}
        
        # Query for all resources
        resource_class = FDIC.CitedResources
        for resource_uri in self.graph.subjects(RDF.type, resource_class):
            resource_id = str(resource_uri).split("_")[1] if "_" in str(resource_uri) else str(resource_uri).split("#")[-1]
            
            resources[resource_id] = {
                "name": self._get_literal(resource_uri, RDFS.label),
                "description": self._get_literal(resource_uri, DCTERMS.description),
                "homepage": str(self.graph.value(resource_uri, FOAF.homepage, default="")),
                "type": self._get_literal(resource_uri, DCTERMS.type)
            }
            
            # Add source if available
            source = self.graph.value(resource_uri, DCTERMS.source)
            if source:
                resources[resource_id]["source"] = str(source)
                
        return resources
        
    def _extract_column_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Extract column mappings from RDF graph"""
        columns = {}
        
        # Query for all column mappings
        mapping_class = FDIC.ColumnMapping
        for column_uri in self.graph.subjects(RDF.type, mapping_class):
            column_name = self._get_literal(column_uri, FDIC.columnName)
            if not column_name:
                continue
                
            column_data = {
                "label": self._get_literal(column_uri, RDFS.label),
                "description": self._get_literal(column_uri, DCTERMS.description),
                "semantic_type": self._get_literal(column_uri, FDIC.semanticType),
                "data_type": self._get_literal(column_uri, FDIC.dataType),
                "comments": self._get_literal(column_uri, RDFS.comment)
            }
            
            # Extract mappings
            mappings = []
            see_also_values = list(self.graph.objects(column_uri, RDFS.seeAlso))
            for see_also in see_also_values:
                mapping = {"property": str(see_also)}
                
                # Determine ontology from URI
                uri_str = str(see_also)
                if "fibo" in uri_str:
                    mapping["ontology"] = "FIBO"
                elif "geosparql" in uri_str:
                    mapping["ontology"] = "GeoSPARQL"
                elif "geonames" in uri_str:
                    mapping["ontology"] = "GeoNames"
                elif "schema.org" in uri_str:
                    mapping["ontology"] = "SchemaOrg"
                elif "w3.org/2003/01/geo" in uri_str:
                    mapping["ontology"] = "W3C-WGS84"
                elif "vcard" in uri_str:
                    mapping["ontology"] = "vCard"
                elif "foaf" in uri_str:
                    mapping["ontology"] = "FOAF"
                    
                mappings.append(mapping)
                
            if mappings:
                column_data["mappings"] = mappings
                
            # Extract references
            references = []
            ref_values = list(self.graph.objects(column_uri, DCTERMS.references))
            for ref in ref_values:
                references.append({"url": str(ref), "type": "reference"})
                
            # Add Wikipedia/Wikidata references from seeAlso
            for see_also in see_also_values:
                uri_str = str(see_also)
                if "wikipedia.org" in uri_str:
                    references.append({"url": uri_str, "type": "definition"})
                elif "investopedia.com" in uri_str:
                    references.append({"url": uri_str, "type": "glossary"})
                    
            # Check for sameAs (Wikidata entities)
            same_as = self.graph.value(column_uri, OWL.sameAs)
            if same_as:
                references.append({"url": str(same_as), "type": "wikidata"})
                
            if references:
                column_data["references"] = references
                
            columns[column_name] = column_data
            
        return columns
        
    def dict_to_yaml(self, data: Dict[str, Any], yaml_path: Path):
        """Convert dictionary to YAML file"""
        log.info(f"Writing YAML to: {yaml_path}")
        
        # Add header comment
        yaml_content = """# FDIC Column Mappings - YAML Format
# This file provides semantic mappings for FDIC institution data CSV columns
# Format Version: 1.0
# Created: 2025-06-20
# License: CC BY 4.0

"""
        
        # Write YAML content
        yaml_content += yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
        
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)
            
    def dict_to_jsonld(self, data: Dict[str, Any], jsonld_path: Path):
        """Convert dictionary to JSON-LD file"""
        log.info(f"Writing JSON-LD to: {jsonld_path}")
        
        # Build JSON-LD structure
        jsonld = {
            "@context": self._build_jsonld_context(),
            "@graph": self._build_jsonld_graph(data)
        }
        
        with open(jsonld_path, 'w') as f:
            json.dump(jsonld, f, indent=2)
            
    def yaml_to_ttl(self, yaml_path: Path, ttl_path: Path):
        """Convert YAML file to TTL"""
        log.info(f"Converting YAML to TTL: {yaml_path} -> {ttl_path}")
        
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
            
        self._dict_to_rdf(data)
        self.graph.serialize(destination=ttl_path, format='turtle')
        
    def jsonld_to_ttl(self, jsonld_path: Path, ttl_path: Path):
        """Convert JSON-LD file to TTL"""
        log.info(f"Converting JSON-LD to TTL: {jsonld_path} -> {ttl_path}")
        
        # Parse JSON-LD directly into RDF
        self.graph.parse(jsonld_path, format='json-ld')
        self.graph.serialize(destination=ttl_path, format='turtle')
        
    def _dict_to_rdf(self, data: Dict[str, Any]):
        """Convert dictionary data to RDF triples"""
        # Add ontology metadata
        onto_uri = URIRef("http://example.org/fdic/column-mappings")
        self.graph.add((onto_uri, RDF.type, OWL.Ontology))
        self.graph.add((onto_uri, RDFS.label, Literal("FDIC Column Mappings", lang="en")))
        self.graph.add((onto_uri, DCTERMS.title, Literal("FDIC CSV Column Semantic Mappings", lang="en")))
        
        # Add dataset metadata
        if "dataset" in data:
            self._add_dataset_metadata(data["dataset"])
            
        # Add resources
        if "resources" in data:
            self._add_resources(data["resources"])
            
        # Add column mappings
        if "columns" in data:
            self._add_column_mappings(data["columns"])
            
    def _add_dataset_metadata(self, dataset: Dict[str, Any]):
        """Add dataset metadata to RDF graph"""
        dataset_uri = FDIC.FDICBankDataset
        self.graph.add((dataset_uri, RDF.type, DCAT.Dataset))
        self.graph.add((dataset_uri, DCTERMS.title, Literal(dataset.get("title", ""))))
        self.graph.add((dataset_uri, DCTERMS.description, Literal(dataset.get("description", ""))))
        
        # Add keywords
        for keyword in dataset.get("keywords", []):
            self.graph.add((dataset_uri, DCAT.keyword, Literal(keyword)))
            
        # Add publisher
        if "publisher" in dataset:
            publisher_node = BNode()
            self.graph.add((dataset_uri, DCTERMS.publisher, publisher_node))
            self.graph.add((publisher_node, RDF.type, FOAF.Organization))
            self.graph.add((publisher_node, FOAF.name, Literal(dataset["publisher"].get("name", ""))))
            if "homepage" in dataset["publisher"]:
                self.graph.add((publisher_node, FOAF.homepage, URIRef(dataset["publisher"]["homepage"])))
                
    def _add_resources(self, resources: Dict[str, Dict[str, Any]]):
        """Add resource documentation to RDF graph"""
        for resource_id, resource_data in resources.items():
            resource_uri = FDIC[f"{resource_id}_Resource"]
            self.graph.add((resource_uri, RDF.type, FDIC.CitedResources))
            self.graph.add((resource_uri, RDFS.label, Literal(resource_data.get("name", ""))))
            self.graph.add((resource_uri, DCTERMS.description, Literal(resource_data.get("description", ""))))
            self.graph.add((resource_uri, DCTERMS.type, Literal(resource_data.get("type", ""))))
            
            if "homepage" in resource_data:
                self.graph.add((resource_uri, FOAF.homepage, URIRef(resource_data["homepage"])))
            if "source" in resource_data:
                self.graph.add((resource_uri, DCTERMS.source, URIRef(resource_data["source"])))
                
    def _add_column_mappings(self, columns: Dict[str, Dict[str, Any]]):
        """Add column mappings to RDF graph"""
        for column_name, column_data in columns.items():
            column_uri = FDIC[f"column_{column_name}"]
            self.graph.add((column_uri, RDF.type, FDIC.ColumnMapping))
            self.graph.add((column_uri, FDIC.columnName, Literal(column_name)))
            self.graph.add((column_uri, RDFS.label, Literal(column_data.get("label", ""), lang="en")))
            self.graph.add((column_uri, DCTERMS.description, Literal(column_data.get("description", ""))))
            self.graph.add((column_uri, FDIC.semanticType, Literal(column_data.get("semantic_type", ""))))
            self.graph.add((column_uri, FDIC.dataType, Literal(column_data.get("data_type", ""))))
            
            if "comments" in column_data:
                self.graph.add((column_uri, RDFS.comment, Literal(column_data["comments"], lang="en")))
                
            # Add mappings
            for mapping in column_data.get("mappings", []):
                if "property" in mapping:
                    self.graph.add((column_uri, RDFS.seeAlso, URIRef(mapping["property"])))
                    
            # Add references
            for ref in column_data.get("references", []):
                if "url" in ref:
                    if ref.get("type") == "wikidata":
                        self.graph.add((column_uri, OWL.sameAs, URIRef(ref["url"])))
                    else:
                        self.graph.add((column_uri, RDFS.seeAlso, URIRef(ref["url"])))
                        
    def _build_jsonld_context(self) -> Dict[str, Any]:
        """Build JSON-LD context"""
        return {
            "@version": 1.1,
            "@base": "http://example.org/fdic/",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            "owl": "http://www.w3.org/2002/07/owl#",
            "dcterms": "http://purl.org/dc/terms/",
            "dcat": "http://www.w3.org/ns/dcat#",
            "prov": "http://www.w3.org/ns/prov#",
            "fibo": "https://spec.edmcouncil.org/fibo/ontology/",
            "geo": "http://www.opengis.net/ont/geosparql#",
            "geonames": "http://www.geonames.org/ontology#",
            "schema": "https://schema.org/",
            "vcard": "http://www.w3.org/2006/vcard/ns#",
            "foaf": "http://xmlns.com/foaf/0.1/",
            "fdic": "http://example.org/fdic/ontology#",
            "ColumnMapping": "fdic:ColumnMapping",
            "columnName": "fdic:columnName",
            "semanticType": "fdic:semanticType",
            "dataType": "fdic:dataType"
        }
        
    def _build_jsonld_graph(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build JSON-LD graph from dictionary data"""
        graph = []
        
        # Add ontology node
        graph.append({
            "@id": "column-mappings",
            "@type": "owl:Ontology",
            "label": "FDIC Column Mappings",
            "title": "FDIC CSV Column Semantic Mappings"
        })
        
        # Add dataset node
        if "dataset" in data:
            dataset_node = {
                "@id": "fdic:FDICBankDataset",
                "@type": "Dataset",
                "title": data["dataset"].get("title", ""),
                "description": data["dataset"].get("description", "")
            }
            if "keywords" in data["dataset"]:
                dataset_node["keyword"] = data["dataset"]["keywords"]
            graph.append(dataset_node)
            
        # Add column mappings
        for column_name, column_data in data.get("columns", {}).items():
            column_node = {
                "@id": f"fdic:column_{column_name}",
                "@type": "ColumnMapping",
                "columnName": column_name,
                "label": column_data.get("label", ""),
                "description": column_data.get("description", ""),
                "semanticType": column_data.get("semantic_type", ""),
                "dataType": column_data.get("data_type", "")
            }
            
            # Add seeAlso links
            see_also = []
            for mapping in column_data.get("mappings", []):
                if "property" in mapping:
                    see_also.append(mapping["property"])
            if see_also:
                column_node["seeAlso"] = see_also
                
            graph.append(column_node)
            
        return graph
        
    def _get_literal(self, subject: URIRef, predicate: URIRef, default: str = "") -> str:
        """Get literal value from graph"""
        value = self.graph.value(subject, predicate)
        return str(value) if value else default
        
    def _get_literals(self, subject: URIRef, predicate: URIRef) -> List[str]:
        """Get multiple literal values from graph"""
        return [str(obj) for obj in self.graph.objects(subject, predicate)]


def main():
    """Command line interface for format conversion"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert between FDIC column mapping formats")
    parser.add_argument("input", help="Input file path")
    parser.add_argument("output", help="Output file path")
    parser.add_argument("--from-format", choices=["ttl", "yaml", "jsonld"], 
                       help="Input format (auto-detected if not specified)")
    parser.add_argument("--to-format", choices=["ttl", "yaml", "jsonld"],
                       help="Output format (auto-detected if not specified)")
    
    args = parser.parse_args()
    
    # Auto-detect formats from file extensions
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    if not args.from_format:
        ext = input_path.suffix.lower()
        if ext == ".ttl":
            args.from_format = "ttl"
        elif ext in [".yaml", ".yml"]:
            args.from_format = "yaml"
        elif ext in [".jsonld", ".json"]:
            args.from_format = "jsonld"
        else:
            raise ValueError(f"Cannot auto-detect input format from extension: {ext}")
            
    if not args.to_format:
        ext = output_path.suffix.lower()
        if ext == ".ttl":
            args.to_format = "ttl"
        elif ext in [".yaml", ".yml"]:
            args.to_format = "yaml"
        elif ext in [".jsonld", ".json"]:
            args.to_format = "jsonld"
        else:
            raise ValueError(f"Cannot auto-detect output format from extension: {ext}")
            
    # Perform conversion
    converter = FDICMappingConverter()
    
    if args.from_format == "ttl":
        data = converter.ttl_to_dict(input_path)
        if args.to_format == "yaml":
            converter.dict_to_yaml(data, output_path)
        elif args.to_format == "jsonld":
            converter.dict_to_jsonld(data, output_path)
    elif args.from_format == "yaml":
        if args.to_format == "ttl":
            converter.yaml_to_ttl(input_path, output_path)
        else:
            # Convert via dictionary for other formats
            with open(input_path, 'r') as f:
                data = yaml.safe_load(f)
            if args.to_format == "jsonld":
                converter.dict_to_jsonld(data, output_path)
    elif args.from_format == "jsonld":
        if args.to_format == "ttl":
            converter.jsonld_to_ttl(input_path, output_path)
        else:
            # Parse JSON-LD to dict first
            converter.graph.parse(input_path, format='json-ld')
            data = converter.ttl_to_dict(input_path)  # Re-use extraction logic
            if args.to_format == "yaml":
                converter.dict_to_yaml(data, output_path)
                
    log.info(f"Conversion complete: {input_path} -> {output_path}")


if __name__ == "__main__":
    main()