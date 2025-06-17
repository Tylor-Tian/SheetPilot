"""Missing value imputation module."""

import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Any
from sklearn.impute import KNNImputer
import warnings


def impute_missing(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
    method: str = "mean",
    **kwargs
) -> pd.DataFrame:
    """
    Impute missing values in specified columns.
    
    Args:
        df: Input DataFrame
        columns: Columns to impute (None = all columns)
        method: Imputation method (mean, median, mode, knn, constant)
        **kwargs: Method-specific parameters
        
    Returns:
        DataFrame with imputed values
    """
    result_df = df.copy()
    
    # Select columns to process
    if columns is None:
        columns = result_df.columns.tolist()
    
    # Validate columns exist
    missing_cols = set(columns) - set(result_df.columns)
    if missing_cols:
        raise ValueError(f"Columns not found: {missing_cols}")
    
    # Check missing percentage and warn if high
    for col in columns:
        missing_pct = result_df[col].isna().sum() / len(result_df) * 100
        if missing_pct > 50:
            warnings.warn(
                f"Column '{col}' has {missing_pct:.1f}% missing values"
            )
    
    # Apply imputation based on method
    if method == "mean":
        for col in columns:
            if pd.api.types.is_numeric_dtype(result_df[col]):
                result_df[col].fillna(result_df[col].mean(), inplace=True)
                
    elif method == "median":
        for col in columns:
            if pd.api.types.is_numeric_dtype(result_df[col]):
                result_df[col].fillna(result_df[col].median(), inplace=True)
                
    elif method == "mode":
        for col in columns:
            mode_val = result_df[col].mode()
            if len(mode_val) > 0:
                result_df[col].fillna(mode_val[0], inplace=True)
                
    elif method == "knn":
        # KNN imputation for numeric columns
        n_neighbors = kwargs.get("n_neighbors", 5)
        numeric_cols = [c for c in columns 
                       if pd.api.types.is_numeric_dtype(result_df[c])]
        
        if numeric_cols:
            imputer = KNNImputer(n_neighbors=n_neighbors)
            result_df[numeric_cols] = imputer.fit_transform(
                result_df[numeric_cols]
            )
            
    elif method == "constant":
        fill_value = kwargs.get("fill_value", 0)
        for col in columns:
            result_df[col].fillna(fill_value, inplace=True)
            
    else:
        raise ValueError(f"Unknown imputation method: {method}")
        
    return result_df


# Module interface
process = impute_missing
