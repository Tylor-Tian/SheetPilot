"""Integration tests for the complete pipeline."""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile

from app.core.orchestrator import Orchestrator, ModuleConfig
from modules.file_parser import parse_file
from modules.missing_imputer import impute_missing
from modules.text_normalizer import normalize_text
from modules.outlier_detector import detect_outliers


class TestIntegration:
    """Integration test suite."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample test data."""
        np.random.seed(42)
        n = 100
        
        df = pd.DataFrame({
            'numeric_clean': np.random.randn(n),
            'numeric_missing': np.random.randn(n),
            'numeric_outliers': np.random.randn(n),
            'text_clean': ['text_' + str(i) for i in range(n)],
            'text_messy': ['TEXT_' + str(i) + '!!!' for i in range(n)],
            'category': np.random.choice(['A', 'B', 'C'], n)
        })
        
        # Add missing values
        missing_idx = np.random.choice(n, 20, replace=False)
        df.loc[missing_idx, 'numeric_missing'] = np.nan
        
        # Add outliers
        outlier_idx = np.random.choice(n, 5, replace=False)
        df.loc[outlier_idx, 'numeric_outliers'] = 100
        
        return df
    
    def test_full_pipeline(self, sample_data):
        """Test complete cleaning pipeline."""
        # Configure pipeline
        steps = [
            ModuleConfig(
                name="missing_imputer",
                module_func=impute_missing,
                params={
                    "columns": ["numeric_missing"],
                    "method": "mean"
                }
            ),
            ModuleConfig(
                name="text_normalizer",
                module_func=normalize_text,
                params={
                    "columns": ["text_messy"],
                    "lowercase": True,
                    "remove_punct": True
                }
            ),
            ModuleConfig(
                name="outlier_detector",
                module_func=detect_outliers,
                params={
                    "columns": ["numeric_outliers"],
                    "method": "iqr",
                    "action": "remove"
                }
            )
        ]
        
        # Run pipeline
        orchestrator = Orchestrator()
        cleaned_df, report = orchestrator.run_pipeline(sample_data, steps)
        
        # Verify results
        assert len(report.steps_completed) == 3
        assert len(report.errors) == 0
        
        # Check missing values filled
        assert cleaned_df['numeric_missing'].isna().sum() == 0
        
        # Check text normalized
        assert all(cleaned_df['text_messy'].str.islower())
        assert not any(cleaned_df['text_messy'].str.contains('!'))
        
        # Check outliers removed
        assert len(cleaned_df) < len(sample_data)
        assert cleaned_df['numeric_outliers'].max() < 100
    
    def test_file_roundtrip(self, sample_data, tmp_path):
        """Test saving and loading data."""
        # Save to CSV
        csv_path = tmp_path / "test_data.csv"
        sample_data.to_csv(csv_path, index=False)
        
        # Load and verify
        loaded_df = parse_file(str(csv_path))
        pd.testing.assert_frame_equal(
            sample_data, 
            loaded_df,
            check_dtype=False  # CSV may change dtypes
        )
        
        # Save to Excel
        excel_path = tmp_path / "test_data.xlsx"
        sample_data.to_excel(excel_path, index=False)
        
        # Load and verify
        loaded_df = parse_file(str(excel_path))
        pd.testing.assert_frame_equal(
            sample_data,
            loaded_df,
            check_dtype=False
        )
    
    def test_error_handling(self, sample_data):
        """Test pipeline error handling."""
        # Configure with invalid column
        steps = [
            ModuleConfig(
                name="missing_imputer",
                module_func=impute_missing,
                params={
                    "columns": ["nonexistent_column"],
                    "method": "mean"
                }
            )
        ]
        
        # Run with stop_on_error=False
        orchestrator = Orchestrator(stop_on_error=False)
        cleaned_df, report = orchestrator.run_pipeline(sample_data, steps)
        
        # Should complete with errors
        assert len(report.errors) == 1
        assert report.errors[0]['module'] == 'missing_imputer'
        
        # Original data should be unchanged
        pd.testing.assert_frame_equal(sample_data, cleaned_df)
    
    def test_empty_pipeline(self, sample_data):
        """Test pipeline with no steps."""
        orchestrator = Orchestrator()
        cleaned_df, report = orchestrator.run_pipeline(sample_data, [])
        
        # Should return original data
        pd.testing.assert_frame_equal(sample_data, cleaned_df)
        assert len(report.steps_completed) == 0
        assert len(report.errors) == 0


if __name__ == "__main__":
    pytest.main([__file__])
