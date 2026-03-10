# Pre-commit Checks Design

## Overview
Set up pre-commit hooks for the TradingAgents repository to enforce code quality standards before commits. This ensures consistent code style, type safety, and security by running automated checks on staged files.

## Requirements
- **Checks**: Code linting (ruff), formatting (ruff format), type checking (mypy), security (bandit)
- **Strictness**: Fail on all issues
- **Scope**: Changed files only (staged changes)
- **CI Integration**: Run on all builds (PRs and pushes to main)

## Architecture

### Pre-commit Framework
Uses the pre-commit framework to manage Git hooks. Hooks run on staged files before commits, with checks executed in order: ruff lint → ruff format → mypy → bandit. Each hook fails the commit if it finds issues.

### Configuration Management
- `.pre-commit-config.yaml`: Defines hooks, versions, file patterns, and exclusions
- `pyproject.toml`: Ruff and mypy settings already configured here, used by hooks to avoid duplication
- Hook environments cached in `.cache/pre-commit` for performance

## Components

### Pre-commit Hooks
| Hook | Purpose | Tool |
|------|---------|------|
| Ruff lint | Code style issues and potential bugs | ruff |
| Ruff format | Code formatting consistency | ruff-format |
| Mypy | Static type checking | mypy |
| Bandit | Security vulnerability scanning | bandit |

### Configuration Files
- `.pre-commit-config.yaml`: Pre-commit hook definitions
- `pyproject.toml`: Tool configurations (ruff, mypy)

### Installation
- Add `pre-commit` to dev dependencies in pyproject.toml
- Provide setup command: `pre-commit install`

## Data Flow

1. Developer stages changes: `git add`
2. Developer commits: `git commit`
3. Pre-commit intercepts and runs hooks on staged files
4. Each hook processes files through configured tool
5. If any hook fails → commit blocked with error output
6. If all hooks pass → commit proceeds

## Error Handling

### Hook Failures
- Clear error messages with line numbers and descriptions
- Commit blocked until errors are fixed
- Manual testing: `pre-commit run --all-files`

### Configuration Errors
- Invalid config caught during `pre-commit install`
- Missing dependencies show clear error messages
- Version conflicts prevent installation

### CI/CD Integration
- GitHub Actions runs pre-commit with `pre-commit run --all-files`
- Ensures all checks pass even if developers skip locally

## Testing Strategy

### Local Testing
- Developers install hooks: `pre-commit install`
- Hooks automatically run before commits
- Manual verification: `pre-commit run --all-files`

### CI/CD Testing
- GitHub Action workflow runs on all builds
- Workflow runs on PRs and pushes to main
- Cached environments for faster CI runs

### Verification
- Test hooks on various file types (.py, .md, .yaml)
- Verify error messages are clear and actionable
- Confirm hooks respect existing ruff/mypy configurations

## Implementation Notes
- Leverage existing ruff and mypy configs in pyproject.toml
- Pin hook versions for reproducibility
- Consider adding bandit exclusions if needed (known false positives)
