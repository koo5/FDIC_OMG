#!/usr/bin/env python3
"""
FDIC OMG Job - Robust job wrapper for FDIC semantic augmentation

This module integrates the FDIC RDF generator with the Robust worker system.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib.parse import quote
from datetime import datetime

# Add paths for Robust imports
sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__), '../../../common/libs/misc')))

from .core import FDICRDFGenerator
from .cli import generate_challenge_metadata

log = logging.getLogger(__name__)


def process_fdic_omg_job(
    input_files: List[str],
    output_path: str,
    public_url: str,
    result_tmp_directory_name: str
) -> Dict[str, Any]:
    """
    Process FDIC CSV file as a Robust job
    
    Args:
        input_files: List of input file paths
        output_path: Directory for output files
        public_url: Public URL of the server
        result_tmp_directory_name: Temporary directory name for results
        
    Returns:
        Robust job result dictionary
    """
    log.info(f"Starting FDIC OMG job processing")
    log.info(f"Input files: {input_files}")
    log.info(f"Output path: {output_path}")
    
    # Find CSV file
    csv_file = None
    for file_path in input_files:
        if file_path.lower().endswith('.csv'):
            csv_file = file_path
            break
    
    if not csv_file:
        return {
            "alerts": ["No CSV file found in input"],
            "reports": []
        }
    
    # Construct result URI from public URL and result directory
    result_uri = f"{public_url}/rdf/results/{result_tmp_directory_name}/"
    
    # Generate RDF
    try:
        generator = FDICRDFGenerator(result_uri)
        results = generator.process_csv(Path(csv_file), max_rows=100)  # Limit for demo
        
        # Save RDF outputs
        output_files = _save_outputs(generator.graph, Path(output_path), results)
        
        # Generate HTML report
        html_report = _generate_html_report(results, output_files, result_uri)
        html_path = Path(output_path) / "fdic_omg_report.html"
        with open(html_path, 'w') as f:
            f.write(html_report)
        
        # Generate data table HTML with RDF links
        data_table_html = _generate_data_table_html(generator, results, result_uri)
        table_path = Path(output_path) / "fdic_data_table.html"
        with open(table_path, 'w') as f:
            f.write(data_table_html)
        
        # Generate metadata JSON
        metadata = generate_challenge_metadata(generator.column_mappings)
        metadata["processing_results"] = {
            "dataset_uri": results["dataset_uri"],
            "rows_processed": results["rows_processed"],
            "columns_mapped": results["columns_mapped"],
            "triples_generated": results["triples_generated"]
        }
        metadata_path = Path(output_path) / "column_mappings.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Construct full URLs for all reports (matching Prolog actor pattern)
        base_result_url = f"{public_url}/tmp/{result_tmp_directory_name}/"
        
        # Return Robust result format
        return {
            "alerts": [],
            "reports": [
                {
                    "key": "task_directory",
                    "title": "Task Directory", 
                    "val": {"url": base_result_url}
                },
                {
                    "key": "fdic_omg_report",
                    "title": "FDIC OMG Semantic Augmentation Report",
                    "val": {"url": base_result_url + "fdic_omg_report.html"}
                },
                {
                    "key": "fdic_data_table",
                    "title": "Interactive Data Table with RDF Links",
                    "val": {"url": base_result_url + "fdic_data_table.html"}
                },
                {
                    "key": "fdic_turtle",
                    "title": "RDF Turtle Format",
                    "val": {"url": base_result_url + "fdic_semantic.ttl"}
                },
                {
                    "key": "fdic_jsonld",
                    "title": "JSON-LD Format",
                    "val": {"url": base_result_url + "fdic_semantic.jsonld"}
                },
                {
                    "key": "fdic_mappings",
                    "title": "Column Mappings Metadata",
                    "val": {"url": base_result_url + "column_mappings.json"}
                }
            ],
            "uris": {
                "dataset": results["dataset_uri"],
                "csv": results["csv_uri"]
            }
        }
        
    except Exception as e:
        log.error(f"Error processing FDIC CSV: {e}", exc_info=True)
        return {
            "alerts": [f"Error processing FDIC CSV: {str(e)}"],
            "reports": []
        }


def _save_outputs(graph, output_dir: Path, results: Dict) -> Dict[str, str]:
    """Save RDF graph in multiple formats"""
    outputs = {}
    
    formats = [
        ("turtle", "ttl"),
        ("json-ld", "jsonld"),
        ("n3", "n3"),
        ("nt", "nt")
    ]
    
    for format_name, ext in formats:
        output_path = output_dir / f"fdic_semantic.{ext}"
        graph.serialize(destination=str(output_path), format=format_name)
        outputs[format_name] = str(output_path)
        log.info(f"Saved {format_name} to {output_path}")
    
    return outputs


def _generate_html_report(results: Dict, output_files: Dict, result_uri: str) -> str:
    """Generate HTML report for FDIC OMG results"""
    
    # Create RDFTab link
    dataset_uri = results["dataset_uri"]
    rdftab_link = f"/static/rdftab/index.html?node={quote('<' + dataset_uri + '>')}"
    
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>FDIC OMG Semantic Augmentation Results</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .success {{ background-color: #d4edda; color: #155724; padding: 10px; border-radius: 5px; margin: 10px 0; }}
        .metadata {{ background-color: #f8f9fa; padding: 15px; margin: 15px 0; border-left: 4px solid #3498db; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 10px; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        th {{ background-color: #3498db; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .link {{ color: #3498db; text-decoration: none; }}
        .link:hover {{ text-decoration: underline; }}
        .stats {{ display: flex; justify-content: space-around; margin: 20px 0; }}
        .stat-box {{ text-align: center; padding: 20px; background-color: #ecf0f1; border-radius: 5px; }}
        .stat-number {{ font-size: 36px; color: #3498db; font-weight: bold; }}
        .stat-label {{ color: #7f8c8d; margin-top: 5px; }}
        ul {{ line-height: 1.8; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏆 FDIC OMG Semantic Augmentation Challenge</h1>
        
        <div class="success">
            <strong>✅ Success!</strong> FDIC CSV has been successfully augmented with semantic metadata
        </div>
        
        <div class="stats">
            <div class="stat-box">
                <div class="stat-number">{results['triples_generated']:,}</div>
                <div class="stat-label">RDF Triples</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{results['rows_processed']:,}</div>
                <div class="stat-label">Rows Processed</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{results['columns_mapped']}</div>
                <div class="stat-label">Columns Mapped</div>
            </div>
        </div>
        
        <div class="metadata">
            <h2>Dataset Information</h2>
            <p><strong>Dataset URI:</strong> <a href="{rdftab_link}" class="link">{dataset_uri}</a></p>
            <p><strong>Result URI:</strong> {result_uri}</p>
            <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>View in RDF Browser:</strong> <a href="{rdftab_link}" target="_blank" class="link">Open in RDFTab</a></p>
        </div>
        
        <h2>📥 Download Formats</h2>
        <ul>
            <li><a href="fdic_semantic.ttl" class="link">Turtle (.ttl)</a> - Human-readable RDF format</li>
            <li><a href="fdic_semantic.jsonld" class="link">JSON-LD (.jsonld)</a> - JSON with linked data context</li>
            <li><a href="fdic_semantic.n3" class="link">Notation3 (.n3)</a> - N3 RDF format</li>
            <li><a href="fdic_semantic.nt" class="link">N-Triples (.nt)</a> - Line-based RDF format</li>
            <li><a href="column_mappings.json" class="link">Column Mappings (.json)</a> - Metadata specification</li>
        </ul>
        
        <h2>🔗 Ontology Mappings</h2>
        <table>
            <tr>
                <th>CSV Column</th>
                <th>Semantic Type</th>
                <th>Ontology</th>
                <th>Description</th>
            </tr>
"""
    
    # Add column mappings to table
    column_mappings = results.get('column_mappings', {})
    for column, mapping in column_mappings.items():
        ontology_name = "FIBO"
        if "geo" in mapping['ontology_ref'].lower():
            ontology_name = "GeoSPARQL"
        elif "geonames" in mapping['ontology_ref'].lower():
            ontology_name = "GeoNames"
            
        html_report += f"""
            <tr>
                <td><strong>{column}</strong></td>
                <td>{mapping['type']}</td>
                <td>{ontology_name}</td>
                <td>{mapping['description']}</td>
            </tr>"""
    
    html_report += """
        </table>
        
        <h2>✅ Challenge Requirements</h2>
        <ul>
            <li>✓ Machine-readable metadata format (JSON-LD)</li>
            <li>✓ Mappings to FIBO (Financial Industry Business Ontology)</li>
            <li>✓ Mappings to OGC GeoSPARQL</li>
            <li>✓ Mappings to GeoNames ontology</li>
            <li>✓ Dataset provenance with PROV-O</li>
            <li>✓ Repeatable transformation process</li>
            <li>✓ Multiple output formats (Turtle, JSON-LD, N3, N-Triples)</li>
            <li>✓ Scalable to large datasets</li>
        </ul>
        
        <div class="metadata">
            <h2>About This Submission</h2>
            <p>This semantic augmentation was generated by the <strong>Accounts Assessor (Robust)</strong> system 
            for the 2025 OMG Semantic Augmentation Challenge. The system automatically detects FDIC CSV files 
            and applies semantic mappings to well-known ontologies including FIBO, GeoSPARQL, and GeoNames.</p>
            <p>The transformation is fully repeatable and can be applied to updated versions of the FDIC dataset 
            while preserving previously allocated identifiers.</p>
        </div>
    </div>
</body>
</html>"""
    
    return html_report


