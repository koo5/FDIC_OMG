#!/usr/bin/env python3
"""
Test the Robust job integration with the new csv2rdf converter
"""
import sys
import json
import shutil
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fdic_omg.job import process_fdic_omg_job

def test_job_integration():
    """Test that the job module works with new converter"""
    
    # Setup
    csv_file = "/d/sync/jj/fdic_omg/FDIC_Insured_Banks.csv"
    output_dir = Path("test_job_output")
    
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir()
    
    # Run job
    result = process_fdic_omg_job(
        input_files=[csv_file],
        output_path=str(output_dir),
        public_url="http://localhost:8080",
        result_tmp_directory_name="test_job_123"
    )
    
    # Check result structure
    print("Job Result:")
    print(json.dumps(result, indent=2))
    
    # Verify expected outputs
    assert "alerts" in result
    assert "reports" in result
    assert len(result["reports"]) > 0
    
    # Check generated files
    expected_files = [
        "table.ttl",
        "full.ttl", 
        "table_manifest.json",
        "fdic_omg_report.html",
        "processing_results.json",
        "viewer/index-viewer.html"
    ]
    
    for file_name in expected_files:
        file_path = output_dir / file_name
        if file_path.exists():
            print(f"✓ Found {file_name}")
        else:
            print(f"✗ Missing {file_name}")
            
    # Check viewer was copied
    viewer_dir = output_dir / "viewer"
    if viewer_dir.exists():
        print(f"✓ Viewer directory created with {len(list(viewer_dir.iterdir()))} files")
    else:
        print("✗ Viewer directory not found")
        
    # Read manifest to verify structure
    manifest_path = output_dir / "table_manifest.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
        print(f"\nManifest:")
        print(f"  Table: {manifest.get('table_name')}")
        print(f"  Rows: {manifest.get('row_count')}")
        print(f"  Chunks: {len(manifest.get('files', {}).get('chunks', []))}")
    
    # Cleanup
    if output_dir.exists():
        shutil.rmtree(output_dir)
        
    print("\n✅ Job integration test completed!")
    
if __name__ == "__main__":
    test_job_integration()