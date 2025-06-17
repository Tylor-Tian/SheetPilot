"""Core orchestrator for running the data cleaning pipeline."""

import pandas as pd
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass
import logging
import traceback


@dataclass
class ModuleConfig:
    """Configuration for a module in the pipeline."""
    name: str
    module_func: callable
    params: Dict[str, Any]
    enabled: bool = True


@dataclass
class Report:
    """Pipeline execution report."""
    steps_completed: List[str]
    errors: List[Dict[str, str]]
    stats: Dict[str, Any]


class Orchestrator:
    """Manages the data cleaning pipeline execution."""
    
    def __init__(self, stop_on_error: bool = False):
        self.stop_on_error = stop_on_error
        self.logger = logging.getLogger(__name__)
        
    def run_pipeline(
        self, 
        df: pd.DataFrame, 
        steps: List[ModuleConfig]
    ) -> Tuple[pd.DataFrame, Report]:
        """
        Execute the cleaning pipeline on the dataframe.
        
        Args:
            df: Input dataframe
            steps: List of module configurations to execute
            
        Returns:
            Tuple of (cleaned_dataframe, execution_report)
        """
        result_df = df.copy()
        completed_steps = []
        errors = []
        stats = {}
        
        for step in steps:
            if not step.enabled:
                continue
                
            try:
                self.logger.info(f"Executing {step.name}")
                
                # Execute module function
                result_df = step.module_func(result_df, **step.params)
                
                completed_steps.append(step.name)
                stats[step.name] = {"status": "success"}
                
            except Exception as e:
                error_info = {
                    "module": step.name,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }
                errors.append(error_info)
                self.logger.error(f"Error in {step.name}: {e}")
                
                if self.stop_on_error:
                    break
                    
        report = Report(
            steps_completed=completed_steps,
            errors=errors,
            stats=stats
        )
        
        return result_df, report
