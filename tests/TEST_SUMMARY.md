# RDFTab Viewer Test Summary

## Tests Created

### 1. Unit Tests (`test_csv2rdf_output.py`)
Tests the csv2rdf output structure without requiring a browser:
- ✅ Manifest structure validation
- ✅ Table metadata contains columns
- ✅ Columns link to annotations
- ✅ Annotations have seeAlso properties
- ✅ Row data is properly formatted
- ✅ Navigation path exists: Row → Column → Annotation

### 2. Integration Tests (`test_rdftab_viewer_sync.py`)
Full browser-based testing with Playwright:
- Table loads with data
- Clicking cells opens metadata modal
- Navigation from cell to column definition
- Navigation from column to annotation
- Verification of seeAlso links in annotations
- Column info icons functionality

## Key Features Tested

### Navigation Flow
```
Table Cell (click) 
  → Cell Metadata Modal (shows quads)
    → Column Definition Link (click)
      → Column Metadata (shows hasAnnotation)
        → Annotation Link (click)
          → Annotation Object (shows seeAlso links)
```

### RDF Structure
- Table has columns via `ont:hasColumn`
- Columns have annotations via `ont:hasAnnotation`
- Annotations are `fdic:ColumnMapping` instances
- Annotations contain `rdfs:seeAlso` links to external resources

## Running Tests

### Quick Unit Test (No Browser Required)
```bash
python tests/test_csv2rdf_output.py
```

### Full Integration Test (Requires Playwright)
```bash
# Install dependencies
pip install playwright
playwright install chromium

# Run test
python tests/test_rdftab_viewer_sync.py
```

## Verified Functionality

1. **CSV to RDF Conversion**: Properly generates RDF with annotations
2. **Multi-Source Architecture**: rdftab can query multiple sources (API, SPARQL, local files)
3. **Navigation**: Users can navigate from data to metadata to documentation
4. **Annotations**: Column annotations with seeAlso links are preserved and accessible

## Example Annotation
```turtle
fdic:column_ADDRESS a fdic:ColumnMapping ;
    rdfs:label "Street Address"@en ;
    fdic:columnName "ADDRESS" ;
    rdfs:seeAlso 
        <https://spec.edmcouncil.org/fibo/ontology/FND/Places/Addresses/StreetAddress>,
        <http://www.w3.org/2006/vcard/ns#street-address>,
        <https://schema.org/streetAddress>,
        <https://pe.usps.com/text/pub28/welcome.htm> .
```