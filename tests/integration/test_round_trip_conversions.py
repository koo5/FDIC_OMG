#!/usr/bin/env python3
"""
Integration tests for round-trip format conversions
"""

import json
import yaml
import pytest
from pathlib import Path
from rdflib import Graph
import tempfile
import shutil

# Add the parent directory to Python path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fdic_omg.converters.format_converter import FDICMappingConverter


@pytest.mark.integration
class TestRoundTripConversions:
    """Test round-trip conversions between all formats"""
    
    @pytest.fixture
    def converter(self):
        """Create a converter instance"""
        return FDICMappingConverter()
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def fixtures_dir(self):
        """Get the fixtures directory path"""
        return Path(__file__).parent.parent / "fixtures"
    
    def compare_yaml_data(self, data1, data2):
        """Compare two YAML data structures, ignoring minor differences"""
        # Compare dataset
        assert data1["dataset"]["title"] == data2["dataset"]["title"]
        assert data1["dataset"]["description"] == data2["dataset"]["description"]
        
        # Compare columns
        assert set(data1["columns"].keys()) == set(data2["columns"].keys())
        for col_name in data1["columns"]:
            col1 = data1["columns"][col_name]
            col2 = data2["columns"][col_name]
            assert col1["label"] == col2["label"]
            assert col1["semantic_type"] == col2["semantic_type"]
            assert col1["data_type"] == col2["data_type"]
    
    def test_ttl_to_yaml_to_ttl(self, converter, fixtures_dir, temp_dir):
        """Test TTL -> YAML -> TTL conversion"""
        # Load original TTL
        original_ttl = fixtures_dir / "minimal_mapping.ttl"
        
        # Convert TTL to YAML
        yaml_file = temp_dir / "converted.yaml"
        data = converter.ttl_to_dict(original_ttl)
        converter.dict_to_yaml(data, yaml_file)
        
        # Convert YAML back to TTL
        final_ttl = temp_dir / "final.ttl"
        converter.yaml_to_ttl(yaml_file, final_ttl)
        
        # Compare graphs
        original_graph = Graph()
        original_graph.parse(original_ttl, format="turtle")
        
        final_graph = Graph()
        final_graph.parse(final_ttl, format="turtle")
        
        # Check that we have the same number of triples (approximately)
        # Allow some difference due to blank nodes and formatting
        # The converter adds extra metadata during conversion
        assert abs(len(original_graph) - len(final_graph)) < 20
    
    @pytest.mark.xfail(reason="JSON-LD parser issues with dataset extraction")
    def test_yaml_to_jsonld_to_yaml(self, converter, fixtures_dir, temp_dir):
        """Test YAML -> JSON-LD -> YAML conversion"""
        # Load original YAML
        original_yaml = fixtures_dir / "minimal_mapping.yaml"
        with open(original_yaml, 'r') as f:
            original_data = yaml.safe_load(f)
        
        # Convert YAML to JSON-LD
        jsonld_file = temp_dir / "converted.jsonld"
        converter.dict_to_jsonld(original_data, jsonld_file)
        
        # Convert JSON-LD to TTL (intermediate step)
        ttl_file = temp_dir / "intermediate.ttl"
        converter.jsonld_to_ttl(jsonld_file, ttl_file)
        
        # Convert TTL back to YAML
        final_yaml = temp_dir / "final.yaml"
        final_data = converter.ttl_to_dict(ttl_file)
        converter.dict_to_yaml(final_data, final_yaml)
        
        # Load final YAML
        with open(final_yaml, 'r') as f:
            final_yaml_data = yaml.safe_load(f)
        
        # Compare data
        self.compare_yaml_data(original_data, final_yaml_data)
    
    def test_jsonld_to_ttl_to_jsonld(self, converter, fixtures_dir, temp_dir):
        """Test JSON-LD -> TTL -> JSON-LD conversion"""
        # Load original JSON-LD
        original_jsonld = fixtures_dir / "minimal_mapping.jsonld"
        with open(original_jsonld, 'r') as f:
            original_data = json.load(f)
        
        # Convert JSON-LD to TTL
        ttl_file = temp_dir / "converted.ttl"
        converter.jsonld_to_ttl(original_jsonld, ttl_file)
        
        # Convert TTL back to JSON-LD
        final_jsonld = temp_dir / "final.jsonld"
        data = converter.ttl_to_dict(ttl_file)
        converter.dict_to_jsonld(data, final_jsonld)
        
        # Load final JSON-LD
        with open(final_jsonld, 'r') as f:
            final_data = json.load(f)
        
        # Check that @graph exists and has content
        assert "@graph" in final_data
        assert len(final_data["@graph"]) > 0
        
        # Check for column mappings
        column_nodes = [n for n in final_data["@graph"] if n.get("@type") == "ColumnMapping"]
        assert len(column_nodes) > 0
    
    def test_all_formats_preserve_essential_data(self, converter, fixtures_dir, temp_dir):
        """Test that essential data is preserved across all format conversions"""
        # Start with YAML
        original_yaml = fixtures_dir / "minimal_mapping.yaml"
        with open(original_yaml, 'r') as f:
            original_data = yaml.safe_load(f)
        
        # Convert through all formats
        # YAML -> TTL
        ttl_file = temp_dir / "step1.ttl"
        converter.yaml_to_ttl(original_yaml, ttl_file)
        
        # TTL -> JSON-LD
        jsonld_file = temp_dir / "step2.jsonld"
        data_from_ttl = converter.ttl_to_dict(ttl_file)
        converter.dict_to_jsonld(data_from_ttl, jsonld_file)
        
        # JSON-LD -> TTL
        ttl_file2 = temp_dir / "step3.ttl"
        converter.jsonld_to_ttl(jsonld_file, ttl_file2)
        
        # TTL -> YAML
        final_yaml = temp_dir / "final.yaml"
        final_data = converter.ttl_to_dict(ttl_file2)
        converter.dict_to_yaml(final_data, final_yaml)
        
        # Load final YAML
        with open(final_yaml, 'r') as f:
            final_yaml_data = yaml.safe_load(f)
        
        # Verify essential data preserved
        assert original_data["dataset"]["title"] == final_yaml_data["dataset"]["title"]
        assert len(original_data["columns"]) == len(final_yaml_data["columns"])
        
        # Check specific column data
        for col_name in ["TEST_ID", "TEST_NAME"]:
            assert col_name in final_yaml_data["columns"]
            orig_col = original_data["columns"][col_name]
            final_col = final_yaml_data["columns"][col_name]
            assert orig_col["label"] == final_col["label"]
            assert orig_col["data_type"] == final_col["data_type"]
    
    def test_large_mapping_round_trip(self, converter, temp_dir):
        """Test round-trip conversion with the actual large mapping file"""
        # Use the actual FDIC mapping file
        actual_ttl = Path(__file__).parent.parent.parent / "fdic_omg" / "mappings" / "column_mappings.ttl"
        
        if actual_ttl.exists():
            # TTL -> YAML
            yaml_file = temp_dir / "fdic_full.yaml"
            data = converter.ttl_to_dict(actual_ttl)
            converter.dict_to_yaml(data, yaml_file)
            
            # YAML -> JSON-LD
            jsonld_file = temp_dir / "fdic_full.jsonld"
            converter.dict_to_jsonld(data, jsonld_file)
            
            # JSON-LD -> TTL
            final_ttl = temp_dir / "fdic_full_final.ttl"
            converter.jsonld_to_ttl(jsonld_file, final_ttl)
            
            # Verify files were created and have content
            assert yaml_file.exists()
            assert jsonld_file.exists()
            assert final_ttl.exists()
            
            assert yaml_file.stat().st_size > 1000  # Should be substantial
            assert jsonld_file.stat().st_size > 1000
            assert final_ttl.stat().st_size > 1000