#!/usr/bin/env python3
"""Convert between YAML and TTL formats for CSV column annotations."""

import yaml
import rdflib
from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, OWL, XSD, DCTERMS
from pathlib import Path
from typing import Dict, List, Any, Optional
import sys
import argparse
from datetime import datetime
import re


# Define standard namespaces
CSVW = Namespace("http://www.w3.org/ns/csvw#")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
VOID = Namespace("http://rdfs.org/ns/void#")
PROV = Namespace("http://www.w3.org/ns/prov#")

# Mapping of relation types to RDF properties
RELATION_MAPPING = {
    "equivalent": OWL.equivalentProperty,
    "exact": OWL.equivalentProperty,
    "similar": RDFS.seeAlso,
    "instance_of": RDF.type,
    "subclass_of": RDFS.subClassOf,
    "related": RDFS.seeAlso,
    "broader": "http://www.w3.org/2004/02/skos/core#broader",
    "narrower": "http://www.w3.org/2004/02/skos/core#narrower"
}

# Mapping of data types to XSD types
DATATYPE_MAPPING = {
    "string": XSD.string,
    "integer": XSD.integer,
    "decimal": XSD.decimal,
    "float": XSD.float,
    "double": XSD.double,
    "boolean": XSD.boolean,
    "date": XSD.date,
    "dateTime": XSD.dateTime,
    "time": XSD.time,
    "anyURI": XSD.anyURI
}


