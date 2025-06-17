"""Text normalization module."""

import pandas as pd
import re
from typing import List, Optional, Dict
import string
import warnings


def normalize_text(
    df: pd.DataFrame,
    columns: List[str],
    lowercase: bool = True,
    remove_punct: bool = True,
    remove_stopwords: bool = False,
    slang_dict: Optional[Dict[str, str]] = None
) -> pd.DataFrame:
    """
    Normalize text in specified columns.
    
    Args:
        df: Input DataFrame
        columns: Text columns to normalize
        lowercase: Convert to lowercase
        remove_punct: Remove punctuation
        remove_stopwords: Remove stop words (requires NLTK)
        slang_dict: Dictionary for slang replacement
        
    Returns:
        DataFrame with normalized text
    """
    result_df = df.copy()
    
    # Validate columns
    missing_cols = set(columns) - set(result_df.columns)
    if missing_cols:
        raise ValueError(f"Columns not found: {missing_cols}")
    
    # Validate column types
    for col in columns:
        if not pd.api.types.is_string_dtype(result_df[col]) and \
           not pd.api.types.is_object_dtype(result_df[col]):
            raise ValueError(f"Column '{col}' is not text type")
    
    # Load stopwords if needed
    stopwords_set = set()
    if remove_stopwords:
        try:
            import nltk
            nltk.download('stopwords', quiet=True)
            from nltk.corpus import stopwords
            stopwords_set = set(stopwords.words('english'))
        except ImportError:
            warnings.warn("NLTK not available, skipping stopword removal")
            remove_stopwords = False
    
    # Process each column
    for col in columns:
        # Convert to string and handle NaN
        result_df[col] = result_df[col].astype(str)
        result_df.loc[result_df[col] == 'nan', col] = ''
        
        # Strip whitespace
        result_df[col] = result_df[col].str.strip()
        
        # Lowercase
        if lowercase:
            result_df[col] = result_df[col].str.lower()
        
        # Remove punctuation
        if remove_punct:
            result_df[col] = result_df[col].apply(
                lambda x: x.translate(str.maketrans('', '', string.punctuation))
            )
        
        # Replace slang
        if slang_dict:
            for slang, replacement in slang_dict.items():
                result_df[col] = result_df[col].str.replace(
                    slang, replacement, regex=False
                )
        
        # Remove stopwords
        if remove_stopwords:
            result_df[col] = result_df[col].apply(
                lambda x: ' '.join(
                    word for word in x.split() 
                    if word not in stopwords_set
                )
            )
        
        # Clean up extra whitespace
        result_df[col] = result_df[col].str.replace(r'\s+', ' ', regex=True)
        result_df[col] = result_df[col].str.strip()
    
    return result_df


# Module interface
process = normalize_text