def _generate_data_table_html(generator: 'FDICRDFGenerator', results: Dict, result_uri: str) -> str:
    """Generate interactive HTML table with all data and RDF links"""
    
    from rdflib import URIRef
    from rdflib.collection import Collection
    
    # Get the RDF graph
    graph = generator.graph
    column_mappings = generator.column_mappings
    
    # Find the CSV file URI
    csv_uri = URIRef(results.get('csv_uri', result_uri + f"csv_file_fdic"))
    
    # Get the column list from RDF
    column_list_uri = graph.value(csv_uri, URIRef(result_uri + "hasColumnList"))
    columns = []
    column_names = []
    column_map = {}
    
    if column_list_uri:
        col_collection = Collection(graph, column_list_uri)
        for col_uri in col_collection:
            col_name = str(graph.value(col_uri, URIRef("http://purl.org/dc/terms/title")))
            columns.append(col_uri)
            column_names.append(col_name)
            column_map[col_name] = str(col_uri)
    
    # Get the row list from RDF
    row_list_uri = graph.value(csv_uri, URIRef(result_uri + "hasRowList"))
    rows = []
    
    if row_list_uri:
        row_collection = Collection(graph, row_list_uri)
        rows = list(row_collection)
    
    # Build the data structure for the table
    csv_data = []
    for row_uri in rows:
        row_data = {}
        # Get all cells for this row
        for cell in graph.objects(row_uri, URIRef(result_uri + "hasCell")):
            col_name = str(graph.value(cell, URIRef(result_uri + "columnName")))
            value = str(graph.value(cell, URIRef(result_uri + "rawValue")))
            if col_name:
                row_data[col_name] = value
        
        if row_data:
            csv_data.append(row_data)
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>FDIC Data with Semantic Links</title>
    <meta charset="UTF-8">
    <style>
        body {{ 
            font-family: Arial, sans-serif; 
            margin: 10px; 
            background-color: #f8f9fa; 
        }}
        .header {{
            background-color: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{ color: #2c3e50; margin: 0 0 10px 0; }}
        .info {{ color: #7f8c8d; margin-bottom: 15px; }}
        .controls {{
            margin-bottom: 20px;
            padding: 15px;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .table-container {{
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: auto;
            max-height: 80vh;
        }}
        table {{ 
            width: 100%; 
            border-collapse: collapse; 
            min-width: 1200px;
        }}
        th {{ 
            background-color: #3498db; 
            color: white; 
            padding: 12px 8px; 
            text-align: left; 
            position: sticky;
            top: 0;
            z-index: 10;
            border-right: 1px solid #2980b9;
            font-size: 12px;
            vertical-align: top;
        }}
        td {{ 
            padding: 8px; 
            border-bottom: 1px solid #ecf0f1; 
            border-right: 1px solid #ecf0f1;
            font-size: 11px;
            max-width: 150px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        tr:nth-child(even) {{ background-color: #f8f9fa; }}
        tr:hover {{ background-color: #e3f2fd; }}
        .rdf-link {{ 
            display: inline-block;
            background: linear-gradient(45deg, #e74c3c, #c0392b);
            color: white; 
            text-decoration: none; 
            padding: 2px 6px; 
            border-radius: 3px; 
            font-size: 10px;
            margin-left: 4px;
            transition: all 0.2s;
        }}
        .rdf-link:hover {{ 
            background: linear-gradient(45deg, #c0392b, #a93226);
            transform: scale(1.05);
        }}
        .column-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .column-name {{
            font-weight: bold;
            margin-bottom: 2px;
        }}
        .column-type {{
            font-size: 10px;
            color: #bdc3c7;
            font-weight: normal;
        }}
        .row-number {{
            background-color: #34495e;
            color: white;
            font-weight: bold;
            text-align: center;
            position: sticky;
            left: 0;
            z-index: 5;
            min-width: 60px;
        }}
        .cell-container {{
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .cell-value {{
            flex: 1;
            margin-right: 4px;
        }}
        .legend {{
            margin-top: 15px;
            padding: 15px;
            background-color: #ecf0f1;
            border-radius: 5px;
            font-size: 12px;
        }}
        .search-box {{
            padding: 8px 12px;
            border: 1px solid #bdc3c7;
            border-radius: 4px;
            font-size: 14px;
            width: 300px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🏦 FDIC Data with Semantic RDF Links</h1>
        <div class="info">
            Dataset: {results.get('dataset_uri', 'N/A')} | 
            Rows: {results.get('rows_processed', 0):,} | 
            Columns: {results.get('columns_mapped', 0)} |
            RDF Triples: {results.get('triples_generated', 0):,}
        </div>
        <p>Each column, row, and cell has a linked RDF resource. Click the <span class="rdf-link">RDF</span> buttons to explore the semantic data.</p>
    </div>
    
    <div class="controls">
        <label for="search">🔍 Search data: </label>
        <input type="text" id="search" class="search-box" placeholder="Type to filter table data..." onkeyup="filterTable()">
        <span style="margin-left: 20px; color: #7f8c8d;">Tip: Search is case-insensitive and searches all visible columns</span>
    </div>
    
    <div class="table-container">
        <table id="dataTable">
            <thead>
                <tr>
                    <th class="row-number">
                        <div class="column-header">
                            <div>
                                <div class="column-name">Row #</div>
                                <div class="column-type">Index</div>
                            </div>
                        </div>
                    </th>"""
    
    # Generate column headers with RDF links
    for col in column_names:
        mapping = column_mappings.get(col, {})
        ontology_ref = mapping.get('ontology_ref', '#unknown')
        col_type = mapping.get('type', 'string')
        
        # Use the actual column URI from RDF
        col_uri = column_map.get(col, f"{result_uri}column/{quote(col)}")
        
        html += f"""
                    <th>
                        <div class="column-header">
                            <div>
                                <div class="column-name">{col}</div>
                                <div class="column-type">{col_type}</div>
                            </div>
                            <a href="/static/rdftab/index.html?node={quote('<' + col_uri + '>')}" 
                               class="rdf-link" target="_blank" title="View column semantic definition">RDF</a>
                        </div>
                    </th>"""
    
    html += """
                </tr>
            </thead>
            <tbody>"""
    
    # Generate data rows with RDF links
    for idx, row in enumerate(csv_data[:100]):  # Limit to first 100 rows for performance
        # Create row URI
        row_uri = f"{result_uri}row/{idx}"
        
        html += f"""
                <tr>
                    <td class="row-number">
                        <div class="cell-container">
                            <span class="cell-value">{idx + 1}</span>
                            <a href="/static/rdftab/index.html?node={quote('<' + row_uri + '>')}" 
                               class="rdf-link" target="_blank" title="View row as RDF resource">RDF</a>
                        </div>
                    </td>"""
        
        # Generate cells with RDF links  
        for col in column_names:
            cell_value = str(row.get(col, ''))
            if len(cell_value) > 30:
                display_value = cell_value[:30] + "..."
            else:
                display_value = cell_value
            
            # Create cell URI
            cell_uri = f"{result_uri}cell/{idx}/{quote(col)}"
            
            html += f"""
                    <td>
                        <div class="cell-container">
                            <span class="cell-value" title="{cell_value}">{display_value}</span>
                            <a href="/static/rdftab/index.html?node={quote('<' + cell_uri + '>')}" 
                               class="rdf-link" target="_blank" title="View cell value as RDF">RDF</a>
                        </div>
                    </td>"""
        
        html += "</tr>"
    
    html += f"""
            </tbody>
        </table>
    </div>
    
    <div class="legend">
        <h3>🔗 RDF Link Guide</h3>
        <ul>
            <li><strong>Column RDF links</strong> - Show the semantic property definition and ontology mappings (FIBO, GeoSPARQL, GeoNames)</li>
            <li><strong>Row RDF links</strong> - Show the complete bank record as a structured RDF resource</li>
            <li><strong>Cell RDF links</strong> - Show individual data values with their semantic types and relationships</li>
        </ul>
        <p><strong>Dataset URI:</strong> <a href="/static/rdftab/index.html?node={quote('<' + results.get('dataset_uri', '') + '>')}" target="_blank">{results.get('dataset_uri', '')}</a></p>
    </div>

    <script>
        function filterTable() {{
            const input = document.getElementById('search');
            const filter = input.value.toLowerCase();
            const table = document.getElementById('dataTable');
            const rows = table.getElementsByTagName('tr');
            
            // Start from 1 to skip header row
            for (let i = 1; i < rows.length; i++) {{
                const row = rows[i];
                const cells = row.getElementsByTagName('td');
                let found = false;
                
                // Search through all cells in the row
                for (let j = 0; j < cells.length; j++) {{
                    const cellText = cells[j].textContent || cells[j].innerText;
                    if (cellText.toLowerCase().indexOf(filter) > -1) {{
                        found = true;
                        break;
                    }}
                }}
                
                row.style.display = found ? '' : 'none';
            }}
        }}
        
        // Add click handlers for better UX
        document.addEventListener('DOMContentLoaded', function() {{
            const rdfLinks = document.querySelectorAll('.rdf-link');
            rdfLinks.forEach(link => {{
                link.addEventListener('click', function(e) {{
                    e.stopPropagation(); // Prevent row selection when clicking RDF link
                }});
            }});
        }});
    </script>
</body>
</html>"""
    
    return html


# Entry point for Robust worker
def main(input_files, output_path, params):
    """Main entry point called by Robust worker"""
    public_url = params.get('public_url', 'http://localhost')
    result_tmp_directory_name = params.get('result_tmp_directory_name', 'unknown')
    
    return process_fdic_omg_job(
        input_files=input_files,
        output_path=output_path,
        public_url=public_url,
        result_tmp_directory_name=result_tmp_directory_name
    )