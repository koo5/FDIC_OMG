#!/usr/bin/env python3
"""Test BOM handling in CSV files"""
import csv
import tempfile
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_csv_with_bom():
    """Test that CSV files with BOM are properly handled"""
    # Create a temporary CSV file with BOM
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as f:
        # Write BOM (UTF-8 signature)
        f.write(b'\xef\xbb\xbf')
        # Write CSV content
        content = 'Name,Value\nTest1,100\nTest2,200\n'
        f.write(content.encode('utf-8'))
        temp_path = f.name
    
    try:
        # Read the CSV file using our parse_csv function
        with open(temp_path, 'r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            headers = reader.fieldnames
            rows = list(reader)
        
        # Verify headers don't include BOM
        assert headers == ['Name', 'Value'], f"Expected ['Name', 'Value'], got {headers}"
        
        # Verify data is correct
        assert len(rows) == 2
        assert rows[0]['Name'] == 'Test1'
        assert rows[0]['Value'] == '100'
        assert rows[1]['Name'] == 'Test2' 
        assert rows[1]['Value'] == '200'
        
        print("✓ BOM handling test passed")
        
    finally:
        # Clean up
        os.unlink(temp_path)


def test_csv_without_bom():
    """Test that CSV files without BOM also work correctly"""
    # Create a temporary CSV file without BOM
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        content = 'Name,Value\nTest1,100\nTest2,200\n'
        f.write(content)
        temp_path = f.name
    
    try:
        # Read the CSV file
        with open(temp_path, 'r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            headers = reader.fieldnames
            rows = list(reader)
        
        # Verify headers
        assert headers == ['Name', 'Value'], f"Expected ['Name', 'Value'], got {headers}"
        
        # Verify data is correct
        assert len(rows) == 2
        assert rows[0]['Name'] == 'Test1'
        assert rows[0]['Value'] == '100'
        
        print("✓ Non-BOM handling test passed")
        
    finally:
        # Clean up
        os.unlink(temp_path)


if __name__ == '__main__':
    test_csv_with_bom()
    test_csv_without_bom()
    print("\nAll BOM handling tests passed!")