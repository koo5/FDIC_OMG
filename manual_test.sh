#!/bin/bash
echo "Generating test data..."
python -m fdic_omg.cli example/example1.csv --output-dir test_viewer_output

echo ""
echo "Starting server on port 8123..."
echo "Visit http://localhost:8123 to view the data"
echo "Press Ctrl+C to stop"
cd test_viewer_output/viewer && python -m http.server 8123