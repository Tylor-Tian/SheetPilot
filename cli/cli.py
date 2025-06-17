"""Command-line interface for SheetPilot."""

import click
import pandas as pd
import json
from pathlib import Path

from app.core.orchestrator import Orchestrator, ModuleConfig
from modules.file_parser import parse_file
from modules.missing_imputer import impute_missing
from modules.text_normalizer import normalize_text
from modules.outlier_detector import detect_outliers


@click.command()
@click.option('--input', '-i', required=True, help='Input file path')
@click.option('--format', '-f', help='File format (auto-detected if not specified)')
@click.option('--output', '-o', required=True, help='Output file path')
@click.option('--impute', help='Imputation config: "columns=A,B method=mean"')
@click.option('--normalize', help='Normalization config: "columns=X,Y lowercase=true"')
@click.option('--outlier', help='Outlier config: "columns=P,Q method=iqr threshold=1.5"')
@click.option('--config', '-c', help='JSON config file path')
def main(input, format, output, impute, normalize, outlier, config):
    """SheetPilot CLI - Clean your data from the command line."""
    
    click.echo("SheetPilot CLI")
    click.echo("=" * 50)
    
    # Load data
    click.echo(f"Loading data from {input}...")
    try:
        df = parse_file(input, file_format=format)
        click.echo(f"Loaded {len(df)} rows, {len(df.columns)} columns")
    except Exception as e:
        click.echo(f"Error loading file: {e}", err=True)
        return
    
    # Build pipeline steps
    steps = []
    
    if config:
        # Load from config file
        with open(config, 'r') as f:
            config_data = json.load(f)
            steps = build_steps_from_config(config_data)
    else:
        # Build from command line options
        if impute:
            params = parse_params(impute)
            steps.append(ModuleConfig(
                name="missing_imputer",
                module_func=impute_missing,
                params=params
            ))
            
        if normalize:
            params = parse_params(normalize)
            steps.append(ModuleConfig(
                name="text_normalizer",
                module_func=normalize_text,
                params=params
            ))
            
        if outlier:
            params = parse_params(outlier)
            steps.append(ModuleConfig(
                name="outlier_detector",
                module_func=detect_outliers,
                params=params
            ))
    
    if not steps:
        click.echo("No cleaning operations specified", err=True)
        return
    
    # Run pipeline
    click.echo("\nRunning cleaning pipeline...")
    orchestrator = Orchestrator()
    
    try:
        cleaned_df, report = orchestrator.run_pipeline(df, steps)
        
        # Show report
        click.echo("\n=== Cleaning Report ===")
        click.echo(f"Steps completed: {', '.join(report.steps_completed)}")
        
        if report.errors:
            click.echo(f"\nErrors: {len(report.errors)}")
            for error in report.errors:
                click.echo(f"  - {error['module']}: {error['error']}")
        
        # Save output
        click.echo(f"\nSaving cleaned data to {output}...")
        if output.endswith('.xlsx'):
            cleaned_df.to_excel(output, index=False)
        else:
            cleaned_df.to_csv(output, index=False)
            
        click.echo(f"✓ Saved {len(cleaned_df)} rows")
        
    except Exception as e:
        click.echo(f"Pipeline error: {e}", err=True)


def parse_params(param_string):
    """Parse parameter string into dictionary."""
    params = {}
    
    for pair in param_string.split():
        if '=' in pair:
            key, value = pair.split('=', 1)
            
            # Handle lists
            if ',' in value:
                value = value.split(',')
            # Handle booleans
            elif value.lower() in ('true', 'false'):
                value = value.lower() == 'true'
            # Try to convert numbers
            else:
                try:
                    if '.' in value:
                        value = float(value)
                    else:
                        value = int(value)
                except ValueError:
                    pass
                    
            params[key] = value
            
    return params


def build_steps_from_config(config_data):
    """Build module steps from JSON config."""
    steps = []
    
    module_map = {
        "missing_imputer": impute_missing,
        "text_normalizer": normalize_text,
        "outlier_detector": detect_outliers
    }
    
    for step_config in config_data.get('steps', []):
        module_name = step_config.get('module')
        if module_name in module_map:
            steps.append(ModuleConfig(
                name=module_name,
                module_func=module_map[module_name],
                params=step_config.get('params', {})
            ))
            
    return steps


if __name__ == '__main__':
    main()
