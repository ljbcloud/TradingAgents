# UV and Ruff Migration Design

> **Design Document:** Migration to uv, ruff, and asdf tooling

**Date:** 2026-03-09

**Goal:** Migrate TradingAgents from pip/conda/setuptools to uv for dependency management, add ruff for linting/formatting, and configure asdf for tool version management.

---

## Overview

Complete migration to modern Python tooling stack to simplify development workflow, improve performance, and enforce consistent code quality.

## Architecture

### 1. Dependency Management (uv)
- Replace pip/conda with uv for all dependency operations
- pyproject.toml remains source of truth
- uv.lock as lockfile
- Remove requirements.txt entirely
- Update build system to uv backend

### 2. Linting and Formatting (ruff)
- Strict configuration with all rules enabled
- Line length: 88 characters
- Target Python: 3.10+
- Preview mode enabled
- CI/CD integration

### 3. Tool Version Management (asdf)
- Python: 3.13.0 (latest stable)
- uv: 0.5.0
- ruff: 0.8.0
- Minimum Python requirement: >=3.10

### 4. Docker Integration
- uv-based dependency installation
- Python 3.13-slim base image
- Cached uv.lock for faster rebuilds

### 5. CI/CD Updates
- GitHub Actions workflows
- uv for dependency installation
- ruff for linting/formatting checks

---

## Key Decisions

1. **Remove requirements.txt** - pyproject.toml is sufficient, eliminates duplication
2. **Migrate Docker to uv** - Full consistency across environments
3. **Python version** - .tool-versions pins 3.13.0, pyproject.toml allows >=3.10
4. **Strict ruff config** - Maximum code quality enforcement
5. **Update CI/CD** - All workflows use uv and ruff

---

## Technical Approach

### Phase 1: Dependency Management
- Update pyproject.toml `[build-system]` to use uv
- Remove requirements.txt
- Verify uv sync works with existing dependencies

### Phase 2: Linting and Formatting
- Create ruff.toml with strict configuration
- Add pre-commit hooks (optional)
- Run ruff to identify and fix issues

### Phase 3: Tool Versioning
- Create .tool-versions file
- Document asdf setup in README

### Phase 4: Docker Migration
- Rewrite Dockerfile to use uv
- Update docker-compose if needed
- Test Docker builds

### Phase 5: CI/CD Integration
- Update .github/workflows files
- Add ruff checks
- Cache uv cache directory

### Phase 6: Documentation
- Update README with new commands
- Add CONTRIBUTING.md with development workflow
- Update any existing setup documentation

---

## Success Criteria

1. ✅ uv successfully installs all dependencies
2. ✅ ruff passes without errors
3. ✅ Code is formatted according to ruff rules
4. ✅ Docker builds and runs successfully
5. ✅ CI/CD workflows pass with uv and ruff
6. ✅ Documentation is accurate and complete

---

## Rollback Strategy

If any phase fails:
- Revert specific changes (git revert)
- Keep working setup in separate branch
- Document issues for future resolution

---

## Open Questions

None - all decisions finalized during design phase.
