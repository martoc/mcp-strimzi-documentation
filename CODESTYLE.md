# Code Style Guide

This document outlines the coding standards and conventions used in this project.

## Language

- Use British English in code, comments, and documentation
- Variable names should use American spelling where it's a Python/programming convention
  (e.g., `color` not `colour` in CSS-related code)

## Python Style

### General

- Follow [PEP 8](https://peps.python.org/pep-0008/) guidelines
- Maximum line length: 120 characters
- Use 4 spaces for indentation (no tabs)

### Type Hints

- All functions must have type hints for parameters and return values
- Use `|` union syntax (Python 3.10+) instead of `Union[]`
- Use `list[T]` instead of `List[T]`

```python
# Good
def search(query: str, limit: int = 10) -> list[SearchResult]:
    ...

# Avoid
def search(query, limit=10):
    ...
```

### Imports

- Standard library imports first
- Third-party imports second
- Local imports third
- Each group separated by a blank line
- Sorted alphabetically within each group

```python
import json
import logging
from pathlib import Path

import frontmatter
from fastmcp import FastMCP

from mcp_strimzi_documentation.database import DocumentDatabase
from mcp_strimzi_documentation.models import Document
```

### Docstrings

- Use Google-style docstrings
- All public modules, classes, and functions must have docstrings
- Include Args, Returns, and Raises sections where applicable

```python
def search(query: str, section: str | None = None) -> list[SearchResult]:
    """Search documents using FTS5.

    Args:
        query: Search query string.
        section: Optional section filter.

    Returns:
        List of SearchResult instances ordered by relevance.
    """
```

### Naming Conventions

- Classes: `PascalCase`
- Functions and variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private methods/attributes: `_leading_underscore`

## Testing

- Use pytest framework
- Test files: `test_<module>.py`
- Test classes: `Test<ClassName>`
- Test functions: `test_<description>`
- Use fixtures for common setup

```python
class TestDocumentDatabase:
    def test_search_returns_results(self, database: DocumentDatabase) -> None:
        """Test that search returns matching results."""
        ...
```

## Error Handling

- Prefer explicit error handling over silent failures
- Use specific exception types
- Log errors appropriately

```python
# Good
try:
    result = perform_operation()
except SpecificError as e:
    logger.error("Operation failed: %s", e)
    raise

# Avoid
try:
    result = perform_operation()
except Exception:
    pass
```

## Logging

- Use the `logging` module
- Use appropriate log levels:
  - `DEBUG`: Detailed information for debugging
  - `INFO`: General operational information
  - `WARNING`: Something unexpected but not an error
  - `ERROR`: A significant problem occurred

```python
logger = logging.getLogger(__name__)

logger.info("Indexing %d documents", count)
logger.debug("Processing file: %s", file_path)
logger.error("Failed to parse: %s", file_path)
```

## Tools

### Linting and Formatting

- **Ruff**: Linting and formatting
- **mypy**: Static type checking

```bash
# Run linter
make lint

# Format code
make format

# Run type checker
make typecheck
```

### Pre-commit

Run `make build` before committing to ensure code quality:

```bash
make build
```

This runs linting, type checking, and tests.
