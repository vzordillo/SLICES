# Contributing to SLICES

## Development Setup

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/vzordillo/SLICES.git
   cd SLICES
   ```

2. **Create conda environment**:
   ```bash
   conda create -n slices python=3.11
   conda activate slices
   ```

3. **Install in development mode**:
   ```bash
   pip install -e ".[dev]"
   ```

## Code Style

- Follow PEP 8 style guide
- Use type hints where possible
- Add docstrings to all public functions/classes
- Keep line length under 100 characters

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src/slices --cov-report=html

# Run specific test category
pytest tests/unit/
pytest tests/integration/
pytest tests/regression/
```

### Writing Tests

- Add tests for new features
- Ensure tests pass before submitting PR
- Aim for ≥80% code coverage

## Pull Request Process

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes and commit**:
   ```bash
   git add .
   git commit -m "Description of changes"
   ```

3. **Run tests**:
   ```bash
   pytest tests/
   ```

4. **Push and create PR**:
   ```bash
   git push origin feature/your-feature-name
   ```

## Code Review Checklist

- [ ] Tests pass
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
- [ ] Changelog updated (if applicable)

## Reporting Issues

When reporting issues, please include:
- Python version
- Operating system
- Error message and traceback
- Minimal reproducible example
- Expected vs actual behavior