class AnnotationConverter:
    """Generic converter for CSV column annotations between YAML and TTL formats."""
    
    def __init__(self, base_uri: str = "http://example.org/csv2rdf/"):
        """Initialize converter with base URI for annotations."""
        self.base_uri = base_uri
        self.base_ns = Namespace(base_uri)
        
    def yaml_to_ttl(self, yaml_path: Path, ttl_path: Path) -> None:
        """Convert YAML column annotations to TTL format."""
        # Load YAML data
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # Create RDF graph
        g = Graph()
        
        # Bind standard prefixes
        g.bind("", self.base_ns)
        g.bind("csvw", CSVW)
        g.bind("dcat", DCAT)
        g.bind("void", VOID)
        g.bind("prov", PROV)
        g.bind("dcterms", DCTERMS)
        g.bind("owl", OWL)
        g.bind("rdfs", RDFS)
        g.bind("rdf", RDF)
        g.bind("xsd", XSD)
        
        # Add custom namespace prefixes from YAML
        prefixes = data.get('prefixes', {})
        for prefix, uri in prefixes.items():
            g.bind(prefix, Namespace(uri))
        
        # Define ColumnAnnotation class
        column_annotation_class = self.base_ns.ColumnAnnotation
        g.add((column_annotation_class, RDF.type, RDFS.Class))
        g.add((column_annotation_class, RDFS.label, Literal("Column Annotation")))
        g.add((column_annotation_class, RDFS.comment, 
               Literal("Represents semantic annotations for CSV columns")))
        
        # Define custom properties
        column_name_prop = self.base_ns.columnName
        data_type_prop = self.base_ns.dataType
        
        g.add((column_name_prop, RDF.type, RDF.Property))
        g.add((column_name_prop, RDFS.label, Literal("column name")))
        g.add((column_name_prop, RDFS.domain, column_annotation_class))
        
        g.add((data_type_prop, RDF.type, RDF.Property))
        g.add((data_type_prop, RDFS.label, Literal("data type")))
        g.add((data_type_prop, RDFS.domain, column_annotation_class))
        
        # Process column definitions
        columns = data.get('columns', {})
        used_uris = set()
        
        for column_id, column_data in columns.items():
            # Create safe URI for column
            safe_id = re.sub(r'[^a-zA-Z0-9_-]', '_', str(column_id))
            base_uri = f"column_{safe_id}"
            
            # Ensure uniqueness by appending a number if needed
            column_uri_str = base_uri
            counter = 1
            while column_uri_str in used_uris:
                column_uri_str = f"{base_uri}_{counter}"
                counter += 1
            
            used_uris.add(column_uri_str)
            column_uri = self.base_ns[column_uri_str]
            
            # Basic properties
            g.add((column_uri, RDF.type, column_annotation_class))
            g.add((column_uri, column_name_prop, Literal(column_id)))
            
            if 'label' in column_data:
                g.add((column_uri, RDFS.label, Literal(column_data['label'])))
            
            if 'description' in column_data:
                g.add((column_uri, DCTERMS.description, Literal(column_data['description'])))
            
            if 'data_type' in column_data:
                dtype = column_data['data_type']
                xsd_type = DATATYPE_MAPPING.get(dtype, XSD.string)
                g.add((column_uri, data_type_prop, xsd_type))
            
            # Process mappings
            mappings = column_data.get('mappings', [])
            for mapping in mappings:
                if 'property' in mapping:
                    prop_uri = self._expand_uri(mapping['property'], prefixes)
                    relation = mapping.get('relation', 'related')
                    
                    if relation in RELATION_MAPPING:
                        rdf_prop = RELATION_MAPPING[relation]
                        if isinstance(rdf_prop, str):
                            rdf_prop = URIRef(rdf_prop)
                        g.add((column_uri, rdf_prop, prop_uri))
            
            # Process references
            references = column_data.get('references', [])
            for ref in references:
                if isinstance(ref, dict):
                    if 'url' in ref:
                        g.add((column_uri, RDFS.seeAlso, URIRef(ref['url'])))
                    if 'wikidata' in ref:
                        wd_uri = URIRef(f"http://www.wikidata.org/entity/{ref['wikidata']}")
                        g.add((column_uri, OWL.sameAs, wd_uri))
                elif isinstance(ref, str):
                    g.add((column_uri, RDFS.seeAlso, URIRef(ref)))
            
            # Process comments
            comments = column_data.get('comments', [])
            if isinstance(comments, list):
                for comment in comments:
                    g.add((column_uri, RDFS.comment, Literal(comment)))
            elif isinstance(comments, str):
                g.add((column_uri, RDFS.comment, Literal(comments)))
            
            # Process any additional properties
            for key, value in column_data.items():
                if key not in ['label', 'description', 'semantic_type', 'data_type', 
                              'mappings', 'references', 'comments']:
                    # Create custom property
                    prop = self.base_ns[key]
                    if isinstance(value, list):
                        for v in value:
                            g.add((column_uri, prop, Literal(v)))
                    else:
                        g.add((column_uri, prop, Literal(value)))
        
        # Add dataset metadata if present
        if 'dataset_metadata' in data:
            dataset_uri = self.base_ns.Dataset
            metadata = data['dataset_metadata']
            
            g.add((dataset_uri, RDF.type, DCAT.Dataset))
            
            for key, value in metadata.items():
                if key == 'title':
                    g.add((dataset_uri, DCTERMS.title, Literal(value)))
                elif key == 'description':
                    g.add((dataset_uri, DCTERMS.description, Literal(value)))
                elif key == 'publisher':
                    g.add((dataset_uri, DCTERMS.publisher, Literal(value)))
                elif key == 'source':
                    g.add((dataset_uri, DCTERMS.source, URIRef(value)))
                elif key == 'license':
                    g.add((dataset_uri, DCTERMS.license, URIRef(value)))
                else:
                    # Generic property
                    prop = self.base_ns[key]
                    g.add((dataset_uri, prop, Literal(value)))
        
        # Add file metadata
        if 'file_metadata' in data:
            file_meta = data['file_metadata']
            
            if 'created' in file_meta:
                g.add((URIRef(""), DCTERMS.created, Literal(file_meta['created'], datatype=XSD.date)))
            
            if 'modified' in file_meta:
                g.add((URIRef(""), DCTERMS.modified, Literal(file_meta['modified'], datatype=XSD.date)))
            
            if 'version' in file_meta:
                g.add((URIRef(""), self.base_ns.version, Literal(file_meta['version'])))
        
        # Write TTL file
        g.serialize(destination=ttl_path, format='turtle')
        print(f"Converted {yaml_path} to {ttl_path}")
    
    def ttl_to_yaml(self, ttl_path: Path, yaml_path: Path) -> None:
        """Convert TTL column annotations to YAML format."""
        # Load TTL data
        g = Graph()
        g.parse(ttl_path, format='turtle')
        
        # Initialize data structure
        data = {
            'prefixes': {},
            'columns': {},
            'dataset_metadata': {},
            'file_metadata': {}
        }
        
        # Extract namespace prefixes
        for prefix, namespace in g.namespaces():
            if prefix and str(namespace) != str(self.base_uri):
                data['prefixes'][prefix] = str(namespace)
        
        # Query for column annotations using the csv2rdf ColumnAnnotation class
        column_annotation_class = self.base_ns.ColumnAnnotation
        
        # Get all instances of ColumnAnnotation
        for column_uri in g.subjects(RDF.type, column_annotation_class):
            column_data = {}
            
            # Get column name
            column_name = None
            for name in g.objects(column_uri, self.base_ns.columnName):
                column_name = str(name)
                break
            
            if not column_name:
                continue
            
            # Get basic properties
            for label in g.objects(column_uri, RDFS.label):
                column_data['label'] = str(label)
            
            for desc in g.objects(column_uri, DCTERMS.description):
                column_data['description'] = str(desc)
            
            # Get data type
            for dtype in g.objects(column_uri, self.base_ns.dataType):
                # Convert XSD type back to simple type
                dtype_str = str(dtype)
                for simple, xsd in DATATYPE_MAPPING.items():
                    if str(xsd) == dtype_str:
                        column_data['data_type'] = simple
                        break
            
            # Get mappings and references
            mappings = []
            references = []
            
            # Check all relation types
            for relation, rdf_prop in RELATION_MAPPING.items():
                if isinstance(rdf_prop, str):
                    rdf_prop = URIRef(rdf_prop)
                
                for obj in g.objects(column_uri, rdf_prop):
                    if isinstance(obj, URIRef):
                        obj_str = str(obj)
                        if obj_str.startswith('http://www.wikidata.org/entity/'):
                            # Handle Wikidata specially
                            wd_id = obj_str.split('/')[-1]
                            references.append({'wikidata': wd_id})
                        else:
                            # This is a property mapping
                            mapping = {
                                'property': self._compact_uri(obj_str, data['prefixes']),
                                'relation': relation
                            }
                            mappings.append(mapping)
            
            # Also check rdfs:seeAlso for references
            for ref in g.objects(column_uri, RDFS.seeAlso):
                if isinstance(ref, URIRef):
                    ref_str = str(ref)
                    # Check if it's not already in references
                    if not any(r.get('url') == ref_str if isinstance(r, dict) else r == ref_str 
                              for r in references):
                        references.append(ref_str)
            
            # Get comments
            comments = []
            for comment in g.objects(column_uri, RDFS.comment):
                comment_str = str(comment)
                if comment_str != "Represents semantic annotations for CSV columns":
                    comments.append(comment_str)
            
            # Add to column data
            if mappings:
                column_data['mappings'] = mappings
            if references:
                column_data['references'] = references
            if comments:
                column_data['comments'] = comments if len(comments) > 1 else comments[0]
            
            # Get any additional custom properties
            for pred, obj in g.predicate_objects(column_uri):
                pred_str = str(pred)
                if (pred_str.startswith(str(self.base_uri)) and 
                    pred not in [self.base_ns.columnName, self.base_ns.semanticType, 
                                self.base_ns.dataType]):
                    key = pred_str.replace(str(self.base_uri), '')
                    if key not in column_data:
                        column_data[key] = str(obj)
            
            data['columns'][column_name] = column_data
        
        # Query for dataset metadata
        dataset_uri = self.base_ns.Dataset
        if (dataset_uri, RDF.type, DCAT.Dataset) in g:
            for pred, obj in g.predicate_objects(dataset_uri):
                if pred == DCTERMS.title:
                    data['dataset_metadata']['title'] = str(obj)
                elif pred == DCTERMS.description:
                    data['dataset_metadata']['description'] = str(obj)
                elif pred == DCTERMS.publisher:
                    data['dataset_metadata']['publisher'] = str(obj)
                elif pred == DCTERMS.source:
                    data['dataset_metadata']['source'] = str(obj)
                elif pred == DCTERMS.license:
                    data['dataset_metadata']['license'] = str(obj)
                elif str(pred).startswith(str(self.base_uri)):
                    key = str(pred).replace(str(self.base_uri), '')
                    data['dataset_metadata'][key] = str(obj)
        
        # Get file metadata
        for created in g.objects(URIRef(""), DCTERMS.created):
            data['file_metadata']['created'] = str(created)
        
        for modified in g.objects(URIRef(""), DCTERMS.modified):
            data['file_metadata']['modified'] = str(modified)
        
        for version in g.objects(URIRef(""), self.base_ns.version):
            data['file_metadata']['version'] = str(version)
        
        # Clean up empty sections
        data = {k: v for k, v in data.items() if v}
        
        # Write YAML file
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, 
                     width=120, allow_unicode=True)
        
        print(f"Converted {ttl_path} to {yaml_path}")
    
    def _expand_uri(self, uri: str, prefixes: Dict[str, str]) -> URIRef:
        """Expand a prefixed URI to full URI."""
        if ':' in uri and not uri.startswith('http'):
            prefix, local = uri.split(':', 1)
            if prefix in prefixes:
                return URIRef(prefixes[prefix] + local)
        return URIRef(uri)
    
    def _compact_uri(self, uri: str, prefixes: Dict[str, str]) -> str:
        """Compact a full URI to prefixed form if possible."""
        for prefix, namespace in prefixes.items():
            if uri.startswith(namespace):
                return f"{prefix}:{uri[len(namespace):]}"
        return uri


