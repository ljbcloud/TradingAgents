# UV and Ruff Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate TradingAgents from pip/conda/setuptools to uv for dependency management, add ruff for linting/formatting, and configure asdf for tool version management.

**Architecture:** Replace pip/conda with uv (faster, modern tool), add ruff (comprehensive linting/formatting), and use asdf for consistent tool versions across environments.

**Tech Stack:** uv (dependency management), ruff (linting/formatting), asdf (version management)

---

## Task 1: Update pyproject.toml build system

**Files:**
- Modify: `pyproject.toml:1-10`

**Step 1: Update build-system section**

Change from:
```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

To:
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Step 2: Verify pyproject.toml syntax**

Run: `python -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb'))"`
Expected: No syntax errors

**Step 3: Test uv sync with updated build system**

Run: `uv sync --frozen`
Expected: Successful dependency installation

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore: update build-system to hatchling for uv compatibility"
```

---

## Task 2: Remove requirements.txt

**Files:**
- Delete: `requirements.txt`
- Modify: `README.md` (remove references)

**Step 1: Verify no references to requirements.txt in code**

Run: `grep -r "requirements.txt" --include="*.py" --include="*.md" --include="*.yml" --include="*.yaml" .`
Expected: Only README.md references found

**Step 2: Delete requirements.txt**

Run: `rm requirements.txt`

**Step 3: Remove references from README.md**

Find and remove lines referencing `pip install -r requirements.txt`

**Step 4: Test that uv still works**

Run: `uv sync --frozen`
Expected: Dependencies installed successfully

**Step 5: Commit**

```bash
git add requirements.txt README.md
git commit -m "chore: remove requirements.txt, use uv for dependency management"
```

---

## Task 3: Create ruff.toml with strict configuration

**Files:**
- Create: `ruff.toml`

**Step 1: Create ruff.toml**

```toml
target-version = "py310"
line-length = 88

[lint]
select = ["ALL"]
ignore = [
    "ANN",      # Type annotations (optional)
    "D203",     # One blank line before class
    "D213",     # Multi-line docstring summary should start at the second line
    "COM812",   # Missing trailing comma (conflicts with formatter)
]
preview = true

[lint.isort]
known-first-party = ["tradingagents"]

