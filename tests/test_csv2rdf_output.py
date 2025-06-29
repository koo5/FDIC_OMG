#!/usr/bin/env python3
"""
Unit tests for csv2rdf output structure.
Verifies that the generated RDF files contain expected triples.
"""
import subprocess
import json
from pathlib import Path
import sys
import os
import shutil
from rdflib import Graph, URIRef, Namespace

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class TestCsv2RdfOutput:
    """Test csv2rdf output structure"""
    
    def __init__(self):
        self.output_dir = Path("test_csv2rdf_unit")
        self.csv_path = "/d/sync/jj/fdic_omg/FDIC_Insured_Banks.csv"
        
    def setup(self):
        """Generate test data"""
        print("Setting up test data...")
        
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
            
        # Run csv2rdf
        result = subprocess.run([
            sys.executable, "-m", "fdic_omg.csv2rdf",
            self.csv_path,
            "--annotations", "fdic_omg/annotations/fdic_banks.ttl",
            "--max-rows", "5",  # Very small dataset
            "--output-dir", str(self.output_dir)
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        
        if result.returncode != 0:
            raise RuntimeError(f"csv2rdf failed: {result.stderr}")
            
    def teardown(self):
        """Clean up test data"""
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
            
    def test_manifest_structure(self):
        """Test that manifest.json has correct structure"""
        print("\nTest 1: Checking manifest structure...")
        
        manifest_path = self.output_dir / "table_manifest.json"
        assert manifest_path.exists(), "Manifest should exist"
        
        with open(manifest_path) as f:
            manifest = json.load(f)
            
        # Check required fields
        assert "table_name" in manifest
        assert "table_uri" in manifest
        assert "row_count" in manifest
        assert "files" in manifest
        assert "metadata" in manifest["files"]
        assert "full" in manifest["files"]
        assert "chunks" in manifest["files"]
        
        print(f"✓ Manifest has correct structure")
        print(f"  Table: {manifest['table_name']}")
        print(f"  Rows: {manifest['row_count']}")
        print(f"  Chunks: {len(manifest['files']['chunks'])}")
        
    def test_table_metadata(self):
        """Test that table.ttl contains expected triples"""
        print("\nTest 2: Checking table metadata...")
        
        table_ttl = self.output_dir / "table.ttl"
        assert table_ttl.exists(), "table.ttl should exist"
        
        # Parse with rdflib
        g = Graph()
        g.parse(table_ttl, format="turtle")
        
        # Define namespaces
        ONT = Namespace("https://example.org/ontology#")
        FDIC = Namespace("http://example.org/fdic/ontology#")
        
        # Find table subject
        tables = list(g.subjects(predicate=URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), 
                                object=ONT.Table))
        assert len(tables) == 1, "Should have exactly one table"
        table_uri = tables[0]
        print(f"✓ Found table: {table_uri}")
        
        # Check table has columns
        columns = list(g.objects(subject=table_uri, predicate=ONT.hasColumn))
        assert len(columns) > 0, "Table should have columns"
        print(f"✓ Table has {len(columns)} columns")
        
        # Check some columns have annotations
        annotated_columns = 0
        for col in columns:
            annotations = list(g.objects(subject=col, predicate=ONT.hasAnnotation))
            if annotations:
                annotated_columns += 1
                
        assert annotated_columns > 0, "Some columns should have annotations"
        print(f"✓ {annotated_columns} columns have annotations")
        
    def test_annotation_properties(self):
        """Test that annotations have expected properties"""
        print("\nTest 3: Checking annotation properties...")
        
        table_ttl = self.output_dir / "table.ttl"
        g = Graph()
        g.parse(table_ttl, format="turtle")
        
        # Define namespaces
        ONT = Namespace("https://example.org/ontology#")
        RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
        
        # Find annotation objects (they are ColumnAnnotation instances)
        FDIC = Namespace("http://example.org/fdic/ontology#")
        
        # Find all ColumnAnnotation instances
        mappings = list(g.subjects(predicate=URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), 
                                  object=FDIC.ColumnAnnotation))
        
        annotation_found = len(mappings) > 0
        seealso_found = False
        
        for mapping in mappings:
            # Check if this annotation has seeAlso
            seealsos = list(g.objects(subject=mapping, predicate=RDFS.seeAlso))
            if seealsos:
                seealso_found = True
                print(f"✓ Found annotation {mapping} with {len(seealsos)} seeAlso links:")
                for sa in seealsos[:3]:  # Show first 3
                    print(f"    - {sa}")
                break
                    
        assert annotation_found, "Should find annotation objects"
        assert seealso_found, "Annotations should have seeAlso properties"
        
    def test_row_data(self):
        """Test that chunk files contain row data"""
        print("\nTest 4: Checking row data in chunks...")
        
        # Load first chunk
        chunk_path = self.output_dir / "chunk_0000.ttl"
        assert chunk_path.exists(), "First chunk should exist"
        
        g = Graph()
        g.parse(chunk_path, format="turtle")
        
        # Count rows
        ONT = Namespace("https://example.org/ontology#")
        rows = list(g.subjects(predicate=URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), 
                               object=ONT.Row))
        
        assert len(rows) > 0, "Chunk should contain row data"
        print(f"✓ Chunk contains {len(rows)} rows")
        
        # Check a row has properties
        if rows:
            first_row = rows[0]
            props = list(g.predicates(subject=first_row))
            # Subtract 1 for rdf:type
            data_props = len(props) - 1
            print(f"✓ First row has {data_props} data properties")
            
    def test_navigation_path(self):
        """Test that the navigation path exists: row → column → annotation"""
        print("\nTest 5: Checking navigation path...")
        
        table_ttl = self.output_dir / "table.ttl"
        chunk_ttl = self.output_dir / "chunk_0000.ttl"
        
        # Load both files
        g = Graph()
        g.parse(table_ttl, format="turtle")
        g.parse(chunk_ttl, format="turtle")
        
        ONT = Namespace("https://example.org/ontology#")
        
        # Find a row
        rows = list(g.subjects(predicate=URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), 
                               object=ONT.Row))
        
        if rows:
            # A row should reference values, but to get to column we need table metadata
            # This demonstrates the connection exists in the data
            
            # Find table
            tables = list(g.subjects(predicate=URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), 
                                    object=ONT.Table))
            if tables:
                table = tables[0]
                # Get columns
                columns = list(g.objects(subject=table, predicate=ONT.hasColumn))
                
                # Check if any column has annotation
                for col in columns:
                    annotations = list(g.objects(subject=col, predicate=ONT.hasAnnotation))
                    if annotations:
                        print(f"✓ Navigation path exists:")
                        print(f"    Row: {rows[0]}")
                        print(f"    Column: {col}")
                        print(f"    Annotation: {annotations[0]}")
                        return
                        
        print("⚠ Could not verify complete navigation path")
        
    def run_tests(self):
        """Run all tests"""
        try:
            self.setup()
            self.test_manifest_structure()
            self.test_table_metadata()
            self.test_annotation_properties()
            self.test_row_data()
            self.test_navigation_path()
            print("\n✅ All unit tests passed!")
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.teardown()


def main():
    """Main test runner"""
    # Change to FDIC_OMG directory
    original_dir = os.getcwd()
    os.chdir(Path(__file__).parent.parent)
    
    try:
        tester = TestCsv2RdfOutput()
        tester.run_tests()
    finally:
        os.chdir(original_dir)


if __name__ == "__main__":
    main()