def main():
    """CLI interface for converting between YAML and TTL formats."""
    parser = argparse.ArgumentParser(
        description='Convert CSV column annotations between YAML and TTL formats'
    )
    parser.add_argument('input', type=Path, help='Input file (YAML or TTL)')
    parser.add_argument('output', type=Path, help='Output file (YAML or TTL)')
    parser.add_argument('--format', choices=['yaml-to-ttl', 'ttl-to-yaml', 'auto'],
                      default='auto', help='Conversion direction (default: auto-detect)')
    parser.add_argument('--base-uri', type=str, default='http://example.org/annotations/',
                      help='Base URI for annotations (default: http://example.org/annotations/)')
    
    args = parser.parse_args()
    
    # Auto-detect format if needed
    if args.format == 'auto':
        if args.input.suffix.lower() in ['.yaml', '.yml'] and args.output.suffix.lower() == '.ttl':
            args.format = 'yaml-to-ttl'
        elif args.input.suffix.lower() == '.ttl' and args.output.suffix.lower() in ['.yaml', '.yml']:
            args.format = 'ttl-to-yaml'
        else:
            print("Error: Cannot auto-detect conversion format. Please specify --format")
            sys.exit(1)
    
    # Create converter
    converter = AnnotationConverter(base_uri=args.base_uri)
    
    # Perform conversion
    try:
        if args.format == 'yaml-to-ttl':
            converter.yaml_to_ttl(args.input, args.output)
        else:
            converter.ttl_to_yaml(args.input, args.output)
    except Exception as e:
        print(f"Error during conversion: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()