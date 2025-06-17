#!/usr/bin/env python3
"""Setup script for SheetPilot."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="sheetpilot",
    version="1.0.0",
    author="SheetPilot Team",
    description="Desktop AI spreadsheet assistant for automated data cleaning",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/SheetPilot",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/SheetPilot/issues",
        "Documentation": "https://github.com/yourusername/SheetPilot/wiki",
        "Source Code": "https://github.com/yourusername/SheetPilot",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Office/Business :: Financial :: Spreadsheet",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(exclude=["tests", "tests.*", "docs", "docs.*"]),
    python_requires=">=3.8",
    install_requires=[
        "pandas>=1.3.0",
        "numpy>=1.21.0",
        "scikit-learn>=1.0.0",
        "lightgbm>=3.3.0",
        "PyQt5>=5.15.0",
        "nltk>=3.7",
        "openpyxl>=3.0.9",
        "click>=8.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-qt>=4.2.0",
            "pytest-cov>=3.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "sheetpilot=app.__main__:main",
            "sheetpilot-cli=cli.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt", "*.json"],
    },
    zip_safe=False,
)
