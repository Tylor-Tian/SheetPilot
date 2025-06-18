"""File parser module for loading various data formats."""

import pandas as pd
from pathlib import Path
from typing import Optional


def parse_file(
    path: str, 
    file_format: Optional[str] = None,
    current_user: Optional[dict] = None, # Added for orchestrator compatibility
    **kwargs
) -> pd.DataFrame:
    """
    Parse a file into a pandas DataFrame.
    'current_user' is accepted for compatibility but not used by this module.
    
    Args:
        path: Path to the file
        file_format: File format (auto-detected if None)
        **kwargs: Additional arguments passed to pandas read functions
        
    Returns:
        Parsed DataFrame
        
    Raises:
        ValueError: If file format is unsupported
        FileNotFoundError: If file doesn't exist
    """
    file_path = Path(path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")
        
    # Auto-detect format from extension
    if file_format is None:
        file_format = file_path.suffix.lower().lstrip(".")
        
    # Map common variations
    format_map = {
        "csv": "csv",
        "tsv": "tsv",
        "txt": "csv",  # Assume CSV for .txt
        "json": "json",
        "xls": "excel",
        "xlsx": "excel",
        "xlsm": "excel",
        "ods": "excel"
    }
    
    format_key = format_map.get(file_format, file_format)
    
    try:
        if format_key == "csv":
            return pd.read_csv(path, **kwargs)
        elif format_key == "tsv":
            return pd.read_csv(path, sep="\t", **kwargs)
        elif format_key == "json":
            return pd.read_json(path, **kwargs)
        elif format_key == "excel":
            return pd.read_excel(path, **kwargs)
        else:
            raise ValueError(f"Unsupported file format: {file_format}")
            
    except Exception as e:
        raise ValueError(f"Error parsing file: {e}")


# Module interface
process = parse_file
