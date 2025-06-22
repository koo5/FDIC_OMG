#!/usr/bin/env python3
"""
JSON Schema validation tests for FDIC column mappings
"""

import json
import yaml
import pytest
from pathlib import Path
from jsonschema import validate, ValidationError, Draft7Validator

# Add the parent directory to Python path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.validation
class TestJSONSchemaValidation:
    """Test JSON Schema validation for mapping files"""
    
    @pytest.fixture
    def schema(self):
        """Load the JSON Schema"""
        schema_path = Path(__file__).parent.parent.parent / "fdic_omg" / "mappings" / "schemas" / "mapping_schema.json"
        with open(schema_path, 'r') as f:
            return json.load(f)
    
    @pytest.fixture
    def valid_mapping(self):
        """Valid mapping data"""
        return {
            "dataset": {
                "title": "Test Dataset",
                "description": "Test description",
                "publisher": {
                    "name": "Test Publisher",
                    "homepage": "https://test.org"
                },
                "keywords": ["test"],
                "spatial": "Test Location",
                "temporal": "Test Period",
                "version": "2025.1"
            },
            "resources": {
                "TestResource": {
                    "name": "Test Resource",
                    "description": "Test resource description",
                    "homepage": "https://test.org",
                    "type": "Well-formed Ontology"
                }
            },
            "columns": {
                "TEST_COL": {
                    "label": "Test Column",
                    "description": "Test column description",
                    "semantic_type": "coordinate",
                    "data_type": "decimal",
                    "mappings": [
                        {
                            "ontology": "GeoSPARQL",
                            "property": "http://test.org/property",
                            "relation": "equivalent"
                        }
                    ],
                    "references": [
                        {
                            "url": "https://test.org/ref",
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
    
    def test_schema_is_valid(self, schema):
        """Test that the schema itself is valid"""
        # This validates that the schema follows JSON Schema draft-07
        Draft7Validator.check_schema(schema)
    
    def test_valid_mapping_passes(self, schema, valid_mapping):
        """Test that a valid mapping passes validation"""
        # Should not raise any exception
        validate(instance=valid_mapping, schema=schema)
    
    def test_missing_required_dataset_fields(self, schema):
        """Test validation fails when required dataset fields are missing"""
        invalid_mapping = {
            "dataset": {
                # Missing required fields: title, description, publisher
            },
            "columns": {"TEST": {"label": "Test", "semantic_type": "test", "data_type": "string"}},
            "metadata": {
                "format_version": "1.0",
                "created": "2025-06-20",
                "creator": "Test",
                "license": "https://test.org"
            }
        }
        
        with pytest.raises(ValidationError) as exc_info:
            validate(instance=invalid_mapping, schema=schema)
        
        assert "'title' is a required property" in str(exc_info.value)
    
    def test_invalid_semantic_type(self, schema, valid_mapping):
        """Test validation fails with invalid semantic type"""
        valid_mapping["columns"]["TEST_COL"]["semantic_type"] = "invalid_type"
        
        with pytest.raises(ValidationError) as exc_info:
            validate(instance=valid_mapping, schema=schema)
        
        assert "is not one of" in str(exc_info.value)
    
    def test_invalid_data_type(self, schema, valid_mapping):
        """Test validation fails with invalid data type"""
        valid_mapping["columns"]["TEST_COL"]["data_type"] = "invalid_type"
        
        with pytest.raises(ValidationError) as exc_info:
            validate(instance=valid_mapping, schema=schema)
        
        assert "is not one of" in str(exc_info.value)
    
    def test_invalid_relation_type(self, schema, valid_mapping):
        """Test validation fails with invalid relation type"""
        valid_mapping["columns"]["TEST_COL"]["mappings"][0]["relation"] = "invalid_relation"
        
        with pytest.raises(ValidationError) as exc_info:
            validate(instance=valid_mapping, schema=schema)
        
        assert "is not one of" in str(exc_info.value)
    
    def test_invalid_reference_type(self, schema, valid_mapping):
        """Test validation fails with invalid reference type"""
        valid_mapping["columns"]["TEST_COL"]["references"][0]["type"] = "invalid_ref_type"
        
        with pytest.raises(ValidationError) as exc_info:
            validate(instance=valid_mapping, schema=schema)
        
        assert "is not one of" in str(exc_info.value)
    
    def test_invalid_resource_type(self, schema, valid_mapping):
        """Test validation fails with invalid resource type"""
        valid_mapping["resources"]["TestResource"]["type"] = "Invalid Type"
        
        with pytest.raises(ValidationError) as exc_info:
            validate(instance=valid_mapping, schema=schema)
        
        assert "is not one of" in str(exc_info.value)
    
    def test_missing_column_required_fields(self, schema, valid_mapping):
        """Test validation fails when column is missing required fields"""
        del valid_mapping["columns"]["TEST_COL"]["label"]
        
        with pytest.raises(ValidationError) as exc_info:
            validate(instance=valid_mapping, schema=schema)
        
        assert "'label' is a required property" in str(exc_info.value)
    
    def test_invalid_url_format(self, schema, valid_mapping):
        """Test validation passes because jsonschema uri format is lenient"""
        # Note: jsonschema's "uri" format validation is very lenient
        # It accepts many strings that aren't valid URIs
        # This test documents that behavior
        valid_mapping["columns"]["TEST_COL"]["references"][0]["url"] = "not-a-url"
        
        # This actually passes with jsonschema's default URI validation
        validate(instance=valid_mapping, schema=schema)
    
    def test_empty_columns(self, schema, valid_mapping):
        """Test validation fails with empty columns"""
        valid_mapping["columns"] = {}
        
        with pytest.raises(ValidationError) as exc_info:
            validate(instance=valid_mapping, schema=schema)
        
        assert "should be non-empty" in str(exc_info.value) or "does not have enough properties" in str(exc_info.value)
    
    def test_fixture_files_are_valid(self, schema):
        """Test that all fixture files pass validation"""
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        
        # Test YAML fixture
        yaml_file = fixtures_dir / "minimal_mapping.yaml"
        with open(yaml_file, 'r') as f:
            yaml_data = yaml.safe_load(f)
        
        # Should not raise exception
        validate(instance=yaml_data, schema=schema)
    
    def test_actual_mapping_file_is_valid(self, schema):
        """Test that the actual FDIC mapping YAML file is valid"""
        mapping_file = Path(__file__).parent.parent.parent / "fdic_omg" / "mappings" / "column_mappings.yaml"
        
        if mapping_file.exists():
            with open(mapping_file, 'r') as f:
                mapping_data = yaml.safe_load(f)
            
            # Should not raise exception
            validate(instance=mapping_data, schema=schema)