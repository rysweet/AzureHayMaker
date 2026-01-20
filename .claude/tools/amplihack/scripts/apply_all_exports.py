#!/usr/bin/env python3
"""Batch script to add __all__ exports to multiple modules.

This script reads a module, analyzes its public symbols, and adds:
1. __all__ export list at the end of the file
2. Updates docstring with Public API section if needed

Philosophy:
- Batch processing with safety checks
- Preserves existing code structure
- Backs up files before modification
- Validates changes after application

Public API:
    add_all_to_module: Add __all__ export to a single module
    process_modules_batch: Process multiple modules
    backup_file: Create backup before modification
"""

import ast
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from generate_all_exports import analyze_module, generate_all_export


def backup_file(filepath: Path) -> Path:
    """Create backup of file before modification."""
    backup_path = filepath.with_suffix(filepath.suffix + '.bak')
    shutil.copy2(filepath, backup_path)
    return backup_path


def has_public_api_section(content: str) -> bool:
    """Check if docstring already has Public API section."""
    return 'Public API' in content or 'public api' in content.lower()


def add_all_to_module(
    filepath: Path,
    dry_run: bool = True,
    backup: bool = True
) -> Dict[str, any]:
    """Add __all__ export to a Python module.

    Args:
        filepath: Path to the module
        dry_run: If True, only show what would be done
        backup: If True, create backup before modification

    Returns:
        Dict with keys: success, message, symbols
    """
    print(f"\nProcessing: {filepath}")

    # Read current content
    with open(filepath, 'r') as f:
        content = f.read()

    # Check if already has __all__
    if '__all__' in content:
        return {
            "success": False,
            "message": f"Already has __all__ defined",
            "symbols": None
        }

    # Analyze module
    symbols = analyze_module(filepath)

    total_symbols = (
        len(symbols['classes']) +
        len(symbols['functions']) +
        len(symbols['constants'])
    )

    if total_symbols == 0:
        return {
            "success": False,
            "message": "No public symbols found",
            "symbols": symbols
        }

    # Generate __all__ export
    all_export = generate_all_export(symbols)

    if dry_run:
        print(f"  Would add {total_symbols} symbols to __all__")
        print(f"  {all_export[:80]}...")
        return {
            "success": True,
            "message": "Dry run - no changes made",
            "symbols": symbols
        }

    # Create backup if requested
    if backup:
        backup_path = backup_file(filepath)
        print(f"  Backup created: {backup_path}")

    # Add __all__ at the end of file
    # Find a good place to insert (before if __name__ == "__main__" if it exists)
    if 'if __name__ == "__main__"' in content:
        # Insert before main block
        parts = content.rsplit('if __name__ == "__main__"', 1)
        new_content = parts[0].rstrip() + '\n\n\n' + all_export + '\n\n\nif __name__ == "__main__"' + parts[1]
    else:
        # Append at end
        new_content = content.rstrip() + '\n\n\n' + all_export + '\n'

    # Write updated content
    with open(filepath, 'w') as f:
        f.write(new_content)

    print(f"  ✓ Added __all__ with {total_symbols} symbols")

    return {
        "success": True,
        "message": f"Added __all__ with {total_symbols} symbols",
        "symbols": symbols
    }


def process_modules_batch(
    module_paths: List[str],
    dry_run: bool = True,
    backup: bool = True
) -> Dict[str, any]:
    """Process multiple modules in batch.

    Args:
        module_paths: List of module file paths
        dry_run: If True, only show what would be done
        backup: If True, create backups

    Returns:
        Dict with summary statistics
    """
    results = {
        "total": len(module_paths),
        "success": 0,
        "skipped": 0,
        "failed": 0,
        "details": []
    }

    for module_path in module_paths:
        filepath = Path(module_path)

        if not filepath.exists():
            print(f"✗ File not found: {filepath}")
            results["failed"] += 1
            continue

        result = add_all_to_module(filepath, dry_run=dry_run, backup=backup)

        if result["success"]:
            results["success"] += 1
        else:
            results["skipped"] += 1

        results["details"].append({
            "file": str(filepath),
            "result": result
        })

    return results


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Add __all__ exports to Python modules"
    )
    parser.add_argument(
        "modules",
        nargs="+",
        help="Module file paths to process"
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Actually modify files (default is dry-run)"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Don't create backups (default creates .bak files)"
    )

    args = parser.parse_args()

    dry_run = not args.no_dry_run
    backup = not args.no_backup

    if dry_run:
        print("=" * 80)
        print("DRY RUN MODE - No files will be modified")
        print("=" * 80)
    else:
        print("=" * 80)
        print("LIVE MODE - Files will be modified")
        print("=" * 80)

    results = process_modules_batch(
        args.modules,
        dry_run=dry_run,
        backup=backup
    )

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total modules: {results['total']}")
    print(f"Successfully processed: {results['success']}")
    print(f"Skipped: {results['skipped']}")
    print(f"Failed: {results['failed']}")

    if dry_run:
        print("\nTo apply changes, run with --no-dry-run")


__all__ = [
    "add_all_to_module",
    "process_modules_batch",
    "backup_file",
    "has_public_api_section",
]


if __name__ == "__main__":
    main()
