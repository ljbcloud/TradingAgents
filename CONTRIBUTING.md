# Contributing to TradingAgents

Thank you for your interest in contributing to TradingAgents! We welcome contributions from the community.

## Development Setup

### Prerequisites

**Required tools:**
- Python 3.10 or higher
- uv (>= 0.9.25)
- ruff (>= 0.15.5)
- asdf (for tool version management)

**Install tools with asdf:**
```bash
asdf install
asdf reshim python
```

**Or install manually:**
```bash
# Install uv
pip install uv

# Install ruff
pip install ruff
```

### Setup

1. Fork and clone the repository
2. Create a feature branch
3. Install dependencies

```bash
git clone https://github.com/YOUR_USERNAME/TradingAgents.git
cd TradingAgents
git checkout -b feature/your-feature
uv sync
```

4. Set up environment variables

```bash
cp .env.example .env
# Edit .env with your API keys
```

## Development Workflow

### Common Commands

**Install dependencies:**
```bash
uv sync
```

**Run with virtualenv:**
```bash
uv run python main.py
uv run python -m cli.main
```

**Add/remove dependencies:**
```bash
uv add <package>
uv remove <package>
```

**Lint code:**
```bash
ruff check .
ruff check --fix .
```

**Format code:**
```bash
ruff format .
ruff format --check .  # Check without formatting
```

**Run both:**
```bash
ruff check . && ruff format .
```

### Code Quality

All code must pass linting and formatting checks before being merged:

```bash
ruff check . && ruff format .
```

CI/CD automatically runs these checks on all pull requests.

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test
uv run pytest tests/test_file.py

# Run with coverage
uv run pytest --cov=tradingagents
```

### Manual Testing

**TUI mode:**
```bash
uv run python -m cli.main
```

**Web mode:**
```bash
uv run chainlit run cli/web.py
```

## Pull Request Process

1. Update documentation if needed
2. Add tests for new features
3. Run linting and formatting
4. Ensure all tests pass
5. Commit with clear messages
6. Push and create a pull request

### Commit Messages

Use clear, descriptive commit messages:

```
feat: add new feature description
fix: resolve specific issue
docs: update documentation
chore: update tooling or configuration
test: add or update tests
```

### Pull Request Template

```markdown
## Description
Brief description of changes

## Changes
- List of changes made
- Include any breaking changes

## Testing
- How was this tested?
- Any specific test cases added?

## Related Issues
Closes #issue_number
```

## Code Style

- Follow PEP 8 style guide
- Use type hints where appropriate
- Add docstrings to public functions
- Keep functions focused and single-purpose
- Write clear, descriptive variable names

## Documentation

- Update README for user-facing changes
- Add docstrings to new functions
- Update inline comments for complex logic
- Keep documentation up to date

## Getting Help

If you need help:
- Check existing issues and pull requests
- Read the documentation
- Join our [Discord community](https://discord.gg/hk9PGKShPK)
- Open an issue for questions

## License

By contributing to TradingAgents, you agree that your contributions will be licensed under the same license as the project.

## Contact

For more information about contributing, join our [financial AI research community](https://tauric.ai/).
