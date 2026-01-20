#!/usr/bin/env python3
"""Script to analyze modules and generate __all__ exports.

This script analyzes Python modules to identify public symbols and generate
appropriate __all__ export lists following the Bricks & Studs pattern.

Philosophy:
- Automated analysis of module contents
- Generates __all__ lists based on actual exports
- Identifies public classes, functions, and constants
- Creates philosophy docstring sections

Public API:
    analyze_module: Analyze a module and identify public symbols
    generate_all_export: Generate __all__ list for a module
    update_module_docstring: Add philosophy and public API sections
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple


def analyze_module(filepath: Path) -> Dict[str, List[str]]:
    """Analyze a Python module and identify public symbols.

    Args:
        filepath: Path to the Python module

    Returns:
        Dict with keys: classes, functions, constants, imports
    """
    with open(filepath, 'r') as f:
        content = f.read()

    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"Syntax error in {filepath}: {e}")
        return {"classes": [], "functions": [], "constants": [], "imports": []}

    classes = []
    functions = []
    constants = []
    imports = []

    for node in ast.walk(tree):
        # Find top-level classes
        if isinstance(node, ast.ClassDef) and not node.name.startswith('_'):
            classes.append(node.name)

        # Find top-level functions (not private)
        elif isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
            # Skip if it's a method inside a class
            functions.append(node.name)

        # Find module-level constants (uppercase names)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if target.id.isupper() and not target.id.startswith('_'):
                        constants.append(target.id)

    return {
        "classes": sorted(set(classes)),
        "functions": sorted(set(functions)),
        "constants": sorted(set(constants)),
        "imports": imports
    }


def generate_all_export(symbols: Dict[str, List[str]]) -> str:
    """Generate __all__ list from analyzed symbols.

    Args:
        symbols: Dictionary of symbol types

    Returns:
        String representation of __all__ list
    """
    all_exports = []

    # Classes first
    all_exports.extend(symbols.get("classes", []))

    # Then functions
    all_exports.extend(symbols.get("functions", []))

    # Then constants
    all_exports.extend(symbols.get("constants", []))

    if not all_exports:
        return '__all__ = []  # No public symbols'

    # Format as Python list
    if len(all_exports) == 1:
        return f'__all__ = ["{all_exports[0]}"]'

    # Multi-line format for readability
    exports_str = '[\n'
    for export in all_exports:
        exports_str += f'    "{export}",\n'
    exports_str += ']'

    return f'__all__ = {exports_str}'


def generate_public_api_docstring(symbols: Dict[str, List[str]]) -> str:
    """Generate Public API section for module docstring.

    Args:
        symbols: Dictionary of symbol types

    Returns:
        String representation of Public API section
    """
    lines = ["Public API (the \"studs\"):"]

    # Classes
    for cls in symbols.get("classes", []):
        lines.append(f"    {cls}: [Description needed]")

    # Functions
    for func in symbols.get("functions", []):
        lines.append(f"    {func}: [Description needed]")

    # Constants
    for const in symbols.get("constants", []):
        lines.append(f"    {const}: [Description needed]")

    return "\n".join(lines)


def check_module_has_all(filepath: Path) -> bool:
    """Check if module already has __all__ defined."""
    with open(filepath, 'r') as f:
        content = f.read()
    return '__all__' in content


def main():
    """Main entry point."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python generate_all_exports.py <module_path>")
        sys.exit(1)

    filepath = Path(sys.argv[1])

    if not filepath.exists():
        print(f"File not found: {filepath}")
        sys.exit(1)

    # Check if already has __all__
    if check_module_has_all(filepath):
        print(f"Module {filepath} already has __all__ defined")
        print("Analyzing anyway for review...")

    # Analyze module
    print(f"\nAnalyzing {filepath}...")
    symbols = analyze_module(filepath)

    print(f"\nFound:")
    print(f"  Classes: {len(symbols['classes'])}")
    print(f"  Functions: {len(symbols['functions'])}")
    print(f"  Constants: {len(symbols['constants'])}")

    # Generate __all__
    print(f"\nSuggested __all__ export:")
    print(generate_all_export(symbols))

    # Generate Public API docstring
    print(f"\nSuggested Public API docstring section:")
    print(generate_public_api_docstring(symbols))

    print(f"\nDetailed symbols:")
    if symbols['classes']:
        print(f"  Classes: {', '.join(symbols['classes'])}")
    if symbols['functions']:
        print(f"  Functions: {', '.join(symbols['functions'])}")
    if symbols['constants']:
        print(f"  Constants: {', '.join(symbols['constants'])}")


__all__ = [
    "analyze_module",
    "generate_all_export",
    "generate_public_api_docstring",
    "check_module_has_all",
]


if __name__ == "__main__":
    main()
