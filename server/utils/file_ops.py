"""
File Operations Utilities
Helper functions for JSON file loading and saving
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List


# Unified data directory path
DATA_DIR = Path(__file__).parent.parent / "data"


def load_json(path: str) -> Any:
    """Load JSON file, return empty dict/list if not found or invalid"""
    path_obj = Path(path) if not isinstance(path, Path) else path
    
    if not path_obj.exists():
        # Return appropriate default based on file name pattern
        if path_obj.name.endswith(".json"):
            # If it's a contexts file, return dict; otherwise list
            if "context" in path_obj.name.lower():
                return {}
            return []
        return {}
    
    try:
        with open(path_obj, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_json(path: str, data: Any):
    """Save data to JSON file with proper formatting"""
    path_obj = Path(path) if not isinstance(path, Path) else path
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path_obj, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def append_json(path: str, obj: Dict[str, Any]):
    """Append object to JSON array file"""
    path_obj = Path(path) if not isinstance(path, Path) else path
    arr = load_json(path_obj)
    
    if not isinstance(arr, list):
        arr = []
    
    arr.append(obj)
    save_json(path_obj, arr)