[format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"
preview = true
```

**Step 2: Verify ruff.toml syntax**

Run: `ruff check --help`
Expected: Ruff command available (will use config)

**Step 3: Commit**

```bash
git add ruff.toml
git commit -m "chore: add strict ruff configuration"
```

---

## Task 4: Run ruff to identify issues

**Files:**
- No file changes (analysis only)

**Step 1: Run ruff check**

Run: `ruff check .`
Expected: List of linting issues (or none if clean)

**Step 2: Run ruff format check**

Run: `ruff format --check .`
Expected: List of formatting issues (or none if clean)

**Step 3: Document findings**

Create `docs/ruff-findings.md` with counts of issues by category

**Step 4: Commit findings**

```bash
git add docs/ruff-findings.md
git commit -m "docs: document ruff linting and formatting findings"
```

---

## Task 5: Auto-fix ruff linting issues

**Files:**
- Modify: All Python files with fixable issues

**Step 1: Auto-fix all fixable linting issues**

Run: `ruff check --fix .`
Expected: Fixes applied to multiple files

**Step 2: Review changes**

Run: `git diff`
Expected: Verify fixes are appropriate

**Step 3: Run ruff check again**

Run: `ruff check .`
Expected: No fixable issues remain

**Step 4: Commit fixes**

```bash
git add -A
git commit -m "fix: auto-fix ruff linting issues"
```

---

## Task 6: Format code with ruff

**Files:**
- Modify: All Python files needing formatting

**Step 1: Format all Python files**

Run: `ruff format .`
Expected: All files formatted

**Step 2: Verify no formatting issues**

Run: `ruff format --check .`
Expected: No formatting issues

**Step 3: Review changes**

Run: `git diff`
Expected: Verify formatting is appropriate

**Step 4: Commit formatting**

```bash
git add -A
git commit -m "style: format code with ruff"
```

---

## Task 7: Create .tool-versions for asdf

**Files:**
- Create: `.tool-versions`

**Step 1: Create .tool-versions**

```
python 3.13.0
uv 0.5.0
ruff 0.8.0
```

**Step 2: Verify .tool-versions format**

Run: `cat .tool-versions`
Expected: Three lines with tool names and versions

**Step 3: Add .tool-versions to .gitignore if needed**

Check if `.tool-versions` is in `.gitignore` - it should NOT be ignored

**Step 4: Commit**

```bash
git add .tool-versions
git commit -m "chore: add .tool-versions for asdf"
```

---

## Task 8: Update README.md with new commands

**Files:**
- Modify: `README.md`

**Step 1: Update installation section**

Replace conda/pip instructions with asdf/uv:

```bash
# Install asdf
git clone https://github.com/asdf-vm/asdf.git ~/.asdf --branch v0.14.0

# Install plugins
asdf plugin add python
asdf plugin add uv
asdf plugin add ruff

# Install tools
asdf install

# Install dependencies
uv sync
```

**Step 2: Update development section**

Add ruff commands:

```bash
# Lint code
ruff check .

# Auto-fix linting issues
ruff check --fix .

# Format code
ruff format .
```

**Step 3: Update Docker section**

Document Docker now uses uv internally

**Step 4: Update troubleshooting section**

Add common uv/ruff troubleshooting tips

**Step 5: Commit**

```bash
git add README.md
git commit -m "docs: update README with uv/ruff/asdf instructions"
```

---

## Task 9: Update Dockerfile

**Files:**
- Modify: `Dockerfile` (create if not exists)

**Step 1: Check existing Dockerfile**

Run: `ls -la | grep -i docker`
Expected: Identify Dockerfile location

**Step 2: Create/update Dockerfile with uv**

```dockerfile
FROM python:3.13-slim

# Install uv
RUN pip install uv==0.5.0

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy application code
COPY . .

# Run application
CMD ["uv", "run", "main.py"]
```

**Step 3: Test Docker build**

Run: `docker build -t tradingagents .`
Expected: Successful build

**Step 4: Commit**

```bash
git add Dockerfile
git commit -m "chore: migrate Dockerfile to use uv"
```

---

## Task 10: Update docker-compose.yml

**Files:**
- Modify: `docker/docker-compose.yml` (or root level)

**Step 1: Check docker-compose.yml location**

Run: `find . -name "docker-compose.yml" -type f`
Expected: Find docker-compose.yml

**Step 2: Review docker-compose.yml**

Read and understand current configuration

**Step 3: Update if necessary**

Most changes should be handled by Dockerfile update

**Step 4: Test docker-compose**

Run: `docker-compose up --build`
Expected: Successful build and startup

**Step 5: Commit**

```bash
git add docker-compose.yml docker/docker-compose.yml
git commit -m "chore: update docker-compose for uv compatibility"
```

---

## Task 11: Update GitHub Actions workflow - docker-image.yml

**Files:**
- Modify: `.github/workflows/docker-image.yml`

**Step 1: Read current workflow**

Run: `cat .github/workflows/docker-image.yml`

**Step 2: Add uv installation step**

Add before dependency installation:

```yaml
- name: Install uv
  run: pip install uv==0.5.0
```

**Step 3: Update dependency installation**

Replace `pip install` with:

```yaml
- name: Install dependencies
  run: uv sync --frozen
```

**Step 4: Add uv cache**

```yaml
- name: Cache uv
  uses: actions/cache@v3
  with:
    path: ~/.cache/uv
    key: ${{ runner.os }}-uv-${{ hashFiles('uv.lock') }}
```

**Step 5: Commit**

```bash
git add .github/workflows/docker-image.yml
git commit -m "ci: update docker-image workflow to use uv"
```

---

## Task 12: Update GitHub Actions workflow - docker-compose.yml

**Files:**
- Modify: `.github/workflows/docker-compose.yml`

**Step 1: Read current workflow**

Run: `cat .github/workflows/docker-compose.yml`

**Step 2: Add uv installation step**

Same as Task 11

**Step 3: Update dependency installation**

Same as Task 11

**Step 4: Add uv cache**

Same as Task 11

**Step 5: Commit**

```bash
git add .github/workflows/docker-compose.yml
git commit -m "ci: update docker-compose workflow to use uv"
```

---

## Task 13: Add ruff check to GitHub Actions

**Files:**
- Modify: `.github/workflows/docker-image.yml` and `.github/workflows/docker-compose.yml`

**Step 1: Add linting step to docker-image.yml**

Add after dependency installation:

```yaml
- name: Lint with ruff
  run: uv run ruff check .

- name: Check formatting with ruff
  run: uv run ruff format --check .
```

**Step 2: Add linting step to docker-compose.yml**

Same as Step 1

**Step 3: Test workflows locally (optional)**

Run: `act` if installed to test workflows

**Step 4: Commit**

```bash
git add .github/workflows/
git commit -m "ci: add ruff linting and formatting checks"
```

---

## Task 14: Create CONTRIBUTING.md

**Files:**
- Create: `docs/CONTRIBUTING.md` or root level

**Step 1: Create CONTRIBUTING.md**

```markdown
# Contributing to TradingAgents

## Setup

### Prerequisites

- asdf (tool version manager)
- git

### Installation

```bash
# Install asdf
git clone https://github.com/asdf-vm/asdf.git ~/.asdf --branch v0.14.0
echo '. "$HOME/.asdf/asdf.sh"' >> ~/.bashrc
source ~/.bashrc

# Install plugins
asdf plugin add python
asdf plugin add uv
asdf plugin add ruff

# Install tools
asdf install

# Install dependencies
uv sync
```

## Development Workflow

### Running the application

```bash
uv run main.py
```

### Linting

```bash
# Check for linting issues
ruff check .

# Auto-fix issues
ruff check --fix .
```

### Formatting

```bash
# Format code
ruff format .

# Check formatting without making changes
ruff format --check .
```

### Adding dependencies

```bash
# Add a new dependency
uv add package-name

# Add dev dependency
uv add --dev package-name

# Remove dependency
uv remove package-name
```

## Testing

```bash
# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=tradingagents
```

## Code Style

- Use ruff for linting and formatting
- Line length: 88 characters
- Target Python: 3.10+
- Follow PEP 8 guidelines

## Pull Request Process

1. Ensure all tests pass
2. Run ruff check and fix all issues
3. Format code with ruff format
4. Update documentation as needed
5. Submit PR with clear description
```

**Step 2: Commit**

```bash
git add CONTRIBUTING.md docs/CONTRIBUTING.md
git commit -m "docs: add CONTRIBUTING.md with development workflow"
```

---

## Task 15: Create uv-workflow.md documentation

**Files:**
- Create: `docs/uv-workflow.md`

**Step 1: Create uv-workflow.md**

```markdown
# UV Workflow Guide

UV is a fast Python package installer and resolver, written in Rust.

## Common Commands

### Initial Setup

```bash
# Install dependencies
uv sync

# Install specific dependency group
uv sync --group dev

# Install with frozen lockfile
uv sync --frozen
```

### Managing Dependencies

```bash
# Add a dependency
uv add package-name

# Add with specific version
uv add package-name==1.2.3

# Add dev dependency
uv add --dev package-name

# Remove dependency
uv remove package-name
```

### Running Scripts

```bash
# Run main script
uv run main.py

# Run pytest
uv run pytest

# Run with additional arguments
uv run python script.py --option value
```

### Virtual Environment

```bash
# Activate virtual environment
source .venv/bin/activate

# Deactivate
deactivate

# Recreate virtual environment
uv sync --reinstall
```

## Troubleshooting

### Dependencies not installing

```bash
# Clear cache and retry
uv cache clean
uv sync --reinstall
```

### Lock file issues

```bash
# Update lock file
uv lock

# Regenerate from scratch
rm uv.lock
uv lock
```

### Python version conflicts

```bash
# Check Python version
uv run python --version

# Set Python version
uv python pin 3.13
```

## Best Practices

- Always use `uv run` for reproducible environments
- Commit `uv.lock` to version control
- Use `--frozen` in CI/CD for reproducible builds
- Run `uv sync` after pulling changes
```

**Step 2: Commit**

```bash
git add docs/uv-workflow.md
git commit -m "docs: add UV workflow guide"
```

---

## Task 16: Test complete setup

**Files:**
- No file changes (verification only)

**Step 1: Clean install test**

Run: `rm -rf .venv && uv sync --frozen`
Expected: Dependencies installed successfully

**Step 2: Run application**

Run: `uv run python -c "import tradingagents; print('Import successful')"`
Expected: No import errors

**Step 3: Run ruff checks**

Run: `ruff check . && ruff format --check .`
Expected: No errors

**Step 4: Test Docker build**

Run: `docker build -t tradingagents .`
Expected: Successful build

**Step 5: Create verification notes**

Create `docs/verification.md` with test results

**Step 6: Commit**

```bash
git add docs/verification.md
git commit -m "docs: add migration verification notes"
```

---

## Task 17: Update .gitignore if needed

**Files:**
- Modify: `.gitignore`

**Step 1: Review .gitignore**

Run: `cat .gitignore`

**Step 2: Ensure uv cache is not committed**

Add if not present:
```
.uv-cache/
```

**Step 3: Ensure .venv is not committed**

Add if not present:
```
.venv/
```

**Step 4: Ensure .tool-versions IS committed**

Remove from .gitignore if present

**Step 5: Commit**

```bash
git add .gitignore
git commit -m "chore: update .gitignore for uv"
```

---

## Task 18: Final verification and cleanup

**Files:**
- No file changes (verification)

**Step 1: Run full ruff check**

Run: `ruff check . && ruff format --check .`
Expected: No issues

**Step 2: Verify all dependencies work**

Run: `uv run python -m pytest tests/ -v` (if tests exist)
Expected: Tests pass

**Step 3: Check git status**

Run: `git status`
Expected: Clean working directory (all changes committed)

**Step 4: Create migration summary**

Create `docs/migration-summary.md` with:
- Changes made
- Files modified
- Benefits achieved
- Known issues (if any)

**Step 5: Commit**

```bash
git add docs/migration-summary.md
git commit -m "docs: add migration summary"
```

---

## Task 19: Create migration PR

**Files:**
- No file changes (git operation)

**Step 1: Push to remote**

Run: `git push origin development`
Expected: Successful push

**Step 2: Create PR description**

Summary:
```
Migrate from pip/conda to uv, add ruff for linting/formatting, configure asdf

Changes:
- Updated pyproject.toml build system to uv-compatible backend
- Removed requirements.txt (pyproject.toml is source of truth)
- Added strict ruff.toml configuration
- Created .tool-versions for asdf
- Updated Dockerfile to use uv
- Updated GitHub Actions workflows
- Added CONTRIBUTING.md and uv-workflow.md docs
- Updated README with new commands

Benefits:
- Faster dependency installation (10-100x faster than pip)
- Consistent tooling across environments
- Comprehensive linting and formatting
- Better developer experience
```

**Step 3: Create PR**

Run: `gh pr create --title "Migrate to uv and ruff" --body <description above>`

**Step 4: Monitor CI/CD**

Wait for GitHub Actions to complete successfully

---

## Success Criteria Verification

- [x] uv successfully installs all dependencies
- [x] ruff passes without errors
- [x] Code is formatted according to ruff rules
- [x] Docker builds and runs successfully
- [x] CI/CD workflows pass with uv and ruff
- [x] Documentation is accurate and complete
