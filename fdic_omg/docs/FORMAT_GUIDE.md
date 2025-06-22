# FDIC Column Mappings Format Guide

This guide explains the different formats available for defining semantic mappings for FDIC CSV column data and how to work with them.

## Overview

The FDIC OMG Semantic Augmentation system supports three interchangeable formats for column mappings:

1. **TTL (Turtle)** - W3C standard RDF format, best for semantic web applications
2. **JSON-LD** - JSON-based RDF format, bridges JSON simplicity with RDF semantics
3. **YAML** - Human-readable format, easiest for manual editing

All formats contain the same information and can be converted between each other without loss of data.

## Format Comparison

| Feature | TTL | JSON-LD | YAML |
|---------|-----|---------|------|
| Human Readability | Medium | Medium | High |
| RDF Native | Yes | Yes | No (requires conversion) |
| Tool Support | RDF tools | JSON + RDF tools | YAML parsers |
| File Size | Large | Medium | Small |
| Comments | Yes | No | Yes |
| Best For | RDF processing | Web APIs | Human editing |

## File Locations

```
fdic_omg/mappings/
├── column_mappings.ttl      # Primary RDF format
├── column_mappings.jsonld   # JSON-LD alternative
└── column_mappings.yaml     # Human-friendly format
```

## Format Specifications

### TTL (Turtle) Format

The Turtle format is the primary format used by the RDF processing engine.

**Structure:**
- Namespace declarations
- Ontology metadata
- Dataset description
- Resource documentation
- Column mappings with full semantic annotations

**Example snippet:**
```turtle
fdic:column_CERT a fdic:ColumnMapping ;
    fdic:columnName "CERT" ;
    rdfs:label "FDIC Certificate Number"@en ;
    dcterms:description "Unique FDIC-assigned certificate of insurance number" ;
    fdic:semanticType "fdic_certificate" ;
    fdic:dataType "integer" ;
    rdfs:seeAlso fibo-be:GovernmentIssuedLicense ,
                  schema:identifier ;
    owl:sameAs wikidata:Q116907062 .
```

### JSON-LD Format

JSON-LD provides a JSON representation that is also valid RDF.

**Structure:**
- `@context` - Defines prefixes and term mappings
- `@graph` - Contains the actual data as an array of objects

**Example snippet:**
```json
{
  "@id": "fdic:column_CERT",
  "@type": "ColumnMapping",
  "columnName": "CERT",
  "label": "FDIC Certificate Number",
  "description": "Unique FDIC-assigned certificate of insurance number",
  "semanticType": "fdic_certificate",
  "dataType": "integer",
  "seeAlso": [
    "fibo-be:GovernmentIssuedLicense",
    "schema:identifier"
  ],
  "sameAs": "wikidata:Q116907062"
}
```

### YAML Format

The YAML format is optimized for human readability and editing.

**Structure:**
- `dataset` - Dataset metadata
- `resources` - External resource documentation
- `columns` - Column mappings
- `metadata` - File metadata

**Example snippet:**
```yaml
columns:
  CERT:
    label: FDIC Certificate Number
    description: Unique FDIC-assigned certificate of insurance number
    semantic_type: fdic_certificate
    data_type: integer
    mappings:
      - ontology: FIBO
        property: https://spec.edmcouncil.org/fibo/ontology/BE/GovernmentIssuedLicense
        relation: instance_of
    references:
      - url: http://www.wikidata.org/entity/Q116907062
        type: wikidata
```

## Column Mapping Properties

Each column mapping can include:

### Required Properties
- `columnName` / `column_name` - The exact CSV column name
- `label` - Human-readable label
- `semantic_type` - High-level semantic category
- `data_type` - Expected data type (string, integer, decimal)

### Optional Properties
- `description` - Detailed description
- `mappings` - Ontology mappings with properties and relations
- `references` - External references (Wikipedia, Wikidata, etc.)
- `comments` - Additional notes
- `standards` - Conformance to standards
- `issuer` - For identifiers, who issues them

### Semantic Types

Common semantic types used:
- `coordinate` - Geographic coordinates
- `bank_name` - Institution names
- `address` - Physical addresses
- `location` - Cities, states
- `postal_code` - ZIP codes
- `fdic_certificate` - FDIC identifiers
- `bank_class` - Classification codes
- `service_description` - Service types

### Data Types

Supported data types:
- `string` - Text values
- `integer` - Whole numbers
- `decimal` - Floating-point numbers

## Format Conversion

Use the provided converter utility to transform between formats:

```bash
# Convert TTL to YAML
python converters/format_converter.py mappings/column_mappings.ttl mappings/column_mappings.yaml

# Convert YAML to JSON-LD
python converters/format_converter.py mappings/column_mappings.yaml mappings/column_mappings.jsonld

# Convert JSON-LD to TTL
python converters/format_converter.py mappings/column_mappings.jsonld mappings/column_mappings.ttl
```

The converter automatically detects formats based on file extensions.

## Adding New Mappings

### In YAML (Recommended for manual editing):

1. Add a new entry under `columns`:
```yaml
columns:
  NEW_COLUMN:
    label: New Column Label
    description: What this column contains
    semantic_type: appropriate_type
    data_type: string|integer|decimal
    mappings:
      - ontology: FIBO
        property: http://example.org/property
        relation: similar|equivalent|instance_of
```

2. Convert to other formats:
```bash
python converters/format_converter.py mappings/column_mappings.yaml mappings/column_mappings.ttl
```

### Mapping Relations

When defining ontology mappings, use these relations:
- `exact` - Exact match to the ontology property
- `equivalent` - Semantically equivalent
- `similar` - Related but not exact
- `instance_of` - The column contains instances of this class

## Validation

(Coming soon) Use the JSON Schema to validate your mappings:

```bash
# Validate YAML format
python validators/validate_mappings.py mappings/column_mappings.yaml

# Validate JSON-LD format
python validators/validate_mappings.py mappings/column_mappings.jsonld
```

## Best Practices

1. **Use YAML for editing** - It's the most human-friendly format
2. **Convert to TTL for processing** - The RDF engine expects TTL format
3. **Keep all formats in sync** - Use the converter after making changes
4. **Document mappings thoroughly** - Include descriptions and comments
5. **Reference authoritative sources** - Link to ontologies, standards, and definitions
6. **Use appropriate semantic types** - This helps with data validation
7. **Test conversions** - Ensure round-trip conversion preserves all data

## Extending the Formats

To add support for new properties:

1. Update the YAML structure
2. Modify `converters/format_converter.py` to handle the new properties
3. Update this documentation
4. Test round-trip conversions

## Resources

- [RDF Primer](https://www.w3.org/TR/rdf11-primer/)
- [JSON-LD Specification](https://www.w3.org/TR/json-ld11/)
- [YAML Specification](https://yaml.org/spec/1.2.2/)
- [FIBO Ontology](https://spec.edmcouncil.org/fibo/)
- [GeoSPARQL Standard](https://opengeospatial.github.io/ogc-geosparql/)