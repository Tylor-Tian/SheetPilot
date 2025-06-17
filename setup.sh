#!/bin/bash

# Setup script for SheetPilot project
# Run this from inside your cloned SheetPilot directory

echo "Setting up SheetPilot project structure..."

# Create directory structure
mkdir -p app/{gui,core}
mkdir -p modules/{file_parser,missing_imputer,text_normalizer,outlier_detector}
mkdir -p {plugins,cli,tests,docs}

# Create all __init__.py files
find . -type d -name "app" -o -name "gui" -o -name "core" -o -name "modules" -o -name "file_parser" -o -name "missing_imputer" -o -name "text_normalizer" -o -name "outlier_detector" -o -name "plugins" -o -name "cli" -o -name "tests" | while read dir; do
    touch "$dir/__init__.py"
done

# Create main files
touch app/__main__.py
touch app/gui/{main_window,import_window,config_window,report_window}.py
touch app/core/{orchestrator,module_registry}.py
touch modules/file_parser/parser.py
touch modules/missing_imputer/imputer.py
touch modules/text_normalizer/normalizer.py
touch modules/outlier_detector/detector.py
touch plugins/README.md
touch cli/cli.py
touch tests/{test_file_parser,test_missing_imputer,test_text_normalizer,test_outlier_detector,test_integration}.py
touch {pyproject.toml,setup.py}
touch docs/README.md

echo "✓ SheetPilot structure created!"
echo ""
echo "Project structure:"
tree -L 3 -I '__pycache__|*.pyc|.git' || find . -type d -not -path '*/\.*' | head -20

echo ""
echo "Next: Copy the code from the PR into each file"
