"""Core orchestrator for running the data cleaning pipeline."""

import pandas as pd
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass
import logging
import traceback
import json # For serializing details for audit log

from app.core.audit_logger import (
    log_audit_event,
    ACTION_PIPELINE_EXECUTION_START,
    ACTION_PIPELINE_EXECUTION_END
)


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
        steps: List[ModuleConfig],
        current_user: Optional[dict] = None # Add current_user parameter
    ) -> Tuple[pd.DataFrame, Report]:
        """
        Execute the cleaning pipeline on the dataframe.
        
        Args:
            df: Input dataframe
            steps: List of module configurations to execute
            current_user: Optional dictionary with user details for audit logging
            
        Returns:
            Tuple of (cleaned_dataframe, execution_report)
        """
        user_id = current_user['id'] if current_user else None
        username = current_user['username'] if current_user else "System" # Default to "System" if no user

        # Prepare details for audit log (simplified representation of steps)
        pipeline_config_summary = [{"module": s.name, "params": list(s.params.keys())} for s in steps if s.enabled]

        log_audit_event(
            action_type=ACTION_PIPELINE_EXECUTION_START,
            outcome="INFO", # Or "ATTEMPT"
            user_id=user_id,
            username=username,
            details={"pipeline_configuration": pipeline_config_summary, "input_rows": len(df)}
        )

        result_df = df.copy()
        completed_steps = []
        errors = []
        stats = {}
        
        for step in steps:
            if not step.enabled:
                continue
                
            try:
                self.logger.info(f"Executing {step.name} for user {username}")
                
                # Execute module function, passing current_user
                # This requires plugin functions to accept current_user=None by default
                result_df = step.module_func(result_df, current_user=current_user, **step.params)
                
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

        pipeline_outcome = 'SUCCESS' if not errors else 'FAILURE'
        log_audit_event(
            action_type=ACTION_PIPELINE_EXECUTION_END,
            outcome=pipeline_outcome,
            user_id=user_id,
            username=username,
            details={
                "steps_completed": report.steps_completed,
                "errors_count": len(report.errors),
                "output_rows": len(result_df)
            }
        )
        
        return result_df, report
