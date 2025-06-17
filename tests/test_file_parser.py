"""Tests for file parser module."""

import pytest
import pandas as pd
import tempfile
from pathlib import Path

from modules.file_parser import parse_file


class TestFileParser:
    """Test file parser functionality."""
    
    @pytest.fixture
    def sample_csv(self, tmp_path):
        """Create a sample CSV file."""
        data = pd.DataFrame({
            'A': [1, 2, 3],
            'B': ['x', 'y', 'z']
        })
        
        file_path = tmp_path / "test.csv"
        data.to_csv(file_path, index=False)
        return file_path
        
    def test_parse_csv(self, sample_csv):
        """Test CSV parsing."""
        df = parse_file(str(sample_csv))
        
        assert len(df) == 3
        assert list(df.columns) == ['A', 'B']
        assert df['A'].tolist() == [1, 2, 3]
        
    def test_auto_format_detection(self, sample_csv):
        """Test automatic format detection."""
        df = parse_file(str(sample_csv), file_format=None)
        assert len(df) == 3
        
    def test_file_not_found(self):
        """Test error on missing file."""
        with pytest.raises(FileNotFoundError):
            parse_file("nonexistent.csv")
            
    def test_unsupported_format(self, tmp_path):
        """Test error on unsupported format."""
        file_path = tmp_path / "test.xyz"
        file_path.write_text("data")
        
        with pytest.raises(ValueError, match="Unsupported file format"):
            parse_file(str(file_path))
