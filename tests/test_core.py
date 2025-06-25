#!/usr/bin/env python3
"""Test suite for FDIC RDF Core functionality"""

import pytest
import tempfile
from pathlib import Path
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, XSD, DCTERMS

from fdic_omg.core import FDICRDFGenerator

# Define namespaces for testing
FDIC = Namespace("http://example.org/fdic/ontology#")
DATA = Namespace("http://example.org/fdic/data#")


@pytest.fixture
def sample_csv_file():
    """Create a temporary CSV file with sample FDIC data"""
    content = """CERT,NAME,ADDRESS,CITY,STALP,ZIP,X,Y
57,First National Bank,123 Main St,Springfield,IL,62701,-89.6501,39.7817
628,Second State Bank,456 Oak Ave,Chicago,IL,60601,-87.6298,41.8781
1234,Third Federal Credit Union,789 Pine Rd,Peoria,IL,61602,-89.5890,40.6936
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(content)
        temp_path = Path(f.name)
    yield temp_path
    temp_path.unlink()


@pytest.fixture
def generator():
    """Create a generator instance"""
    return FDICRDFGenerator()


class TestFDICRDFGenerator:
    """Test cases for FDICRDFGenerator"""
    
    def test_initialization(self, generator):
        """Test generator initialization"""
        assert generator.base_uri == "http://example.org/fdic/data#"
        assert isinstance(generator.graph, Graph)
        assert len(generator.graph) == 0
    
    def test_namespace_bindings(self, generator):
        """Test that namespaces are properly bound"""
        namespaces = dict(generator.graph.namespaces())
        assert str(namespaces.get('fdic')) == str(FDIC)
        assert str(namespaces.get('data')) == str(DATA)
        assert 'dcterms' in namespaces
        assert 'rdfs' in namespaces
    
    def test_process_csv_basic(self, generator, sample_csv_file):
        """Test basic CSV processing"""
        results = generator.process_csv(sample_csv_file)
        
        assert results['rows_processed'] == 3
        assert results['triples_generated'] > 0
        assert 'table_uri' in results
        assert 'graph' in results
        assert isinstance(results['graph'], Graph)
    
    def test_process_csv_with_limit(self, generator, sample_csv_file):
        """Test CSV processing with row limit"""
        results = generator.process_csv(sample_csv_file, max_rows=2)
        
        assert results['rows_processed'] == 2
        
        # Check that only 2 rows are in the graph
        rows = list(generator.graph.subjects(RDF.type, FDIC.Row))
        assert len(rows) == 2
    
    def test_table_structure(self, generator, sample_csv_file):
        """Test that table structure is correctly created"""
        results = generator.process_csv(sample_csv_file)
        
        # Find the table
        tables = list(generator.graph.subjects(RDF.type, FDIC.Table))
        assert len(tables) == 1
        
        table = tables[0]
        
        # Check table properties
        title = generator.graph.value(table, DCTERMS.title)
        assert title is not None
        assert sample_csv_file.name in str(title)
        
        # Check columns
        columns = list(generator.graph.objects(table, FDIC.hasColumn))
        assert len(columns) == 8  # CERT, NAME, ADDRESS, CITY, STALP, ZIP, X, Y
        
        # Check column properties
        column_names = set()
        for col in columns:
            col_name = generator.graph.value(col, FDIC.columnName)
            column_names.add(str(col_name))
        
        expected_columns = {'CERT', 'NAME', 'ADDRESS', 'CITY', 'STALP', 'ZIP', 'X', 'Y'}
        assert column_names == expected_columns
    
    def test_row_structure(self, generator, sample_csv_file):
        """Test that rows are correctly created"""
        results = generator.process_csv(sample_csv_file)
        
        # Check rows
        rows = list(generator.graph.subjects(RDF.type, FDIC.Row))
        assert len(rows) == 3
        
        # Check row indices
        indices = []
        for row in rows:
            idx = generator.graph.value(row, FDIC.rowIndex)
            if idx is not None:
                indices.append(int(idx))
        
        assert sorted(indices) == [0, 1, 2]
    
    def test_cell_structure(self, generator, sample_csv_file):
        """Test that cells are correctly created"""
        results = generator.process_csv(sample_csv_file)
        
        # Check cells
        cells = list(generator.graph.subjects(RDF.type, FDIC.Cell))
        assert len(cells) > 0
        
        # Check a specific cell value
        for cell in cells:
            value = generator.graph.value(cell, FDIC.value)
            if str(value) == "First National Bank":
                # Found the bank name cell
                row = generator.graph.value(cell, FDIC.inRow)
                col = generator.graph.value(cell, FDIC.inColumn)
                assert row is not None
                assert col is not None
                
                # Check that this column is NAME
                col_name = generator.graph.value(col, FDIC.columnName)
                assert str(col_name) == "NAME"
                break
        else:
            pytest.fail("Could not find expected cell value")
    
    def test_column_annotations_linked(self, generator, sample_csv_file):
        """Test that column annotations are properly linked"""
        results = generator.process_csv(sample_csv_file)
        
        # Check if annotations are loaded
        annotations = list(generator.graph.subjects(RDF.type, FDIC.ColumnAnnotation))
        
        if annotations:
            # Check that some columns have annotations
            annotated_columns = 0
            for col in generator.graph.subjects(RDF.type, FDIC.Column):
                annotation = generator.graph.value(col, FDIC.hasAnnotation)
                if annotation:
                    annotated_columns += 1
            
            assert annotated_columns > 0
    
    def test_empty_cells_not_created(self, generator):
        """Test that empty cells are not created"""
        content = """CERT,NAME,ADDRESS
