# Pre-commit Checks Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Set up pre-commit hooks for ruff, ruff-format, mypy, and bandit to enforce code quality and security checks before commits.

**Architecture:** Use the pre-commit framework with hooks defined in `.pre-commit-config.yaml`. Hooks run on staged files only, fail on all issues, and integrate with existing ruff/mypy configs in pyproject.toml. CI runs pre-commit on all builds.

**Tech Stack:** pre-commit, ruff, ruff-format, mypy, bandit, GitHub Actions

---

### Task 1: Add pre-commit to dev dependencies

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add pre-commit to optional dev dependencies**

Read `pyproject.toml` and add `pre-commit` to the `[project.optional-dependencies]` section:

```toml
[project.optional-dependencies]
dev = [
    "ruff>=0.15.5",
    "pre-commit>=4.0.0",
]
```

**Step 2: Verify the change**

Run: `cat pyproject.toml | grep -A 3 "\[project.optional-dependencies\]"`
Expected: Shows dev section with ruff and pre-commit

**Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "deps: add pre-commit to dev dependencies"
```

---

### Task 2: Create pre-commit config file

**Files:**
- Create: `.pre-commit-config.yaml`

**Step 1: Write the pre-commit configuration**

Create `.pre-commit-config.yaml` with hooks for ruff, ruff-format, mypy, and bandit:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.9.6
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.15.0
    hooks:
      - id: mypy
        additional_dependencies:
          - types-requests
        args: [--no-error-summary]

  - repo: https://github.com/PyCQA/bandit
    rev: 1.8.3
    hooks:
      - id: bandit
        args: ["-c", "pyproject.toml"]
```

**Step 2: Verify the file exists and is valid YAML**

Run: `cat .pre-commit-config.yaml`
Expected: Shows the pre-commit configuration

**Step 3: Commit**

```bash
git add .pre-commit-config.yaml
git commit -m "chore: add pre-commit configuration"
```

---

### Task 3: Add bandit configuration to pyproject.toml

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add bandit configuration section**

Read `pyproject.toml` and add a `[tool.bandit]` section:

```toml
[tool.bandit]
exclude_dirs = ["tests", ".venv", "venv"]
skips = ["B101", "B601"]
```

**Step 2: Verify the configuration**

Run: `cat pyproject.toml | grep -A 5 "\[tool.bandit\]"`
Expected: Shows bandit configuration

**Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "config: add bandit configuration"
```

---

### Task 4: Create GitHub Actions workflow for CI checks

**Files:**
- Create: `.github/workflows/pre-commit.yml`

**Step 1: Write the GitHub Actions workflow**

Create `.github/workflows/pre-commit.yml`:

```yaml
name: Pre-commit checks

on:
  pull_request:
    branches: ["main"]
  push:
    branches: ["main"]

jobs:
  pre-commit:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true

      - name: Install dependencies
        run: uv sync --all-extras --dev

      - name: Run pre-commit
        run: uv run pre-commit run --all-files
```

**Step 2: Verify the workflow file exists**

Run: `cat .github/workflows/pre-commit.yml`
Expected: Shows the GitHub Actions workflow

**Step 3: Commit**

```bash
git add .github/workflows/pre-commit.yml
git commit -m "ci: add pre-commit GitHub Actions workflow"
```

---

### Task 5: Test pre-commit installation

**Files:**
- None (testing)

**Step 1: Install pre-commit hooks locally**

Run: `uv run pre-commit install`
Expected: Output: "pre-commit installed at .git/hooks/pre-commit"

**Step 2: Verify hooks are installed**

Run: `ls -la .git/hooks/ | grep pre-commit`
Expected: Shows pre-commit hook files

**Step 3: Run pre-commit on all files to verify**

Run: `uv run pre-commit run --all-files`
Expected: Hooks run and may fail if code has issues (this is expected and can be fixed)

**Step 4: No commit needed for testing**
