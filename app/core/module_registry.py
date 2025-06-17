"""Module registry for dynamic loading of cleaning modules."""

import importlib
import os
from pathlib import Path
from typing import Dict, Callable, Optional


class ModuleRegistry:
    """Registry for data cleaning modules."""
    
    def __init__(self):
        self.modules: Dict[str, Callable] = {}
        self._scan_modules()
        
    def _scan_modules(self):
        """Scan and register built-in modules and plugins."""
        # Scan built-in modules
        modules_path = Path(__file__).parent.parent.parent / "modules"
        self._scan_directory(modules_path, "modules")
        
        # Scan plugins
        plugins_path = Path(__file__).parent.parent.parent / "plugins"
        if plugins_path.exists():
            self._scan_directory(plugins_path, "plugins")
            
    def _scan_directory(self, path: Path, package_prefix: str):
        """Scan a directory for modules."""
        for item in path.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                module_name = item.name
                try:
                    # Import the module
                    module = importlib.import_module(
                        f"{package_prefix}.{module_name}"
                    )
                    
                    # Register if it has the required interface
                    if hasattr(module, "process"):
                        self.modules[module_name] = module.process
                        
                except ImportError as e:
                    print(f"Failed to import {module_name}: {e}")
                    
    def get_module(self, name: str) -> Optional[Callable]:
        """Get a registered module by name."""
        return self.modules.get(name)
        
    def list_modules(self) -> Dict[str, Callable]:
        """List all registered modules."""
        return self.modules.copy()
