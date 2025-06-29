#!/usr/bin/env python3
"""Tests for the annotation converter module."""

import pytest
import yaml
from pathlib import Path
import tempfile
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD, DCTERMS

from fdic_omg.annotation_converter import AnnotationConverter, DATATYPE_MAPPING, RELATION_MAPPING


class TestAnnotationConverter:
    """Test cases for the AnnotationConverter class."""
    
    @pytest.fixture
    def converter(self):
        """Create a converter instance with default base URI."""
        return AnnotationConverter()
    
    @pytest.fixture
    def sample_yaml_data(self):
        """Sample YAML data for testing."""
        return {
            'prefixes': {
                'schema': 'https://schema.org/',
                'geo': 'http://www.opengis.net/ont/geosparql#',
                'fibo': 'https://spec.edmcouncil.org/fibo/ontology/'
            },
            'columns': {
                'CERT': {
                    'label': 'Certificate Number',
                    'description': 'Unique identifier for the institution',
                    'data_type': 'integer',
                    'mappings': [
                        {
                            'property': 'schema:identifier',
                            'relation': 'equivalent'
                        },
                        {
                            'property': 'fibo:hasIdentifier',
                            'relation': 'similar'
                        }
                    ],
                    'references': [
                        'https://www.fdic.gov/resources/',
                        {'wikidata': 'Q116907062'}
                    ],
                    'comments': 'Primary key for FDIC institutions'
                },
                'NAME': {
                    'label': 'Institution Name',
                    'description': 'Legal name of the bank',
                    'data_type': 'string',
                    'mappings': [
                        {
                            'property': 'schema:legalName',
                            'relation': 'exact'
                        }
                    ]
                },
                'LATITUDE': {
                    'label': 'Latitude',
                    'description': 'Geographic latitude coordinate',
                    'data_type': 'decimal',
                    'mappings': [
                        {
                            'property': 'geo:lat',
                            'relation': 'equivalent'
                        }
                    ],
                    'references': [
                        {'wikidata': 'Q34027'}
                    ]
                }
            },
            'dataset_metadata': {
                'title': 'Test Dataset',
                'description': 'A test dataset for unit tests',
                'publisher': 'Test Publisher',
                'source': 'https://example.org/data',
                'license': 'https://creativecommons.org/licenses/by/4.0/'
            }
        }
    
    @pytest.fixture
    def temp_yaml_file(self, sample_yaml_data):
        """Create a temporary YAML file with sample data."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(sample_yaml_data, f)
            yield Path(f.name)
        Path(f.name).unlink()
    
    def test_yaml_to_ttl_conversion(self, converter, temp_yaml_file):
        """Test converting YAML to TTL format."""
        with tempfile.NamedTemporaryFile(suffix='.ttl', delete=False) as ttl_file:
            ttl_path = Path(ttl_file.name)
        
        try:
            # Convert YAML to TTL
            converter.yaml_to_ttl(temp_yaml_file, ttl_path)
            
            # Verify TTL file was created
            assert ttl_path.exists()
            
            # Load and verify TTL content
            g = Graph()
            g.parse(ttl_path, format='turtle')
            
            # Check namespaces
            namespaces = dict(g.namespaces())
            assert 'schema' in namespaces
            assert 'geo' in namespaces
            assert 'fibo' in namespaces
            
            # Check column annotations
            csv2rdf = Namespace(converter.base_uri)
            column_class = csv2rdf.ColumnAnnotation
            
            # Count column instances
            columns = list(g.subjects(RDF.type, column_class))
            assert len(columns) == 3
            
            # Check CERT column
            cert_uri = csv2rdf.column_CERT
            assert (cert_uri, RDF.type, column_class) in g
            assert (cert_uri, csv2rdf.columnName, Literal("CERT")) in g
            assert (cert_uri, RDFS.label, Literal("Certificate Number")) in g
            assert (cert_uri, csv2rdf.dataType, XSD.integer) in g
            
            # Check mappings
            schema_ns = Namespace("https://schema.org/")
            assert (cert_uri, OWL.equivalentProperty, schema_ns.identifier) in g
            
            # Check references
            wd_uri = URIRef("http://www.wikidata.org/entity/Q116907062")
            assert (cert_uri, OWL.sameAs, wd_uri) in g
            
        finally:
            ttl_path.unlink()
    
    def test_ttl_to_yaml_roundtrip(self, converter, temp_yaml_file):
        """Test converting YAML to TTL and back to YAML."""
        with tempfile.NamedTemporaryFile(suffix='.ttl', delete=False) as ttl_file:
            ttl_path = Path(ttl_file.name)
        
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as yaml_file:
            yaml_path = Path(yaml_file.name)
        
        try:
            # Convert YAML to TTL
            converter.yaml_to_ttl(temp_yaml_file, ttl_path)
            
            # Convert TTL back to YAML
            converter.ttl_to_yaml(ttl_path, yaml_path)
            
            # Load both YAML files
            with open(temp_yaml_file, 'r') as f:
                original_data = yaml.safe_load(f)
            
            with open(yaml_path, 'r') as f:
                roundtrip_data = yaml.safe_load(f)
            
            # Compare structure
            assert set(roundtrip_data.keys()) == set(original_data.keys())
            assert set(roundtrip_data['columns'].keys()) == set(original_data['columns'].keys())
            
            # Check specific column data
            for col_name in original_data['columns']:
                orig_col = original_data['columns'][col_name]
                rt_col = roundtrip_data['columns'][col_name]
                
                assert rt_col.get('label') == orig_col.get('label')
                assert rt_col.get('description') == orig_col.get('description')
                assert rt_col.get('data_type') == orig_col.get('data_type')
                
        finally:
            ttl_path.unlink()
            yaml_path.unlink()
    
    def test_datatype_mapping(self, converter):
        """Test data type conversions."""
        yaml_data = {
            'columns': {
                'col1': {'data_type': 'string'},
                'col2': {'data_type': 'integer'},
                'col3': {'data_type': 'decimal'},
                'col4': {'data_type': 'boolean'},
                'col5': {'data_type': 'date'},
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(yaml_data, f)
            yaml_path = Path(f.name)
        
        with tempfile.NamedTemporaryFile(suffix='.ttl', delete=False) as ttl_file:
            ttl_path = Path(ttl_file.name)
        
        try:
            converter.yaml_to_ttl(yaml_path, ttl_path)
            
            g = Graph()
            g.parse(ttl_path, format='turtle')
            
            csv2rdf = Namespace(converter.base_uri)
            
            # Check each data type mapping
            assert (csv2rdf.column_col1, csv2rdf.dataType, XSD.string) in g
            assert (csv2rdf.column_col2, csv2rdf.dataType, XSD.integer) in g
            assert (csv2rdf.column_col3, csv2rdf.dataType, XSD.decimal) in g
            assert (csv2rdf.column_col4, csv2rdf.dataType, XSD.boolean) in g
            assert (csv2rdf.column_col5, csv2rdf.dataType, XSD.date) in g
            
        finally:
            yaml_path.unlink()
            ttl_path.unlink()
    
    def test_relation_mapping(self, converter):
        """Test relation type conversions."""
        yaml_data = {
            'columns': {
                'col1': {
                    'mappings': [
                        {'property': 'http://example.org/prop1', 'relation': 'equivalent'},
                        {'property': 'http://example.org/prop2', 'relation': 'similar'},
                        {'property': 'http://example.org/prop3', 'relation': 'related'},
                        {'property': 'http://example.org/Type', 'relation': 'instance_of'},
                    ]
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(yaml_data, f)
            yaml_path = Path(f.name)
        
        with tempfile.NamedTemporaryFile(suffix='.ttl', delete=False) as ttl_file:
            ttl_path = Path(ttl_file.name)
        
        try:
            converter.yaml_to_ttl(yaml_path, ttl_path)
            
            g = Graph()
            g.parse(ttl_path, format='turtle')
            
            csv2rdf = Namespace(converter.base_uri)
            col_uri = csv2rdf.column_col1
            
            # Check relation mappings
            assert (col_uri, OWL.equivalentProperty, URIRef('http://example.org/prop1')) in g
            assert (col_uri, RDFS.seeAlso, URIRef('http://example.org/prop2')) in g
            assert (col_uri, RDFS.seeAlso, URIRef('http://example.org/prop3')) in g
            assert (col_uri, RDF.type, URIRef('http://example.org/Type')) in g
            
        finally:
            yaml_path.unlink()
            ttl_path.unlink()
    
    def test_custom_base_uri(self):
        """Test converter with custom base URI."""
        custom_uri = "http://myorg.com/csv/"
        converter = AnnotationConverter(base_uri=custom_uri)
        
        yaml_data = {
            'columns': {
                'TEST': {
                    'label': 'Test Column',
                    'data_type': 'string'
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(yaml_data, f)
            yaml_path = Path(f.name)
        
        with tempfile.NamedTemporaryFile(suffix='.ttl', delete=False) as ttl_file:
            ttl_path = Path(ttl_file.name)
        
        try:
            converter.yaml_to_ttl(yaml_path, ttl_path)
            
            g = Graph()
            g.parse(ttl_path, format='turtle')
            
            custom_ns = Namespace(custom_uri)
            
            # Check that custom namespace is used
            assert (custom_ns.column_TEST, RDF.type, custom_ns.ColumnAnnotation) in g
            assert (custom_ns.column_TEST, custom_ns.columnName, Literal("TEST")) in g
            
        finally:
            yaml_path.unlink()
            ttl_path.unlink()
    
    def test_wikidata_references(self, converter):
        """Test handling of Wikidata references."""
        yaml_data = {
            'columns': {
                'col1': {
                    'references': [
                        {'wikidata': 'Q12345'},
                        {'wikidata': 'Q67890'},
                        'https://example.org/ref1'
                    ]
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(yaml_data, f)
            yaml_path = Path(f.name)
        
        with tempfile.NamedTemporaryFile(suffix='.ttl', delete=False) as ttl_file:
            ttl_path = Path(ttl_file.name)
        
        try:
            converter.yaml_to_ttl(yaml_path, ttl_path)
            
            g = Graph()
            g.parse(ttl_path, format='turtle')
            
            csv2rdf = Namespace(converter.base_uri)
            col_uri = csv2rdf.column_col1
            
            # Check Wikidata references
            assert (col_uri, OWL.sameAs, URIRef('http://www.wikidata.org/entity/Q12345')) in g
            assert (col_uri, OWL.sameAs, URIRef('http://www.wikidata.org/entity/Q67890')) in g
            assert (col_uri, RDFS.seeAlso, URIRef('https://example.org/ref1')) in g
            
        finally:
            yaml_path.unlink()
            ttl_path.unlink()
    
    def test_empty_yaml(self, converter):
        """Test handling of empty or minimal YAML."""
        yaml_data = {'columns': {}}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(yaml_data, f)
            yaml_path = Path(f.name)
        
        with tempfile.NamedTemporaryFile(suffix='.ttl', delete=False) as ttl_file:
            ttl_path = Path(ttl_file.name)
        
        try:
            # Should not raise an error
            converter.yaml_to_ttl(yaml_path, ttl_path)
            
            # Verify TTL file was created
            assert ttl_path.exists()
            
            g = Graph()
            g.parse(ttl_path, format='turtle')
            
            # Should have basic structure but no columns
            csv2rdf = Namespace(converter.base_uri)
            assert (csv2rdf.ColumnAnnotation, RDF.type, RDFS.Class) in g
            
        finally:
            yaml_path.unlink()
            ttl_path.unlink()
    
    def test_special_characters_in_column_names(self, converter):
        """Test handling of special characters in column names."""
        yaml_data = {
            'columns': {
                'Column Name!': {'label': 'Test 1'},
                'Column@Name': {'label': 'Test 2'},
                'Column#Name': {'label': 'Test 3'},
                'Column Name': {'label': 'Test 4'},  # Space
                'Column-Name': {'label': 'Test 5'},  # Hyphen (should be preserved)
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(yaml_data, f)
            yaml_path = Path(f.name)
        
        with tempfile.NamedTemporaryFile(suffix='.ttl', delete=False) as ttl_file:
            ttl_path = Path(ttl_file.name)
        
        try:
            converter.yaml_to_ttl(yaml_path, ttl_path)
            
            g = Graph()
            g.parse(ttl_path, format='turtle')
            
            # All columns should be created with safe URIs
            csv2rdf = Namespace(converter.base_uri)
            column_class = csv2rdf.ColumnAnnotation
            
            columns = list(g.subjects(RDF.type, column_class))
            assert len(columns) == 5
            
            # Check that column names are preserved in the data
            for col_name in yaml_data['columns']:
                found = False
                for col_uri in columns:
                    if (col_uri, csv2rdf.columnName, Literal(col_name)) in g:
                        found = True
                        break
                assert found, f"Column {col_name} not found"
            
        finally:
            yaml_path.unlink()
            ttl_path.unlink()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])