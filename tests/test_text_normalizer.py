"""Tests for text normalizer module."""

import pytest
import pandas as pd

from modules.text_normalizer import normalize_text


class TestTextNormalizer:
    """Test text normalization."""
    
    @pytest.fixture
    def df_with_text(self):
        """Create DataFrame with text data."""
        return pd.DataFrame({
            'text': ['HELLO World!!!', 'Test@#$ STRING', 'normal text'],
            'numeric': [1, 2, 3]
        })
        
    def test_lowercase(self, df_with_text):
        """Test lowercase conversion."""
        result = normalize_text(
            df_with_text, 
            ['text'], 
            lowercase=True,
            remove_punct=False
        )
        
        assert result['text'].iloc[0] == 'hello world!!!'
        assert result['text'].iloc[1] == 'test@#$ string'
        
    def test_remove_punctuation(self, df_with_text):
        """Test punctuation removal."""
        result = normalize_text(
            df_with_text, 
            ['text'], 
            lowercase=False,
            remove_punct=True
        )
        
        assert result['text'].iloc[0] == 'HELLO World'
        assert result['text'].iloc[1] == 'Test STRING'
        
    def test_combined_normalization(self, df_with_text):
        """Test combined normalization options."""
        result = normalize_text(
            df_with_text, 
            ['text'], 
            lowercase=True,
            remove_punct=True
        )
        
        assert result['text'].iloc[0] == 'hello world'
        assert result['text'].iloc[1] == 'test string'
        
    def test_invalid_column_type(self, df_with_text):
        """Test error on non-text column."""
        with pytest.raises(ValueError, match="not text type"):
            normalize_text(df_with_text, ['numeric'])
