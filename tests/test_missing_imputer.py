"""Tests for missing imputer module."""

import pytest
import pandas as pd
import numpy as np

from modules.missing_imputer import impute_missing


class TestMissingImputer:
    """Test missing value imputation."""
    
    @pytest.fixture
    def df_with_missing(self):
        """Create DataFrame with missing values."""
        return pd.DataFrame({
            'numeric': [1.0, np.nan, 3.0, np.nan, 5.0],
            'category': ['A', 'B', np.nan, 'A', 'B']
        })
        
    def test_mean_imputation(self, df_with_missing):
        """Test mean imputation."""
        result = impute_missing(df_with_missing, ['numeric'], method='mean')
        
        assert result['numeric'].isna().sum() == 0
        assert result['numeric'].iloc[1] == 3.0  # Mean of [1, 3, 5]
        
    def test_median_imputation(self, df_with_missing):
        """Test median imputation."""
        result = impute_missing(df_with_missing, ['numeric'], method='median')
        
        assert result['numeric'].isna().sum() == 0
        assert result['numeric'].iloc[1] == 3.0
        
    def test_mode_imputation(self, df_with_missing):
        """Test mode imputation."""
        result = impute_missing(df_with_missing, ['category'], method='mode')
        
        assert result['category'].isna().sum() == 0
        assert result['category'].iloc[2] in ['A', 'B']
        
    def test_constant_imputation(self, df_with_missing):
        """Test constant value imputation."""
        result = impute_missing(
            df_with_missing, 
            ['numeric'], 
            method='constant', 
            fill_value=0
        )
        
        assert result['numeric'].isna().sum() == 0
        assert result['numeric'].iloc[1] == 0
        
    def test_invalid_column(self, df_with_missing):
        """Test error on invalid column."""
        with pytest.raises(ValueError, match="Columns not found"):
            impute_missing(df_with_missing, ['invalid'], method='mean')
