#!/usr/bin/env python3
"""
Unit tests for FDIC column mappings format converter
"""

import json
import yaml
import pytest
from pathlib import Path
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, DCTERMS

# Add the parent directory to Python path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fdic_omg.converters.format_converter import FDICMappingConverter

# Define test namespaces
FDIC = Namespace("http://example.org/fdic/ontology#")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")


@pytest.mark.unit
class TestFDICMappingConverter:
    """Test cases for FDIC mapping format converter"""
    
    @pytest.fixture
    def converter(self):
        """Create a converter instance for testing"""
        return FDICMappingConverter()
    
    @pytest.fixture
    def sample_dict_data(self):
        """Sample dictionary data for testing"""
        return {
            "dataset": {
                "title": "Test Dataset",
                "description": "Test description",
                "keywords": ["test", "data"],
                "publisher": {
                    "name": "Test Publisher",
                    "homepage": "https://example.org"
                }
            },
            "resources": {
                "TestResource": {
                    "name": "Test Resource",
                    "description": "A test resource",
                    "homepage": "https://test.org",
                    "type": "Well-formed Ontology"
                }
            },
            "columns": {
                "TEST_COL": {
                    "label": "Test Column",
                    "description": "A test column",
                    "semantic_type": "test_type",
                    "data_type": "string",
                    "comments": "Test comment",
                    "mappings": [
                        {
                            "ontology": "GeoSPARQL",
                            "property": "http://www.opengis.net/ont/geosparql#testProperty",
                            "relation": "equivalent"
                        }
                    ],
                    "references": [
                        {
                            "url": "https://example.org/test",
                            "type": "definition"
                        }
                    ]
                }
            },
            "metadata": {
                "format_version": "1.0",
                "created": "2025-06-20",
                "creator": "Test System",
                "license": "https://creativecommons.org/licenses/by/4.0/"
            }
        }
    
    def test_converter_initialization(self, converter):
        """Test converter initializes with proper namespaces"""
        assert converter.graph is not None
        assert isinstance(converter.graph, Graph)
        
        # Check namespace bindings
        namespaces = dict(converter.graph.namespaces())
        assert "fdic" in namespaces
        assert "geo" in namespaces
        assert "schema" in namespaces
    
    def test_dict_to_rdf_conversion(self, converter, sample_dict_data):
        """Test converting dictionary to RDF"""
        converter._dict_to_rdf(sample_dict_data)
        
        # Check dataset was added (TestDataset because title contains "Test")
        dataset_uri = FDIC.TestFDICDataset
        assert (dataset_uri, RDF.type, URIRef("http://www.w3.org/ns/dcat#Dataset")) in converter.graph
        assert (dataset_uri, DCTERMS.title, Literal("Test Dataset")) in converter.graph
        
        # Check column mapping was added
        column_uri = FDIC.column_TEST_COL
        assert (column_uri, RDF.type, FDIC.ColumnMapping) in converter.graph
        assert (column_uri, FDIC.columnName, Literal("TEST_COL")) in converter.graph
        assert (column_uri, RDFS.label, Literal("Test Column", lang="en")) in converter.graph
    
    def test_extract_dataset_metadata(self, converter):
        """Test extracting dataset metadata from RDF"""
        # Add test data to graph
        dataset_uri = FDIC.FDICBankDataset
        converter.graph.add((dataset_uri, RDF.type, URIRef("http://www.w3.org/ns/dcat#Dataset")))
        converter.graph.add((dataset_uri, DCTERMS.title, Literal("Test Dataset")))
        converter.graph.add((dataset_uri, DCTERMS.description, Literal("Test description")))
        
        # Extract metadata
        metadata = converter._extract_dataset_metadata()
        
        assert metadata["title"] == "Test Dataset"
        assert metadata["description"] == "Test description"
    
    def test_extract_column_mappings(self, converter):
        """Test extracting column mappings from RDF"""
        # Add test column mapping
        column_uri = FDIC.column_TEST
        converter.graph.add((column_uri, RDF.type, FDIC.ColumnMapping))
        converter.graph.add((column_uri, FDIC.columnName, Literal("TEST")))
        converter.graph.add((column_uri, RDFS.label, Literal("Test Column", lang="en")))
        converter.graph.add((column_uri, FDIC.semanticType, Literal("test_type")))
        converter.graph.add((column_uri, FDIC.dataType, Literal("string")))
        converter.graph.add((column_uri, RDFS.seeAlso, GEO.testProperty))
        
        # Extract mappings
        columns = converter._extract_column_mappings()
        
        assert "TEST" in columns
        assert columns["TEST"]["label"] == "Test Column"
        assert columns["TEST"]["semantic_type"] == "test_type"
        assert columns["TEST"]["data_type"] == "string"
        assert len(columns["TEST"]["mappings"]) > 0
    
    def test_build_jsonld_context(self, converter):
        """Test building JSON-LD context"""
        context = converter._build_jsonld_context()
        
        assert "@version" in context
        assert context["@version"] == 1.1
        assert "fdic" in context
        assert context["fdic"] == "http://example.org/fdic/ontology#"
        assert "ColumnMapping" in context
        assert "columnName" in context
    
    def test_build_jsonld_graph(self, converter, sample_dict_data):
        """Test building JSON-LD graph"""
        graph = converter._build_jsonld_graph(sample_dict_data)
        
        assert isinstance(graph, list)
        assert len(graph) > 0
        
        # Check for ontology node
        onto_node = next((n for n in graph if n.get("@id") == "column-mappings"), None)
        assert onto_node is not None
        assert onto_node["@type"] == "owl:Ontology"
        
        # Check for column mapping
        column_node = next((n for n in graph if n.get("@id") == "fdic:column_TEST_COL"), None)
        assert column_node is not None
        assert column_node["@type"] == "ColumnMapping"
        assert column_node["columnName"] == "TEST_COL"
    
    def test_get_literal(self, converter):
        """Test _get_literal helper method"""
        # Add test data
        test_uri = URIRef("http://example.org/test")
        converter.graph.add((test_uri, RDFS.label, Literal("Test Label")))
        
        # Test getting existing literal
        result = converter._get_literal(test_uri, RDFS.label)
        assert result == "Test Label"
        
        # Test default value
        result = converter._get_literal(test_uri, DCTERMS.title, "Default")
        assert result == "Default"
    
    def test_convert_value_type(self):
        """Test value type conversion using Literal directly"""
        from rdflib import Literal
        from rdflib.namespace import XSD
        
        # Test decimal conversion
        result = Literal("123.45", datatype=XSD.decimal)
        assert result is not None
        assert result.datatype == XSD.decimal
        assert float(result) == 123.45
        
        # Test integer conversion
        result = Literal("42", datatype=XSD.integer)
        assert result is not None
        assert result.datatype == XSD.integer
        assert int(result) == 42
        
        # Test string conversion
        result = Literal("test", datatype=XSD.string)
        assert result is not None
        assert result.datatype == XSD.string
        assert str(result) == "test"


