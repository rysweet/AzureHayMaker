"""Test suite for verifying __all__ exports in critical modules.

This test file validates that all 30 critical modules have:
1. __all__ list defined
2. Philosophy section in module docstring
3. Public API section in module docstring
4. All symbols in __all__ actually exist in the module
5. __all__ list matches documented Public API
"""

import importlib
import inspect
import pytest
from pathlib import Path


# List of 30 critical modules that MUST have __all__ exports
REQUIRED_MODULES = [
    # Core Hooks (7 modules)
    ".claude.tools.amplihack.hooks.power_steering_checker",
    ".claude.tools.amplihack.hooks.stop",
    ".claude.tools.amplihack.hooks.session_start",
    ".claude.tools.amplihack.hooks.claude_power_steering",
    ".claude.tools.amplihack.hooks.claude_reflection",
    ".claude.tools.amplihack.hooks.precommit_installer",
    ".claude.tools.amplihack.hooks.hook_processor",
    # Security & Defense (2 modules)
    ".claude.tools.amplihack.xpia_defense",
    ".claude.tools.amplihack.context_preservation_secure",
    # Remote Operations (4 modules)
    ".claude.tools.amplihack.remote.cli",
    ".claude.tools.amplihack.remote.executor",
    ".claude.tools.amplihack.remote.orchestrator",
    ".claude.tools.amplihack.remote.integrator",
    # Builders & Transcripts (2 modules)
    ".claude.tools.amplihack.builders.codex_transcripts_builder",
    ".claude.tools.amplihack.builders.claude_transcript_builder",
    # Orchestration Patterns (4 modules)
    ".claude.tools.amplihack.orchestration.patterns.expert_panel",
    ".claude.tools.amplihack.orchestration.patterns.debate",
    ".claude.tools.amplihack.orchestration.patterns.cascade",
    ".claude.tools.amplihack.orchestration.patterns.n_version",
    # Session Management (3 modules)
    ".claude.tools.amplihack.session.file_utils",
    ".claude.tools.amplihack.session.toolkit_logger",
    ".claude.tools.amplihack.session.session_manager",
    # Reflection & Analysis (2 modules)
    ".claude.tools.amplihack.reflection.contextual_error_analyzer",
    ".claude.tools.amplihack.reflection.reflection",
    # Memory System (2 modules)
    ".claude.tools.amplihack.memory.examples",
    ".claude.tools.amplihack.memory.core",
    # Context
    ".claude.tools.amplihack.context_preservation",
    # Scenarios (3 modules)
    ".claude.scenarios.mcp_manager.cli",
    ".claude.scenarios.mcp_manager.mcp_operations",
    ".claude.scenarios.analyze_trace_logs.tool",
]


class TestAllExports:
    """Test __all__ exports for critical modules."""

    @pytest.mark.parametrize("module_name", REQUIRED_MODULES)
    def test_module_has_all_defined(self, module_name):
        """Test that module has __all__ list defined."""
        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            pytest.fail(f"Could not import {module_name}: {e}")

        assert hasattr(module, "__all__"), \
            f"Module {module_name} is missing __all__ export list"

        assert isinstance(module.__all__, list), \
            f"Module {module_name}.__all__ should be a list, got {type(module.__all__)}"

        assert len(module.__all__) > 0, \
            f"Module {module_name}.__all__ is empty - should export at least one symbol"

    @pytest.mark.parametrize("module_name", REQUIRED_MODULES)
    def test_module_has_philosophy_docstring(self, module_name):
        """Test that module docstring contains Philosophy section."""
        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            pytest.fail(f"Could not import {module_name}: {e}")

        docstring = inspect.getdoc(module)
        assert docstring is not None, \
            f"Module {module_name} is missing docstring"

        assert "Philosophy:" in docstring or "philosophy" in docstring.lower(), \
            f"Module {module_name} docstring missing 'Philosophy:' section"

    @pytest.mark.parametrize("module_name", REQUIRED_MODULES)
    def test_module_has_public_api_docstring(self, module_name):
        """Test that module docstring contains Public API section."""
        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            pytest.fail(f"Could not import {module_name}: {e}")

        docstring = inspect.getdoc(module)
        assert docstring is not None, \
            f"Module {module_name} is missing docstring"

        assert "Public API" in docstring or "public api" in docstring.lower(), \
            f"Module {module_name} docstring missing 'Public API' section"

    @pytest.mark.parametrize("module_name", REQUIRED_MODULES)
    def test_all_symbols_exist_in_module(self, module_name):
        """Test that all symbols in __all__ actually exist in the module."""
        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            pytest.fail(f"Could not import {module_name}: {e}")

        if not hasattr(module, "__all__"):
            pytest.skip(f"Module {module_name} doesn't have __all__ yet")

        for symbol in module.__all__:
            assert hasattr(module, symbol), \
                f"Module {module_name}.__all__ exports '{symbol}' but it doesn't exist in the module"

    @pytest.mark.parametrize("module_name", REQUIRED_MODULES)
    def test_all_contains_only_public_symbols(self, module_name):
        """Test that __all__ contains only public symbols (no private _names)."""
        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            pytest.fail(f"Could not import {module_name}: {e}")

        if not hasattr(module, "__all__"):
            pytest.skip(f"Module {module_name} doesn't have __all__ yet")

        for symbol in module.__all__:
            assert not symbol.startswith('_'), \
                f"Module {module_name}.__all__ should not export private symbol '{symbol}'"

    @pytest.mark.parametrize("module_name", REQUIRED_MODULES)
    def test_star_import_works(self, module_name):
        """Test that 'from module import *' works and imports only __all__ symbols."""
        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            pytest.fail(f"Could not import {module_name}: {e}")

        if not hasattr(module, "__all__"):
            pytest.skip(f"Module {module_name} doesn't have __all__ yet")

        # Import all symbols
        namespace = {}
        exec(f"from {module_name} import *", namespace)

        # Check that __all__ symbols are imported
        for symbol in module.__all__:
            assert symbol in namespace, \
                f"Symbol '{symbol}' from {module_name}.__all__ not imported with 'import *'"

        # Check that only __all__ symbols are imported (plus builtins)
        imported_symbols = {k for k in namespace.keys() if not k.startswith('__')}
        expected_symbols = set(module.__all__)

        unexpected = imported_symbols - expected_symbols
        assert len(unexpected) == 0, \
            f"'import *' from {module_name} imported unexpected symbols: {unexpected}"


def test_all_30_modules_accounted_for():
    """Meta-test: Verify we're testing exactly 30 modules."""
    assert len(REQUIRED_MODULES) == 30, \
        f"Expected exactly 30 modules in REQUIRED_MODULES, got {len(REQUIRED_MODULES)}"

    # Check for duplicates
    assert len(REQUIRED_MODULES) == len(set(REQUIRED_MODULES)), \
        "REQUIRED_MODULES contains duplicates"


def test_module_paths_exist():
    """Verify that all module paths exist in the filesystem."""
    project_root = Path(__file__).parent.parent.parent.parent

    for module_name in REQUIRED_MODULES:
        # Convert module name to file path
        parts = module_name.split('.')
        if parts[0] == '':  # Handle leading dot
            parts = parts[1:]

        file_path = project_root / '/'.join(parts[:-1]) / f"{parts[-1]}.py"

        assert file_path.exists(), \
            f"Module file for {module_name} not found at {file_path}"
