# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a recruitment task project. The main Python application is in `main.py`.

## Development Commands

### Running the application
```bash
python main.py
```

### Testing (once tests are added)
```bash
# Run all tests
python -m pytest

# Run a specific test
python -m pytest tests/test_file.py::test_name -v
```

### Linting and formatting (once tools are configured)
```bash
# Run linter
pylint main.py

# Format code
black main.py
```

## Code Structure

The project is currently in early stages with the main implementation in `main.py`. As the task develops, organize code into:
- `main.py` — entry point and core logic
- `tests/` — test files (follow pytest conventions)
- Additional modules as needed

## Common Development Patterns

When implementing the recruitment task:
1. Keep logic modular and testable
2. Use descriptive variable and function names
3. Add docstrings to public functions
4. Write tests alongside features
