"""Utility functions for job processing"""
from pathlib import Path
from typing import Dict
import csv
from urllib.parse import quote


def generate_simple_data_table_html(csv_path: Path, results: Dict, result_uri: str) -> str:
    """Generate simple HTML table showing CSV data with links to RDF resources"""
    
    # Read first few rows of CSV for display
    rows_to_display = 20
    csv_data = []
    headers = []
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        for i, row in enumerate(reader):
            if i >= rows_to_display:
                break
            csv_data.append(row)
    
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
        }}
        th {{ 
            background-color: #3498db; 
            color: white; 
            padding: 12px 8px; 
            text-align: left; 
            position: sticky;
            top: 0;
            z-index: 10;
            font-size: 12px;
        }}
        td {{ 
            padding: 8px; 
            border-bottom: 1px solid #ecf0f1; 
            font-size: 11px;
            max-width: 200px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        tr:nth-child(even) {{ background-color: #f8f9fa; }}
        tr:hover {{ background-color: #e3f2fd; }}
        .rdf-link {{ 
            color: #3498db;
            margin-left: 5px;
            text-decoration: none;
            font-size: 10px;
        }}
        .rdf-link:hover {{ 
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>FDIC Institutions Data - Semantic Web View</h1>
        <div class="info">
            Showing first {rows_to_display} rows of {results.get('rows_processed', 0)} total rows processed.
            <br>Table URI: <a href="{results.get('table_uri', '')}" class="rdf-link">{results.get('table_uri', '')}</a>
        </div>
    </div>
    
    <div class="table-container">
        <table>
            <thead>
                <tr>
"""
    
    # Add column headers
    for col_name in headers:
        html += f'                    <th>{col_name}</th>\n'
    
    html += """                </tr>
            </thead>
            <tbody>
"""
    
    # Add data rows
    for idx, row in enumerate(csv_data):
        html += '                <tr>\n'
        for col_name in headers:
            value = row.get(col_name, '')
            # Truncate long values for display
            display_value = value[:50] + '...' if len(value) > 50 else value
            html += f'                    <td title="{value}">{display_value}</td>\n'
        html += '                </tr>\n'
    
    html += """            </tbody>
        </table>
    </div>
</body>
</html>
"""
    
    return html