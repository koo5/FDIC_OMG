#!/usr/bin/env python3
"""Test suite for FDIC OMG CLI functionality"""

import pytest
import tempfile
from pathlib import Path
from click.testing import CliRunner
from rdflib import Graph

from fdic_omg.cli import cli, generate_fdic_rdf


@pytest.fixture
def runner():
    """Create a CLI test runner"""
    return CliRunner()


@pytest.fixture
def sample_csv_file():
    """Create a temporary CSV file with sample FDIC data"""
    content = """CERT,NAME,ADDRESS,CITY,STALP,ZIP,X,Y
57,First National Bank,123 Main St,Springfield,IL,62701,-89.6501,39.7817
628,Second State Bank,456 Oak Ave,Chicago,IL,60601,-87.6298,41.8781
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(content)
        temp_path = Path(f.name)
    yield temp_path
    temp_path.unlink()


class TestCLI:
    """Test cases for CLI functionality"""
    
    def test_cli_help(self, runner):
        """Test CLI help output"""
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'FDIC OMG Semantic Augmentation CLI' in result.output
        assert '--output-dir' in result.output
        assert '--max-rows' in result.output
        assert '--no-viewer' in result.output
        assert '--no-report' in result.output
    
    def test_cli_basic_conversion(self, runner, sample_csv_file):
        """Test basic CSV to RDF conversion"""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "test_output"
            
            result = runner.invoke(cli, [str(sample_csv_file), '-d', str(output_dir)])
            assert result.exit_code == 0
            assert 'Processing' in result.output
            assert 'RDF written to' in result.output
            
            # Check output files exist
            assert (output_dir / "output.ttl").exists()
            assert (output_dir / "report.html").exists()
            assert (output_dir / "viewer").exists()
            
            # Check RDF is valid
            graph = Graph()
            graph.parse(output_dir / "output.ttl", format='turtle')
            assert len(graph) > 0
    
    def test_cli_default_output(self, runner, sample_csv_file):
        """Test default output with timestamped directory"""
        result = runner.invoke(cli, [str(sample_csv_file)])
        assert result.exit_code == 0
        
        # Should create a timestamped directory
        assert 'fdic_output_' in result.output
        assert 'Output directory:' in result.output
        
        # Extract directory name from output
        import re
        match = re.search(r'Output directory: (fdic_output_\d+_\d+)', result.output)
        assert match is not None
        output_dir = Path(match.group(1))
        
        try:
            assert output_dir.exists()
            assert (output_dir / "output.ttl").exists()
        finally:
            import shutil
            if output_dir.exists():
                shutil.rmtree(output_dir)
    
    def test_cli_with_row_limit(self, runner, sample_csv_file):
        """Test conversion with row limit"""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "test_output"
            
            result = runner.invoke(cli, [
                str(sample_csv_file), 
                '-d', str(output_dir),
                '--max-rows', '1'
            ])
            assert result.exit_code == 0
            assert 'Processed 1 CSV rows' in result.output
    
    def test_cli_no_report(self, runner, sample_csv_file):
        """Test skipping HTML report generation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "test_output"
            
            result = runner.invoke(cli, [
                str(sample_csv_file),
                '-d', str(output_dir),
                '--no-report'
            ])
            assert result.exit_code == 0
            assert 'HTML report written' not in result.output
            
            # Check report file doesn't exist
            assert (output_dir / "output.ttl").exists()
            assert not (output_dir / "report.html").exists()
    
    def test_cli_no_viewer(self, runner, sample_csv_file):
        """Test skipping viewer generation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "test_output"
            
            result = runner.invoke(cli, [
                str(sample_csv_file),
                '-d', str(output_dir),
                '--no-viewer'
            ])
            assert result.exit_code == 0
            assert 'Interactive viewer generated' not in result.output
            
            # Check viewer directory doesn't exist
            assert (output_dir / "output.ttl").exists()
            assert not (output_dir / "viewer").exists()
    
    def test_cli_with_custom_base_uri(self, runner, sample_csv_file):
        """Test custom base URI"""
        custom_uri = "http://mycompany.com/fdic/"
        
        result = runner.invoke(cli, [
            str(sample_csv_file),
            '--base-uri', custom_uri
        ])
        assert result.exit_code == 0
        assert custom_uri in result.output
    
    def test_cli_verbose_mode(self, runner, sample_csv_file):
        """Test verbose mode"""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "test_output"
            
            result = runner.invoke(cli, [
                str(sample_csv_file),
                '-d', str(output_dir),
                '-v'
            ])
            assert result.exit_code == 0
            assert '--- Summary ---' in result.output
            assert 'RDF triples' in result.output
            assert 'CSV rows' in result.output
    
    def test_cli_all_options(self, runner, sample_csv_file):
        """Test CLI with all options combined"""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "test_output"
            
            result = runner.invoke(cli, [
                str(sample_csv_file),
                '-d', str(output_dir),
                '--max-rows', '2',
                '--rows-per-page', '1',
                '--no-report',
                '--no-viewer',
                '-v'
            ])
            
            assert result.exit_code == 0
            assert (output_dir / "output.ttl").exists()
            assert not (output_dir / "report.html").exists()
            assert not (output_dir / "viewer").exists()
    
    def test_cli_nonexistent_file(self, runner):
        """Test CLI with non-existent file"""
        result = runner.invoke(cli, ['nonexistent.csv'])
        assert result.exit_code != 0
    
    def test_cli_invalid_csv(self, runner):
        """Test CLI with invalid CSV"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("This is not a valid CSV\n!!!")
            temp_path = Path(f.name)
        
        try:
            result = runner.invoke(cli, [str(temp_path)])
            # Should still work, just with weird column names
            assert result.exit_code == 0
        finally:
            temp_path.unlink()


class TestGenerateFDICRDF:
    """Test cases for generate_fdic_rdf function"""
    
    def test_generate_function(self, sample_csv_file):
        """Test the generate_fdic_rdf function"""
        results = generate_fdic_rdf(
            str(sample_csv_file),
            "http://example.org/test/",
            max_rows=1
        )
        
        assert 'rows_processed' in results
        assert 'triples_generated' in results
        assert 'table_uri' in results
        assert 'graph' in results
        assert results['rows_processed'] == 1