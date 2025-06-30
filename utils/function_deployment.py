"""
Azure Function Deployment Utilities

This module provides utilities for packaging and deploying Azure Functions,
including ZIP file creation and deployment helpers.
"""

import zipfile
from pathlib import Path
from typing import Optional


def zip_function_folder(func_dir: Path, zip_path: Path) -> None:
    """
    Zip up the contents of a function directory into a ZIP file for deployment.
    
    Ensures all files are stored relative to func_dir (so host.json is at root).
    
    Args:
        func_dir: Path to the function directory to zip
        zip_path: Path where the ZIP file should be created
        
    Raises:
        FileNotFoundError: If func_dir doesn't exist
        PermissionError: If unable to create ZIP file
    """
    if not func_dir.exists():
        raise FileNotFoundError(f"Function directory not found: {func_dir}")
    
    if not func_dir.is_dir():
        raise ValueError(f"Path is not a directory: {func_dir}")
    
    # Ensure parent directory exists for zip_path
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in func_dir.rglob("*"):
            if file_path.is_file():
                # Store files relative to func_dir to maintain proper structure
                relative_path = file_path.relative_to(func_dir)
                zf.write(file_path, relative_path)


def validate_function_structure(func_dir: Path) -> tuple[bool, list[str]]:
    """
    Validate that a directory contains a proper Azure Function structure.
    
    Args:
        func_dir: Path to the function directory to validate
        
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    if not func_dir.exists():
        return False, ["Function directory does not exist"]
    
    if not func_dir.is_dir():
        return False, ["Path is not a directory"]
    
    # Check for required files
    host_json = func_dir / "host.json"
    if not host_json.exists():
        issues.append("Missing host.json file")
    
    requirements_txt = func_dir / "requirements.txt"
    if not requirements_txt.exists():
        issues.append("Missing requirements.txt file")
    
    # Check for at least one function folder
    function_folders = [
        item for item in func_dir.iterdir() 
        if item.is_dir() and (item / "function.json").exists()
    ]
    
    if not function_folders:
        issues.append("No function folders found (folders with function.json)")
    
    return len(issues) == 0, issues


def get_function_info(func_dir: Path) -> dict:
    """
    Get information about an Azure Function directory.
    
    Args:
        func_dir: Path to the function directory
        
    Returns:
        Dictionary with function information
    """
    info = {
        "path": str(func_dir),
        "exists": func_dir.exists(),
        "functions": [],
        "files": [],
        "size": 0
    }
    
    if not func_dir.exists():
        return info
    
    # Get list of function folders
    for item in func_dir.iterdir():
        if item.is_dir() and (item / "function.json").exists():
            info["functions"].append(item.name)
    
    # Get list of all files and calculate total size
    for file_path in func_dir.rglob("*"):
        if file_path.is_file():
            info["files"].append(str(file_path.relative_to(func_dir)))
            info["size"] += file_path.stat().st_size
    
    return info
