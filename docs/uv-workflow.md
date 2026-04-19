# UV Workflow Guide

## What is UV?

[UV](https://github.com/astral-sh/uv) is an extremely fast Python package installer and resolver, written in Rust. It's a modern replacement for pip and pip-tools.

## Key Features

- **Fast**: 10-100x faster than pip
- **Compatible**: Works with existing pyproject.toml and requirements.txt files
- **Reliable**: Better dependency resolution
- **Convenient**: Single binary, no Python installation required to run

## Installation

### With asdf (Recommended)

```bash
# Install uv plugin
asdf plugin add uv

# Install uv
asdf install uv latest

# Reshim
asdf reshim uv

# Verify
uv --version
```

### With pip

```bash
pip install uv
```

### Standalone Binary

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Common Commands

### Project Setup

```bash
# Initialize new project
uv init

# Sync dependencies (install from pyproject.toml)
uv sync

# Sync with specific Python version
uv sync --python 3.13

# Sync with frozen lockfile
uv sync --frozen
```

### Running Code

```bash
# Run with virtualenv
uv run python -m cli.main

# Run module
uv run python -m cli.main

# Run any command in virtualenv
uv run pytest
```

### Dependency Management

```bash
# Add dependency
uv add requests

# Add with version constraint
uv add "requests>=2.0.0,<3.0.0"

# Add dev dependency
uv add --dev pytest

# Add optional dependency
uv add --optional cli typer

# Remove dependency
uv remove requests

# List dependencies
uv pip list
```

### Virtual Environment

```bash
# Create virtualenv
uv venv

# Create with specific Python
uv venv --python 3.13

# Activate (bash/zsh)
source .venv/bin/activate

# Activate (fish)
source .venv/bin/activate.fish

# Deactivate
deactivate
```

### Locking

```bash
# Generate lockfile
uv lock

# Lock with specific Python version
uv lock --python 3.13

# Update lockfile
uv lock --upgrade

# Update specific package
uv lock --upgrade-package requests
```

## Best Practices

### Use uv sync, not pip install

```bash
# Good
uv sync

# Avoid
pip install -r requirements.txt
```

### Use uv run for execution

```bash
# Good - uses project virtualenv
uv run python -m cli.main

# Avoid - requires manual venv activation
python main.py
```

### Keep lockfile updated

```bash
# When adding dependencies
uv add requests

# Lockfile automatically updated
git add uv.lock
git commit -m "add requests dependency"
```

### Use frozen installs in CI/CD

```bash
# CI/CD should use frozen lockfile
uv sync --frozen
```

## Troubleshooting

### Dependencies Not Found

```bash
# Clear cache
uv cache clean

# Re-sync
uv sync --reinstall
```

### Python Version Issues

```bash
# Find Python versions
uv python list

# Install specific Python version
uv python install 3.13.5

# Set default Python
uv python set 3.13.5
```

### Lockfile Conflicts

```bash
# Regenerate lockfile
rm uv.lock
uv lock

# Or with specific resolution
uv lock --resolution=lowest-direct
```

## Integration with Other Tools

### Ruff (Linting/Formatting)

```bash
# Use uv to install ruff
uv tool install ruff

# Run ruff with uv
uv run ruff check .
uv run ruff format .
```

### Pytest (Testing)

```bash
# Run tests
uv run pytest

# With coverage
uv run pytest --cov=agents --cov=dataflows --cov=graph --cov=llm_clients --cov=radon

# Specific test
uv run pytest tests/test_file.py
```

### VS Code Integration

1. Install Python extension
2. Select virtualenv: `.venv`
3. Use `uv run` commands in terminal

## Migration from pip/conda

### From pip

```bash
# Install uv
pip install uv

# Convert requirements.txt to pyproject.toml (optional)
uv pip compile requirements.txt -o pyproject.toml

# Sync
uv sync
```

### From conda

```bash
# Install uv
conda install -c conda-forge uv

# Export conda environment (optional)
conda env export > environment.yml

# Rebuild with uv
uv sync
```

## Performance Tips

1. **Use `--frozen`** in CI/CD for faster installs
2. **Cache `uv.lock`** for faster rebuilds
3. **Parallel installs**: uv automatically parallelizes downloads
4. **Avoid `uv pip install`**: use `uv add` instead

## Resources

- [UV Documentation](https://github.com/astral-sh/uv)
- [UV CLI Reference](https://github.com/astral-sh/uv/blob/main/README.md)
- [Pyproject.toml Specification](https://packaging.python.org/specifications/pyproject-toml/)

## Common Workflows

### Daily Development

```bash
# Pull latest
git pull

# Sync dependencies
uv sync

# Run linting
uv run ruff check .

# Format code
uv run ruff format .

# Run tests
uv run pytest

# Run application
uv run python -m cli.main
```

### Adding a Feature

```bash
# Create branch
git checkout -b feature/new-feature

# Add dependency if needed
uv add new-package

# Write code

# Run linting
uv run ruff check .

# Format code
uv run ruff format .

# Run tests
uv run pytest

# Commit
git add .
git commit -m "feat: add new feature"
```

### Updating Dependencies

```bash
# Update lockfile
uv lock --upgrade

# Review changes
git diff uv.lock

# Sync
uv sync

# Test everything
uv run pytest
```

## FAQ

**Q: Do I still need pip?**
A: Generally no. uv handles all package installation. Use `uv pip install` only for legacy compatibility.

**Q: How do I manage multiple Python versions?**
A: Use `uv python install` to install additional versions, then use `uv sync --python X.Y.Z` to select version.

**Q: Can I use uv with existing conda environments?**
A: Yes, but uv creates its own virtualenvs. Best to migrate fully to uv for consistency.

**Q: How does uv resolve dependencies?**
A: Uses modern dependency resolution algorithm that's faster and more accurate than pip's.

**Q: What if uv.lock has merge conflicts?**
A: Regenerate with `uv lock` after resolving conflicts in pyproject.toml.
