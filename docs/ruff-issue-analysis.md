# Ruff Issue Analysis

**Date:** 2026-03-09

## Summary

Total ruff issues found: **1,068**

## Top Issue Categories

| Error Code | Description | Count | Fixable? |
|------------|-------------|-------|----------|
| E501 | Line too long (> 88 chars) | 272 | Auto |
| F401 | Unused imports | 89 | Manual |
| DOC201 | Missing return in docstring | 68 | Manual |
| W293 | Blank line with whitespace | 56 | Auto |
| I001 | Unsorted/unformatted imports | 48 | Auto |
| UP006 | Use `list` instead of `List` | 26 | Auto |
| F405 | Used but undefined names | 23 | Manual |
| E302 | Blank lines between functions | 22 | Auto |
| E402 | Module level imports not at top | 20 | Auto |
| INP001 | File not in package | 20 | N/A |
| Q000 | Bad quotes (should use double) | 19 | Auto |
| UP035 | Deprecated `typing` members | 19 | Auto |
| DTZ007 | Naive `datetime` with .astimezone | 18 | Manual |
| RUF013 | Implicit `Optional` | 16 | Auto |
| DTZ005 | `.now()` without timezone | 16 | Manual |
| T201 | `print` statements | 16 | N/A |
| BLE001 | Blind exception catches | 15 | Manual |
| ARG001 | Unused function arguments | 12 | Manual |
| ARG002 | Unused method arguments | 12 | Manual |
| TRY003 | Long exception messages | 12 | Manual |

## Fix Strategy

### Auto-fixable (Estimated ~700 issues)

Run: `ruff check --fix .`

This will auto-fix:
- E501 (line length) - partial fix via formatting
- W293 (whitespace)
- I001 (import organization)
- UP006 (type annotation modernization)
- E302 (blank lines)
- E402 (imports)
- Q000 (quotes)
- UP035 (deprecated typing)
- RUF013 (Optional syntax)

### Manual review required (Estimated ~350 issues)

- F401 (unused imports) - Need to verify they're truly unused
- F405 (undefined names) - Need to check if these are dynamic imports
- DOC201 (missing docstrings) - Need to add proper documentation
- DTZ007, DTZ005 (datetime issues) - Need to add timezone awareness
- BLE001 (blind exceptions) - Need to catch specific exceptions
- ARG001, ARG002 (unused args) - May need to remove or use `**kwargs`
- TRY003 (exception messages) - Refactor to shorter messages

### Ignored in config

- D (docstring conventions) - Will add gradually
- ANN (type annotations) - Will add gradually
- ERA001 (commented code) - Will clean up separately
- COM812, ISC001 (trailing commas) - Precedence conflicts

## Next Steps

1. Run `ruff check --fix .` to auto-fix auto-fixable issues
2. Run `ruff format .` to format code
3. Manually review and fix remaining issues
4. Re-run checks until clean