1,Bank One,
2,,456 Street
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)
        
        try:
            results = generator.process_csv(temp_path)
            
            # Count cells - should only have non-empty values
            cells = list(generator.graph.subjects(RDF.type, FDIC.Cell))
            cell_values = []
            for cell in cells:
                value = generator.graph.value(cell, FDIC.value)
                if value:
                    cell_values.append(str(value))
            
            # Should have: 1, Bank One, 2, 456 Street
            assert len(cell_values) == 4
            assert "1" in cell_values
            assert "Bank One" in cell_values
            assert "2" in cell_values
            assert "456 Street" in cell_values
        finally:
            temp_path.unlink()
    
    def test_html_report_generation(self, generator, sample_csv_file):
        """Test HTML report generation"""
        results = generator.process_csv(sample_csv_file)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            report_path = Path(f.name)
        
        try:
            generator.generate_html_report(report_path, sample_csv_file.name, results)
            
            assert report_path.exists()
            content = report_path.read_text()
            
            # Check key elements
            assert "FDIC RDF Conversion Report" in content
            assert str(results['rows_processed']) in content
            assert str(results['triples_generated']) in content
            assert sample_csv_file.name in content
        finally:
            report_path.unlink()
    
    def test_viewer_output_generation(self, generator, sample_csv_file):
        """Test viewer output generation"""
        results = generator.process_csv(sample_csv_file)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            viewer_results = generator.generate_viewer_output(output_dir, rows_per_page=2)
            
            assert 'error' not in viewer_results
            assert viewer_results['total_rows'] == 3
            assert viewer_results['total_pages'] == 2
            
            # Check manifest file
            manifest_path = output_dir / "manifest.json"
            assert manifest_path.exists()
            
            # Check page files
            assert (output_dir / "page_0.json").exists()
            assert (output_dir / "page_1.json").exists()
            
            # Check manifest content
            import json
            manifest = json.loads(manifest_path.read_text())
            assert manifest['total_rows'] == 3
            assert manifest['headers'] == ['CERT', 'NAME', 'ADDRESS', 'CITY', 'STALP', 'ZIP', 'X', 'Y']
    
    def test_base_uri_customization(self):
        """Test custom base URI"""
        custom_uri = "http://mycompany.com/fdic/"
        generator = FDICRDFGenerator(base_uri=custom_uri)
        assert generator.base_uri == custom_uri
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("CERT,NAME\n1,Test Bank")
            temp_path = Path(f.name)
        
        try:
            results = generator.process_csv(temp_path)
            assert results['table_uri'].startswith(custom_uri)
        finally:
            temp_path.unlink()


class TestColumnAnnotations:
    """Test cases for column annotation functionality"""
    
    def test_annotation_file_exists(self):
        """Test that annotation file exists"""
        annotations_file = Path(__file__).parent.parent / "fdic_omg" / "annotations" / "column_annotations.ttl"
        assert annotations_file.exists()
    
    def test_annotation_structure(self):
        """Test annotation file structure"""
        annotations_file = Path(__file__).parent.parent / "fdic_omg" / "annotations" / "column_annotations.ttl"
        
        graph = Graph()
        graph.parse(annotations_file, format="turtle")
        
        # Check that annotations exist
        annotations = list(graph.subjects(RDF.type, FDIC.ColumnAnnotation))
        assert len(annotations) > 0
        
        # Check required properties
        for annotation in annotations:
            col_name = graph.value(annotation, FDIC.columnName)
            assert col_name is not None
            
            # Check optional properties
            desc = graph.value(annotation, DCTERMS.description)
            data_type = graph.value(annotation, FDIC.dataType)
            see_also = list(graph.objects(annotation, RDFS.seeAlso))
            
            # At least some annotations should have these
            if str(col_name) in ['NAME', 'X', 'Y', 'CERT']:
                assert desc is not None
                assert data_type is not None
                assert len(see_also) > 0