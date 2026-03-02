# Testing Guide

## Overview

This project uses **pytest** for automated testing with proper unit tests, mocks, and fixtures.

## Test Structure

```
spooler/tests/
├── conftest.py          # Shared fixtures and configuration
├── test_utils.py        # Tests for utility functions (mm_to_gram)
├── test_gcode.py        # Tests for G-code parsing and normalization
├── test_spoolman.py     # Tests for spool matching logic
└── test_sdcp.py         # Tests for SDCP message parsing
```

## Running Tests

### Install pytest
```bash
pip install pytest pytest-cov
```

### Run all tests
```bash
pytest
```

### Run specific test file
```bash
pytest spooler/tests/test_gcode.py
```

### Run with coverage report
```bash
pytest --cov=spooler --cov-report=html
```

### Run only fast unit tests
```bash
pytest -m unit
```

### Verbose output
```bash
pytest -v
```

## Test Categories

Tests are marked with categories:
- `@pytest.mark.unit` - Fast unit tests with no external dependencies
- `@pytest.mark.integration` - Integration tests (may require services)
- `@pytest.mark.slow` - Slow-running tests

## Writing New Tests

### Example Test Structure
```python
import pytest
from mymodule import my_function

class TestMyFunction:
    """Tests for my_function."""
    
    def test_basic_case(self):
        """Should handle basic input."""
        result = my_function(10)
        assert result == 20
    
    def test_edge_case(self):
        """Should handle edge case."""
        result = my_function(0)
        assert result == 0
    
    def test_with_fixture(self, mock_spools):
        """Should use fixture data."""
        result = my_function(mock_spools)
        assert len(result) > 0
```

### Using Fixtures

Shared fixtures are in `conftest.py`:
- `temp_dir` - Temporary directory for file tests
- `sample_gcode_file` - Sample G-code file with metadata
- `mock_spools` - Mock Spoolman cache data
- `mock_sdcp_status_message` - Mock SDCP message

## What to Test

### ✅ Unit Test These
- Pure functions (calculations, parsing, transformations)
- Business logic (matching algorithms, normalization)
- Data validation and error handling
- Edge cases and boundary conditions

### ❌ Don't Unit Test These
- External API calls (use mocks/stubs instead)
- Database operations (use integration tests)
- UI rendering (use integration/E2E tests)
- Third-party library internals

## Coverage Goals

Aim for:
- **80%+ coverage** for core business logic (gcode, spoolman, utils)
- **60%+ coverage** for infrastructure code (watchers, listeners)
- **Focus on critical paths** over 100% coverage

## Continuous Testing

Run tests automatically:
```bash
# Watch mode (requires pytest-watch)
ptw

# On every commit (use git hooks)
# Add to .git/hooks/pre-commit:
#!/bin/bash
pytest --tb=short -q
```

## Example Test Output

```
========================= test session starts ==========================
collected 45 items

spooler/tests/test_gcode.py ........                            [ 17%]
spooler/tests/test_sdcp.py ..........                           [ 40%]
spooler/tests/test_spoolman.py ...........                      [ 64%]
spooler/tests/test_utils.py ........                            [100%]

========================= 45 passed in 0.23s ===========================
```
