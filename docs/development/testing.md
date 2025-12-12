# Testing Guide

## Running Tests

```bash
# Run all tests
pytest tests/

# Run unit tests only
pytest tests/unit/

# Run with coverage
pytest tests/ --cov=src/slices --cov-report=html
```

## Test Structure

- `tests/unit/`: Unit tests for individual components
- `tests/integration/`: Integration tests for workflows
- `tests/regression/`: Regression tests to prevent breaking changes

## Writing Tests

See existing test files for examples. Use pytest fixtures from `conftest.py`.

