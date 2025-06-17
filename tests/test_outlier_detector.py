"""Tests for outlier detector module."""

import pytest
import pandas as pd
import numpy as np

from modules.outlier_detector import detect_outliers


class TestOutlierDetector:
    """Test outlier detection."""
    
    @pytest.fixture
    def df_with_outliers(self):
        """Create DataFrame with outliers."""
        np.random.seed(42)
        data = np.random.randn(100)
        data[0] = 100  # Clear outlier
        data[1] = -100  # Clear outlier
        
        return pd.DataFrame({
            'values': data,
            'normal': np.random.randn(100)
        })
        
    def test_iqr_detection(self, df_with_outliers):
        """Test IQR outlier detection."""
        result = detect_outliers(
            df_with_outliers, 
            ['values'], 
            method='iqr',
            action='remove'
        )
        
        assert len(result) < len(df_with_outliers)
        assert 100 not in result['values'].values
        assert -100 not in result['values'].values
        
    def test_zscore_detection(self, df_with_outliers):
        """Test Z-score outlier detection."""
        result = detect_outliers(
            df_with_outliers, 
            ['values'], 
            method='zscore',
            threshold=3,
            action='flag'
        )
        
        assert 'is_outlier' in result.columns
        assert result.iloc[0]['is_outlier'] == True
        assert result.iloc[1]['is_outlier'] == True
        
    def test_zero_variance_warning(self):
        """Test warning on zero variance column."""
        df = pd.DataFrame({
            'constant': [1, 1, 1, 1, 1],
            'normal': [1, 2, 3, 4, 5]
        })
        
        with pytest.warns(UserWarning, match="zero variance"):
            result = detect_outliers(df, ['constant', 'normal'], method='iqr')
            
    def test_non_numeric_column(self, df_with_outliers):
        """Test error on non-numeric column."""
        df_with_outliers['text'] = 'abc'
        
        with pytest.raises(ValueError, match="not numeric"):
            detect_outliers(df_with_outliers, ['text'], method='iqr')
