#!/usr/bin/env python3
"""Integration tests for FDIC OMG system"""

import pytest
import tempfile
import json
from pathlib import Path
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, DCTERMS

from fdic_omg.core import FDICRDFGenerator

# Define namespaces
FDIC = Namespace("http://example.org/fdic/ontology#")
DATA = Namespace("http://example.org/fdic/data#")


@pytest.fixture
def full_csv_file():
    """Create a CSV file with all FDIC columns"""
    content = """CERT,NAME,ADDRESS,CITY,STALP,STNAME,ZIP,FED,RSSD,SERVTYPE,SERVTYPE_DESC,X,Y,LONGITUDE,LATITUDE
57,First National Bank,123 Main St,Springfield,IL,Illinois,62701,7,123456,11,Full Service Brick and Mortar Office,-89.6501,39.7817,-89.6501,39.7817
628,Second State Bank,456 Oak Ave,Chicago,IL,Illinois,60601,7,234567,11,Full Service Brick and Mortar Office,-87.6298,41.8781,-87.6298,41.8781
1234,Third Federal Credit Union,789 Pine Rd,Peoria,IL,Illinois,61602,7,345678,12,Limited Service Drive-Through Only,-89.5890,40.6936,-89.5890,40.6936
5678,Fourth Community Bank,321 Elm Blvd,Rockford,IL,Illinois,61101,7,456789,11,Full Service Brick and Mortar Office,-89.0938,42.2711,-89.0938,42.2711
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(content)
        temp_path = Path(f.name)
    yield temp_path
    temp_path.unlink()


class TestFullWorkflow:
    """Test complete workflow from CSV to RDF with all features"""
    
    def test_full_conversion_workflow(self, full_csv_file):
        """Test complete conversion workflow"""
        generator = FDICRDFGenerator()
        results = generator.process_csv(full_csv_file)
        
        # Basic checks
        assert results['rows_processed'] == 4
        assert results['triples_generated'] > 100  # Should have many triples
        
        # Check table structure
        tables = list(generator.graph.subjects(RDF.type, FDIC.Table))
        assert len(tables) == 1
        
        # Check all columns are present
        columns = list(generator.graph.subjects(RDF.type, FDIC.Column))
        assert len(columns) == 15  # All columns from CSV
        
        # Check column names
        column_names = set()
        for col in columns:
            name = generator.graph.value(col, FDIC.columnName)
            if name:
                column_names.add(str(name))
        
        expected_columns = {
            'CERT', 'NAME', 'ADDRESS', 'CITY', 'STALP', 'STNAME', 
            'ZIP', 'FED', 'RSSD', 'SERVTYPE', 'SERVTYPE_DESC',
            'X', 'Y', 'LONGITUDE', 'LATITUDE'
        }
        assert column_names == expected_columns
        
        # Check rows
        rows = list(generator.graph.subjects(RDF.type, FDIC.Row))
        assert len(rows) == 4
        
        # Check cells exist for all data
        cells = list(generator.graph.subjects(RDF.type, FDIC.Cell))
        assert len(cells) == 60  # 4 rows × 15 columns
    
    def test_annotation_enrichment(self, full_csv_file):
        """Test that annotations are properly applied"""
        generator = FDICRDFGenerator()
        results = generator.process_csv(full_csv_file)
        
        # Find columns with known annotations
        annotated_columns = []
        for col in generator.graph.subjects(RDF.type, FDIC.Column):
            col_name = generator.graph.value(col, FDIC.columnName)
            annotation = generator.graph.value(col, FDIC.hasAnnotation)
            if annotation:
                annotated_columns.append(str(col_name))
        
        # These columns should have annotations
        expected_annotated = ['NAME', 'CERT', 'X', 'Y', 'LONGITUDE', 'LATITUDE', 
                              'ZIP', 'CITY', 'ADDRESS', 'STALP', 'STNAME']
        
        for col_name in expected_annotated:
            assert col_name in annotated_columns, f"Column {col_name} should have annotation"
    
    def test_rdf_serialization_formats(self, full_csv_file):
        """Test that RDF can be serialized to different formats"""
        generator = FDICRDFGenerator()
        results = generator.process_csv(full_csv_file)
        
        # Test Turtle (primary format)
        turtle_output = results['graph'].serialize(format='turtle')
        assert '@prefix fdic:' in turtle_output
        assert 'fdic:Table' in turtle_output
        
        # Ensure it's valid RDF by parsing it back
        test_graph = Graph()
        test_graph.parse(data=turtle_output, format='turtle')
        assert len(test_graph) == len(results['graph'])
    
    def test_viewer_generation_with_real_data(self, full_csv_file):
        """Test viewer generation with realistic data"""
        generator = FDICRDFGenerator()
        results = generator.process_csv(full_csv_file)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            viewer_dir = Path(temp_dir)
            viewer_results = generator.generate_viewer_output(viewer_dir, rows_per_page=2)
            
            # Check viewer structure
            assert viewer_results['total_rows'] == 4
            assert viewer_results['total_pages'] == 2
            
            # Check manifest
            manifest_path = viewer_dir / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            assert len(manifest['headers']) == 15
            assert 'column_annotations' in manifest
            
            # Check first page data
            page0_path = viewer_dir / "page_0.json"
            page0 = json.loads(page0_path.read_text())
            assert len(page0['rows']) == 2
            assert len(page0['rows'][0]) == 15  # All columns
            
            # Check data integrity
            first_row = page0['rows'][0]
            assert first_row[0] == '57'  # CERT
            assert first_row[1] == 'First National Bank'  # NAME
    
    def test_report_generation_with_annotations(self, full_csv_file):
        """Test HTML report with annotation details"""
        generator = FDICRDFGenerator()
        results = generator.process_csv(full_csv_file)
        
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            report_path = Path(f.name)
        
        try:
            generator.generate_html_report(report_path, full_csv_file.name, results)
            
            content = report_path.read_text()
            
            # Check statistics
            assert '4' in content  # rows
            assert str(results['triples_generated']) in content
            
            # Check annotation table
            assert 'Column Annotations' in content
            assert 'CERT' in content
            assert 'FED' in content
            assert 'Geographic longitude coordinate' in content  # X/LONGITUDE description
        finally:
            report_path.unlink()
    
    def test_data_consistency(self, full_csv_file):
        """Test that data remains consistent through conversion"""
        generator = FDICRDFGenerator()
        results = generator.process_csv(full_csv_file)
        
        # Extract data back from RDF
        reconstructed_data = {}
        
        # Get rows
        for row in generator.graph.subjects(RDF.type, FDIC.Row):
            row_idx = generator.graph.value(row, FDIC.rowIndex)
            if row_idx is None:
                continue
            
            row_data = {}
            # Get cells for this row
            for cell in generator.graph.subjects(FDIC.inRow, row):
                col = generator.graph.value(cell, FDIC.inColumn)
                if col:
                    col_name = generator.graph.value(col, FDIC.columnName)
                    value = generator.graph.value(cell, FDIC.value)
                    if col_name and value:
                        row_data[str(col_name)] = str(value)
            
            reconstructed_data[int(row_idx)] = row_data
        
        # Verify first row
        assert reconstructed_data[0]['CERT'] == '57'
        assert reconstructed_data[0]['NAME'] == 'First National Bank'
        assert reconstructed_data[0]['CITY'] == 'Springfield'
        
        # Verify last row
        assert reconstructed_data[3]['CERT'] == '5678'
        assert reconstructed_data[3]['NAME'] == 'Fourth Community Bank'
    
    def test_external_references_preserved(self, full_csv_file):
        """Test that external ontology references are preserved"""
        generator = FDICRDFGenerator()
        results = generator.process_csv(full_csv_file)
        
        # Check that annotation rdfs:seeAlso links are present
        see_also_count = 0
        for annotation in generator.graph.subjects(RDF.type, FDIC.ColumnAnnotation):
            see_also_refs = list(generator.graph.objects(annotation, RDFS.seeAlso))
            if see_also_refs:
                see_also_count += len(see_also_refs)
        
        # Should have many external references
        assert see_also_count > 20  # Multiple references per annotation
        
        # Check specific references
        all_see_also = set()
        for s, p, o in generator.graph.triples((None, RDFS.seeAlso, None)):
            all_see_also.add(str(o))
        
        # Should include references to major ontologies
        assert any('geosparql' in ref for ref in all_see_also)
        assert any('fibo' in ref for ref in all_see_also)
        assert any('geonames' in ref for ref in all_see_also)
        assert any('wikipedia' in ref for ref in all_see_also)