@pytest.mark.integration
class TestFormatConversions:
    """Integration tests for format conversions"""
    
    @pytest.fixture
    def test_yaml_file(self, tmp_path):
        """Create a test YAML file"""
        yaml_data = {
            "dataset": {
                "title": "Test Dataset",
                "description": "Test",
                "publisher": {"name": "Test"}
            },
            "resources": {},
            "columns": {
                "TEST": {
                    "label": "Test",
                    "semantic_type": "test",
                    "data_type": "string"
                }
            },
            "metadata": {
                "format_version": "1.0",
                "created": "2025-06-20",
                "creator": "Test",
                "license": "https://test.org"
            }
        }
        
        yaml_file = tmp_path / "test.yaml"
        with open(yaml_file, 'w') as f:
            yaml.dump(yaml_data, f)
        
        return yaml_file
    
    @pytest.fixture
    def test_jsonld_file(self, tmp_path):
        """Create a test JSON-LD file"""
        jsonld_data = {
            "@context": {
                "@base": "http://example.org/fdic/",
                "fdic": "http://example.org/fdic/ontology#",
                "ColumnMapping": "fdic:ColumnMapping"
            },
            "@graph": [
                {
                    "@id": "fdic:column_TEST",
                    "@type": "ColumnMapping",
                    "columnName": "TEST",
                    "label": "Test"
                }
            ]
        }
        
        jsonld_file = tmp_path / "test.jsonld"
        with open(jsonld_file, 'w') as f:
            json.dump(jsonld_data, f)
        
        return jsonld_file
    
    def test_yaml_to_ttl_conversion(self, test_yaml_file, tmp_path):
        """Test YAML to TTL conversion"""
        converter = FDICMappingConverter()
        ttl_file = tmp_path / "output.ttl"
        
        converter.yaml_to_ttl(test_yaml_file, ttl_file)
        
        assert ttl_file.exists()
        
        # Verify TTL content
        graph = Graph()
        graph.parse(ttl_file, format="turtle")
        assert len(graph) > 0
    
    def test_jsonld_to_ttl_conversion(self, test_jsonld_file, tmp_path):
        """Test JSON-LD to TTL conversion"""
        converter = FDICMappingConverter()
        ttl_file = tmp_path / "output.ttl"
        
        converter.jsonld_to_ttl(test_jsonld_file, ttl_file)
        
        assert ttl_file.exists()
        
        # Verify TTL content
        graph = Graph()
        graph.parse(ttl_file, format="turtle")
        assert len(graph) > 0
    
    def test_dict_to_yaml_conversion(self, tmp_path):
        """Test dictionary to YAML conversion"""
        converter = FDICMappingConverter()
        yaml_file = tmp_path / "output.yaml"
        
        test_data = {
            "dataset": {"title": "Test"},
            "columns": {"TEST": {"label": "Test"}}
        }
        
        converter.dict_to_yaml(test_data, yaml_file)
        
        assert yaml_file.exists()
        
        # Verify YAML content
        with open(yaml_file, 'r') as f:
            content = f.read()
            assert "# FDIC Column Mappings" in content
            assert "dataset:" in content
            assert "title: Test" in content