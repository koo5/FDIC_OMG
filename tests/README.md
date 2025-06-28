# RDFTab Viewer Tests

This directory contains Playwright tests for the RDFTab table viewer functionality.

## Setup

1. Install Playwright and dependencies:
```bash
pip install -r requirements.txt
playwright install chromium
```

2. Ensure you have the FDIC CSV file at `/d/sync/jj/fdic_omg/FDIC_Insured_Banks.csv`

## Running Tests

### Synchronous Test (Recommended)
```bash
python tests/test_rdftab_viewer_sync.py
```

This test will:
- Generate test data using csv2rdf
- Start a local server
- Open a browser and test the following navigation flow:
  1. Click on a table cell to view its metadata
  2. Navigate from cell metadata to column definition
  3. Navigate from column definition to annotation object
  4. Verify annotation has seeAlso properties
  5. Test column info icons in table headers

### Headless Mode

To run tests in headless mode (no visible browser), edit the test file and change:
```python
browser = p.chromium.launch(headless=False)
```
to:
```python
browser = p.chromium.launch(headless=True)
```

## Test Coverage

The test verifies:
- ✓ Table loads with data
- ✓ Clicking cells opens metadata modal
- ✓ Navigation from cell → column → annotation
- ✓ Annotation objects have seeAlso links
- ✓ Column info icons work

## Troubleshooting

If the test fails:
1. Check that the CSV file exists
2. Ensure no other process is using the test port (8766)
3. Check that rdftab was built with `npm --prefix ../../../rdftab run build:viewer`
4. Look at browser console for JavaScript errors