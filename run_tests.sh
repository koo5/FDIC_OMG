#!/bin/bash
# Script to run all FDIC OMG tests

echo "Running FDIC OMG Test Suite"
echo "==========================="

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Install test dependencies if needed
echo "Installing test dependencies..."
pip install pytest pytest-cov jsonschema

# Run all tests
echo ""
echo "Running all tests..."
pytest

# Run specific test categories
echo ""
echo "Test Summary by Category:"
echo "------------------------"

echo ""
echo "Unit Tests:"
pytest -m unit --tb=no -q

echo ""
echo "Integration Tests:"
pytest -m integration --tb=no -q

echo ""
echo "Validation Tests:"
pytest -m validation --tb=no -q

# Generate coverage report
echo ""
echo "Coverage Report:"
echo "---------------"
pytest --cov=fdic_omg --cov-report=term-missing --tb=no -q

echo ""
echo "Full HTML coverage report generated in htmlcov/"
echo "Test run complete!"