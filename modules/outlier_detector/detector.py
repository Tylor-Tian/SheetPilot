"""Outlier detection module."""

import pandas as pd
import numpy as np
from typing import List, Optional
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
import warnings


def detect_outliers(
    df: pd.DataFrame,
    columns: List[str],
    method: str = "iqr",
    threshold: Optional[float] = None,
    action: str = "remove",
    **kwargs
) -> pd.DataFrame:
    """
    Detect and handle outliers in numeric columns.
    
    Args:
        df: Input DataFrame
        columns: Numeric columns to check
        method: Detection method (iqr, zscore, isolation, lof)
        threshold: Method-specific threshold
        action: What to do with outliers (remove, flag)
        **kwargs: Method-specific parameters
        
    Returns:
        DataFrame with outliers handled
    """
    result_df = df.copy()
    
    # Validate columns
    missing_cols = set(columns) - set(result_df.columns)
    if missing_cols:
        raise ValueError(f"Columns not found: {missing_cols}")
    
    # Validate numeric columns
    for col in columns:
        if not pd.api.types.is_numeric_dtype(result_df[col]):
            raise ValueError(f"Column '{col}' is not numeric")
    
    # Skip zero variance columns
    valid_columns = []
    for col in columns:
        if result_df[col].std() == 0:
            warnings.warn(f"Column '{col}' has zero variance, skipping")
        else:
            valid_columns.append(col)
    
    if not valid_columns:
        return result_df
    
    # Initialize outlier mask
    outlier_mask = pd.Series(False, index=result_df.index)
    
    # Apply detection method
    if method == "iqr":
        threshold = threshold or 1.5
        for col in valid_columns:
            Q1 = result_df[col].quantile(0.25)
            Q3 = result_df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - threshold * IQR
            upper_bound = Q3 + threshold * IQR
            
            col_outliers = (result_df[col] < lower_bound) | \
                          (result_df[col] > upper_bound)
            outlier_mask = outlier_mask | col_outliers
            
    elif method == "zscore":
        threshold = threshold or 3
        for col in valid_columns:
            z_scores = np.abs(
                (result_df[col] - result_df[col].mean()) / 
                result_df[col].std()
            )
            col_outliers = z_scores > threshold
            outlier_mask = outlier_mask | col_outliers
            
    elif method == "isolation":
        contamination = kwargs.get("contamination", 0.1)
        iso_forest = IsolationForest(
            contamination=contamination,
            random_state=42
        )
        
        # Fit on valid columns
        X = result_df[valid_columns].values
        outlier_labels = iso_forest.fit_predict(X)
        outlier_mask = outlier_labels == -1
        
    elif method == "lof":
        n_neighbors = kwargs.get("n_neighbors", 20)
        contamination = kwargs.get("contamination", 0.1)
        
        lof = LocalOutlierFactor(
            n_neighbors=n_neighbors,
            contamination=contamination
        )
        
        X = result_df[valid_columns].values
        outlier_labels = lof.fit_predict(X)
        outlier_mask = outlier_labels == -1
        
    else:
        raise ValueError(f"Unknown outlier detection method: {method}")
    
    # Handle outliers based on action
    if action == "remove":
        result_df = result_df[~outlier_mask]
    elif action == "flag":
        result_df["is_outlier"] = outlier_mask
    else:
        raise ValueError(f"Unknown action: {action}")
    
    return result_df


# Module interface
process = detect_outliers
