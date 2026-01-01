# Contributing to Journal Automation

Thank you for your interest in contributing to the Journal Automation project! This document provides guidelines for contributing effectively.

## Getting Started

### Prerequisites

- Python 3.13 or higher
- [uv](https://docs.astral.sh/uv/) for fast dependency management

### First Time Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/journal.git
   cd journal
   ```

2. **Create virtual environment**:
   ```bash
   make venv
   ```

3. **Install dependencies**:
   ```bash
   make sync
   ```

4. **Install pre-commit hook**:
   ```bash
   make install-githook
   ```

## Development Workflow

### Daily Development

Once your virtual environment is activated:

```bash
# Activate the virtual environment (do this once per session)
source .venv/bin/activate

# Run linting
make lint

# Run tests
make pytest

# Run the application
python main.py --help
```

### Making Changes

1. Create a new branch for your feature or fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following the code quality guidelines below.

3. Run the linting and type checking:
   ```bash
   make lint
   ```

4. Run tests:
   ```bash
   make pytest
   ```

5. Commit your changes with a clear message (see [Commit Message Guidelines](#commit-message-guidelines)).

6. Push your branch and create a pull request.

## Code Quality Guidelines

### Type Hints

All code must include type hints following PEP 484. The pre-commit hook will block commits with missing types or the use of `Any` type.

**Good:**
```python
def process_commits(repo_path: str) -> list[dict]:
    """Process git commits and return structured data."""
    # ...
```

**Bad:**
```python
def process_commits(repo_path):
    """Process git commits and return structured data."""
    # ...
```

### Linting

We use [ruff](https://docs.astral.sh/ruff/) for fast Python linting. The configuration is in `pyproject.toml`.

Common issues:
- Line length: 100 characters
- Import ordering: Must follow isort rules
- Documentation: Google-style docstrings required for public functions

### Type Checking

We use [pyright](https://microsoft.github.io/pyright/) for static type checking. The pre-commit hook runs this automatically.

To run manually:
```bash
pyright .
```

### No Type/Linter Ignores

The pre-commit hook will block commits that contain:
- `# type: ignore`
- `# noqa`
- `# ruff: ignore`
- `# pylint: ignore`

If you need to use one of these, you must provide justification in a comment and get approval from a maintainer.

## Commit Message Guidelines

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Changes that do not affect the meaning of the code (white-space, formatting, etc.)
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `perf`: A code change that improves performance
- `test`: Adding missing tests or correcting existing tests
- `chore`: Changes to the build process or auxiliary tools
- `ci`: Changes to CI configuration files

### Examples

```
feat(agents): add fact-checking agent for validation

Implement a new agent that validates generated journal entries
by cross-referencing git commit data.

Closes #123
```

```
fix(orchestrator): handle empty git history gracefully

Previously, the orchestrator would crash when encountering
repos with no commit history. Now it returns early with an
appropriate message.
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=.

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_orchestrator.py
```

### Writing Tests

All new features must include tests. We use pytest for testing.

Tests should be placed in the `tests/` directory and follow the naming convention `test_*.py`.

Example:
```python
def test_process_commits_with_empty_repo():
    """Test that empty repo is handled gracefully."""
    result = process_commits("/tmp/empty-repo")
    assert result == []
```

## Pre-commit Hook

The pre-commit hook runs automatically before each commit and checks:

1. Python syntax compilation
2. Ruff linting
3. Any type usage (blocks `Any` type)
4. Pyright type checking

If any check fails, the commit will be blocked. Fix the issues and try again.

To run the hook manually:
```bash
make githook
```

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the community
- Show empathy towards other community members

## Questions?

If you have questions or need help, please open an issue on GitHub.

Thank you for contributing!
