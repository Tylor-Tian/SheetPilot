# SheetPilot Plugin Development Guide

## Overview

Plugins extend SheetPilot with custom data cleaning modules. This guide explains how to create and install plugins.

## Plugin Structure

Each plugin must be a Python package (directory with `__init__.py`) containing a `process` function:

```python
# plugins/my_plugin/__init__.py

import pandas as pd

def process(df: pd.DataFrame, **params) -> pd.DataFrame:
    """
    Process the dataframe.
    
    Args:
        df: Input DataFrame
        **params: Plugin-specific parameters
        
    Returns:
        Processed DataFrame
    """
    # Your processing logic here
    result_df = df.copy()
    
    # Example: Add a new column
    if "new_column_name" in params:
        result_df[params["new_column_name"]] = "processed"
    
    return result_df
