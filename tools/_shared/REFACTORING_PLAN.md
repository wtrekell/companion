# Shared Module Migration: Parallel Refactoring Plan

**Date Created:** 2025-10-30
**Status:** READY FOR EXECUTION
**Goal:** Migrate shared utilities from `tools/gmail/src/shared/` to `tools/_shared/`
**Strategy:** Parallel execution across 6 independent teams
**Total Files Affected:** 16 files (13 Python, 1 TOML, 3 Markdown)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Pre-Migration Checklist](#pre-migration-checklist)
3. [Phase 1: Core Migration](#phase-1-core-migration)
4. [Phase 2: Parallel Team Assignments](#phase-2-parallel-team-assignments)
5. [Phase 3: Streamlining Improvements](#phase-3-streamlining-improvements-optional)
6. [Phase 4: Verification & Testing](#phase-4-verification--testing)
7. [Phase 5: Git Operations](#phase-5-git-operations)
8. [Rollback Plan](#rollback-plan)
9. [Post-Migration Validation](#post-migration-validation)

---

## Executive Summary

### Why This Refactoring?

**Current Problem:**
- Shared utilities are nested in `tools/gmail/src/shared/`
- Creates artificial dependency on Gmail tool
- Confusing import patterns (relative in Gmail, absolute in others)
- Implies Gmail "owns" shared code

**Solution:**
- Move to neutral location: `tools/_shared/`
- Standardize all imports to absolute: `from tools._shared`
- Clear separation: tool code vs shared utilities
- Better discoverability and maintainability

### Impact Summary

**Files to Update:**
- **Python code:** 13 files
  - Gmail: 5 files (relative → absolute imports)
  - Reddit: 3 files (path update)
  - StackExchange: 3 files (path update)
  - Web Articles: 1 file (path update)
  - Tests: 1 file (path update)
- **Configuration:** 1 file (`pyproject.toml`)
- **Documentation:** 3 files (README.md, INTEGRATION_GUIDE.md, CLAUDE.md)

**Benefits:**
- ✅ Eliminates architectural debt
- ✅ Enables independent tool development
- ✅ Standardizes import patterns across all tools
- ✅ Improves code discoverability
- ✅ Zero breaking changes (all imports updated atomically)

**Estimated Effort:** 2-3 hours with 6 parallel teams
**Risk Level:** LOW (no circular dependencies, comprehensive tests)

---

## Pre-Migration Checklist

Before starting, ensure:

- [ ] All team members have latest `main` branch: `git pull origin main`
- [ ] Working directory is clean: `git status` shows no uncommitted changes
- [ ] All tests pass: `uv run pytest tools/gmail/tests/`
- [ ] Linting passes: `uv run ruff check . && uv run ruff format .`
- [ ] Type checking passes: `uv run mypy .`
- [ ] Create feature branch: `git checkout -b refactor/migrate-shared-modules`
- [ ] Team leads assigned to each of 6 teams
- [ ] Communication channel established (Slack/Discord/etc.)

---

## Phase 1: Core Migration

**Responsibility:** Lead Engineer (Sequential Execution Required)
**Duration:** 15-20 minutes
**Status:** MUST COMPLETE BEFORE PHASE 2

### Step 1.1: Create Directory Structure

```bash
# From repository root
cd /Users/williamtrekell/Documents/army-of-me

# Create the new shared directory
mkdir -p tools/_shared

# Verify creation
ls -la tools/_shared
```

### Step 1.2: Move Shared Modules (Using git mv)

**IMPORTANT:** Use `git mv` to preserve file history

```bash
# Move all 8 shared files
git mv tools/gmail/src/shared/__init__.py tools/_shared/__init__.py
git mv tools/gmail/src/shared/config.py tools/_shared/config.py
git mv tools/gmail/src/shared/exceptions.py tools/_shared/exceptions.py
git mv tools/gmail/src/shared/filters.py tools/_shared/filters.py
git mv tools/gmail/src/shared/http_client.py tools/_shared/http_client.py
git mv tools/gmail/src/shared/output.py tools/_shared/output.py
git mv tools/gmail/src/shared/security.py tools/_shared/security.py
git mv tools/gmail/src/shared/storage.py tools/_shared/storage.py

# Verify all files moved
ls -la tools/_shared/
# Should show 8 .py files (2,146 LOC total)
```

### Step 1.3: Remove Old Directory

```bash
# Remove the now-empty shared directory
git rm -r tools/gmail/src/shared/

# Verify removal
ls tools/gmail/src/
# Should NOT show 'shared' directory
```

### Step 1.4: Verify Structure

```bash
# Confirm new structure
tree tools/_shared/
# Expected output:
# tools/_shared/
# ├── __init__.py       (65 LOC)
# ├── config.py         (201 LOC)
# ├── exceptions.py     (141 LOC)
# ├── filters.py        (243 LOC)
# ├── http_client.py    (151 LOC)
# ├── output.py         (300 LOC)
# ├── security.py       (523 LOC)
# └── storage.py        (522 LOC)
```

### Step 1.5: Stage Changes

```bash
# Stage the moved files
git add tools/_shared/

# Check status
git status
# Should show:
# - renamed: tools/gmail/src/shared/* → tools/_shared/*
# - deleted: tools/gmail/src/shared/
```

**✅ CHECKPOINT:** Announce to all teams that Phase 1 is complete. Teams can now begin Phase 2 work.

---

## Phase 2: Parallel Team Assignments

**All teams work simultaneously after Phase 1 completes.**

Each team should:
1. Create a working branch from the Phase 1 state
2. Make their assigned changes
3. Test locally
4. Prepare for integration

---

### Team 1: Gmail Tool Updates

**Lead:** [Assign team lead]
**Complexity:** MEDIUM (relative → absolute import conversion)
**Files:** 5 Python files
**Import Changes:** 17 statements

#### Files to Update

1. **tools/gmail/src/collectors/gmail/collector.py**
2. **tools/gmail/src/collectors/gmail/config.py**
3. **tools/gmail/src/collectors/gmail/auth.py**
4. **tools/gmail/src/collectors/gmail/send_cli.py**
5. **tools/gmail/src/collectors/gmail/cli.py**

#### Detailed Instructions

##### File 1: collector.py

**Location:** `tools/gmail/src/collectors/gmail/collector.py`

**Line 21-29 - FIND:**
```python
from ...shared.exceptions import (
    AuthenticationFailureError,
    ConfigurationValidationError,
    ContentProcessingError,
    StateManagementError,
)
from ...shared.filters import apply_content_filter
from ...shared.output import ensure_folder_structure, write_markdown_file
from ...shared.storage import JsonStateManager
```

**REPLACE WITH:**
```python
from tools._shared.exceptions import (
    AuthenticationFailureError,
    ConfigurationValidationError,
    ContentProcessingError,
    StateManagementError,
)
from tools._shared.filters import apply_content_filter
from tools._shared.output import ensure_folder_structure, write_markdown_file
from tools._shared.storage import JsonStateManager
```

**Line 1272 - FIND:**
```python
from ...shared.exceptions import StateManagementError
```

**REPLACE WITH:**
```python
from tools._shared.exceptions import StateManagementError
```

##### File 2: config.py

**Location:** `tools/gmail/src/collectors/gmail/config.py`

**Lines 10-12 - FIND:**
```python
from ...shared.config import load_yaml_config
from ...shared.exceptions import ConfigurationValidationError
from ...shared.security import sanitize_text_content
```

**REPLACE WITH:**
```python
from tools._shared.config import load_yaml_config
from tools._shared.exceptions import ConfigurationValidationError
from tools._shared.security import sanitize_text_content
```

##### File 3: auth.py

**Location:** `tools/gmail/src/collectors/gmail/auth.py`

**Lines 15-16 - FIND:**
```python
from ...shared.exceptions import AuthenticationFailureError, InputValidationError
from ...shared.security import sanitize_text_content
```

**REPLACE WITH:**
```python
from tools._shared.exceptions import AuthenticationFailureError, InputValidationError
from tools._shared.security import sanitize_text_content
```

##### File 4: send_cli.py

**Location:** `tools/gmail/src/collectors/gmail/send_cli.py`

**Lines 10-11 - FIND:**
```python
from ...shared.exceptions import InputValidationError, PathTraversalError
from ...shared.security import sanitize_text_content, validate_email_address
```

**REPLACE WITH:**
```python
from tools._shared.exceptions import InputValidationError, PathTraversalError
from tools._shared.security import sanitize_text_content, validate_email_address
```

##### File 5: cli.py

**Location:** `tools/gmail/src/collectors/gmail/cli.py`

**Line 13 - FIND:**
```python
from ...shared.exceptions import AuthenticationFailureError, ContentProcessingError
```

**REPLACE WITH:**
```python
from tools._shared.exceptions import AuthenticationFailureError, ContentProcessingError
```

#### Team 1 Verification

```bash
# Verify no relative imports remain
grep -n "from \.\.\.shared" tools/gmail/src/collectors/gmail/*.py
# Should return nothing

# Verify new imports are present
grep -n "from tools\._shared" tools/gmail/src/collectors/gmail/*.py
# Should show 17 matches across 5 files

# Test Gmail collector
uv run gmail-collect --help
# Should display help without errors
```

---

### Team 2: Reddit Tool Updates

**Lead:** [Assign team lead]
**Complexity:** LOW (simple find/replace)
**Files:** 3 Python files
**Import Changes:** 9 statements

#### Files to Update

1. **tools/reddit/src/collectors/reddit/collector.py**
2. **tools/reddit/src/collectors/reddit/config.py**
3. **tools/reddit/src/collectors/reddit/cli.py**

#### Simple Find/Replace Pattern

**FIND (in all 3 files):**
```python
from tools.gmail.src.shared
```

**REPLACE WITH:**
```python
from tools._shared
```

#### Detailed Line Numbers

##### File 1: collector.py
- Lines 14-19: 6 import statements

##### File 2: config.py
- Line 9: 1 import statement (imports 2 functions)

##### File 3: cli.py
- Line 12: 1 import statement

#### Team 2 Verification

```bash
# Verify no old imports remain
grep -n "tools\.gmail\.src\.shared" tools/reddit/src/collectors/reddit/*.py
# Should return nothing

# Verify new imports are present
grep -n "from tools\._shared" tools/reddit/src/collectors/reddit/*.py
# Should show 9 matches across 3 files

# Test Reddit collector
uv run reddit-collect --help
# Should display help without errors
```

---

### Team 3: StackExchange Tool Updates

**Lead:** [Assign team lead]
**Complexity:** LOW (simple find/replace)
**Files:** 3 Python files
**Import Changes:** 13 statements (heaviest user of shared modules)

#### Files to Update

1. **tools/stackexchange/src/collectors/stackexchange/collector.py**
2. **tools/stackexchange/src/collectors/stackexchange/config.py**
3. **tools/stackexchange/src/collectors/stackexchange/cli.py**

#### Simple Find/Replace Pattern

**FIND (in all 3 files):**
```python
from tools.gmail.src.shared
```

**REPLACE WITH:**
```python
from tools._shared
```

#### Detailed Line Numbers

##### File 1: collector.py
- Lines 16-21: 6 import statements (10 total items)

##### File 2: config.py
- Lines 8-10: 3 import statements

##### File 3: cli.py
- Lines 12-13: 2 import statements

#### Team 3 Verification

```bash
# Verify no old imports remain
grep -n "tools\.gmail\.src\.shared" tools/stackexchange/src/collectors/stackexchange/*.py
# Should return nothing

# Verify new imports are present
grep -n "from tools\._shared" tools/stackexchange/src/collectors/stackexchange/*.py
# Should show 13 matches across 3 files

# Test StackExchange collector
uv run stackexchange-collect --help
# Should display help without errors
```

---

### Team 4: Web Articles Tool Updates

**Lead:** [Assign team lead]
**Complexity:** TRIVIAL (single file, single import)
**Files:** 1 Python file
**Import Changes:** 1 statement

#### File to Update

**tools/web_articles/src/collectors/web_articles/config.py**

#### Change Required

**Line 9 - FIND:**
```python
from tools.gmail.src.shared.config import load_yaml_config
```

**REPLACE WITH:**
```python
from tools._shared.config import load_yaml_config
```

#### Team 4 Verification

```bash
# Verify no old imports remain
grep -n "tools\.gmail\.src\.shared" tools/web_articles/src/collectors/web_articles/*.py
# Should return nothing

# Verify new imports are present
grep -n "from tools\._shared" tools/web_articles/src/collectors/web_articles/*.py
# Should show 1 match

# Test Web Articles collectors
uv run web-discover --help
uv run web-fetch --help
# Both should display help without errors
```

---

### Team 5: Tests & Configuration Updates

**Lead:** [Assign team lead]
**Complexity:** TRIVIAL (2 files, 2 changes)
**Files:** 2 files
**Changes:** 2 statements

#### File 1: Test Configuration

**Location:** `tools/gmail/tests/test_config.py`

**Line 20 - FIND:**
```python
from tools.gmail.src.shared.exceptions import ConfigurationValidationError
```

**REPLACE WITH:**
```python
from tools._shared.exceptions import ConfigurationValidationError
```

#### File 2: Root Configuration

**Location:** `pyproject.toml` (repository root)

**Line 123 - FIND:**
```toml
[[tool.mypy.overrides]]
module = "tools.gmail.src.shared.http_client"
ignore_errors = true
```

**REPLACE WITH:**
```toml
[[tool.mypy.overrides]]
module = "tools._shared.http_client"
ignore_errors = true
```

#### Team 5 Verification

```bash
# Verify test file updated
grep -n "tools\.gmail\.src\.shared" tools/gmail/tests/test_config.py
# Should return nothing

grep -n "from tools\._shared" tools/gmail/tests/test_config.py
# Should show 1 match

# Verify pyproject.toml updated
grep -n "tools\.gmail\.src\.shared" pyproject.toml
# Should return nothing

grep -n "tools\._shared" pyproject.toml
# Should show 1 match

# Run tests
uv run pytest tools/gmail/tests/
# All tests should pass
```

---

### Team 6: Documentation Updates

**Lead:** [Assign team lead]
**Complexity:** LOW (3 files, ~17 references)
**Files:** 3 Markdown files

#### Files to Update

1. **tools/README.md** (~10 references)
2. **tools/INTEGRATION_GUIDE.md** (~2 references)
3. **tools/CLAUDE.md** (~5 references)

#### Find/Replace Patterns

Apply these in order to all 3 documentation files:

**Pattern 1 - Path references:**
```
FIND: tools/gmail/src/shared/
REPLACE WITH: tools/_shared/
```

**Pattern 2 - Absolute import examples:**
```
FIND: tools.gmail.src.shared
REPLACE WITH: tools._shared
```

**Pattern 3 - Relative import examples:**
```
FIND: from ...shared
REPLACE WITH: from tools._shared
```

#### Specific Locations

##### README.md
- Line 180: "Shared utilities live in `tools/gmail/src/shared/`"
- Line 859: "Use shared utilities from `tools.gmail.src.shared`"
- Line 877: "common functionality through the `tools/gmail/src/shared/` library"
- Lines 881-884: Example imports
- Lines 938-940: Example imports

##### INTEGRATION_GUIDE.md
- Line 303: "Reddit uses absolute imports (`from tools.gmail.src.shared`)"
- Line 310: "Uses absolute imports from `tools.gmail.src.shared`"

##### CLAUDE.md
- Lines 75, 132, 142-145, 149, 238, 347: Multiple references

#### Additional CLAUDE.md Updates

**Remove notion-todoist references** (tool doesn't exist):
- Lines 7, 34-40: Remove from commands section
- Lines 92-105: Remove directory structure
- Lines 152-170: Remove architecture section
- Lines 264-267: Remove state management section
- Lines 289-324: Remove workflows section
- Lines 352-360: Remove gotchas section
- Lines 379-383: Remove documentation references
- Lines 392-397: Remove status claims

#### Team 6 Verification

```bash
# Verify no old path references remain in docs
grep -n "gmail/src/shared" tools/README.md tools/INTEGRATION_GUIDE.md tools/CLAUDE.md
# Should return nothing

# Verify new path is present
grep -n "tools/_shared" tools/README.md tools/INTEGRATION_GUIDE.md tools/CLAUDE.md
# Should show ~17 matches

# Verify notion-todoist removed from CLAUDE.md
grep -n "notion-todoist" tools/CLAUDE.md
# Should return nothing
```

---

## Phase 3: Streamlining Improvements (Optional)

**Responsibility:** Platform Team (Post-Migration)
**Priority:** MEDIUM
**Can be done in separate PR after main migration**

### Improvement 1: Standardize State File Locations

**Problem:** Inconsistent state file locations across tools

**Current State:**
- Gmail: `output/gmail/.gmail_state.json` (hidden file)
- Reddit: `output/reddit/reddit_state.json` (visible file)
- StackExchange: `output/stackexchange/stackexchange_state.db`
- Web Articles: `tools/web_articles/data/gatherers_state.json` (in tool directory)

**Proposed Standard:**
- All state files in `output/<tool>/` directory
- Consistent naming: `<tool>_state.json` or `<tool>_state.db`
- No hidden files (remove leading dot from `.gmail_state.json`)

**Changes Required:**

1. **Gmail:** Update config to use `output/gmail/gmail_state.json` (remove dot)
2. **Web Articles:** Move state to `output/web-articles/web_articles_state.json`

**Impact:** Low (only affects new installations; existing state files remain functional)

### Improvement 2: Standardize Configuration Paths

**Problem:** Web Articles uses tool-relative paths instead of root-relative

**Current Web Articles Config:**
```yaml
state_file: "tools/web_articles/data/gatherers_state.json"
review_file: "tools/web_articles/data/links_for_review.yaml"
```

**Proposed Change:**
```yaml
state_file: "output/web-articles/web_articles_state.json"
review_file: "output/web-articles/links_for_review.yaml"
```

**Benefits:**
- Consistent with other tools
- All output in predictable location
- Easier backup/restore procedures

### Improvement 3: Remove Transcribe from Root pyproject.toml

**Problem:** Transcribe has its own `pyproject.toml` but is listed in root dependencies

**Action:** Verify transcribe is truly independent and document separate installation

---

## Phase 4: Verification & Testing

**Responsibility:** QA Team + All Team Leads
**Duration:** 30-45 minutes

### Step 4.1: Code Quality Checks

```bash
# From repository root
cd /Users/williamtrekell/Documents/army-of-me

# Run linter
uv run ruff check .
# Expected: All checks pass

# Run formatter check
uv run ruff format --check .
# Expected: All files formatted correctly

# Apply formatting if needed
uv run ruff format .
```

### Step 4.2: Type Checking

```bash
# Run mypy on all code
uv run mypy .
# Expected: No type errors

# Specifically check shared modules
uv run mypy tools/_shared/
# Expected: All shared modules pass strict type checking
```

### Step 4.3: Run Existing Tests

```bash
# Run Gmail tests
uv run pytest tools/gmail/tests/ -v
# Expected: All tests pass (currently ~3 tests)

# Run with coverage
uv run pytest tools/gmail/tests/ --cov=tools.gmail --cov=tools._shared
# Check that shared modules are being tested
```

### Step 4.4: Console Script Testing

Test each console script individually:

```bash
# Gmail
uv run gmail-collect --help
uv run gmail-send --help

# Reddit
uv run reddit-collect --help

# StackExchange
uv run stackexchange-collect --help

# Web Articles
uv run web-discover --help
uv run web-fetch --help
```

**Expected:** All commands display help text without import errors.

### Step 4.5: Dry Run Testing

```bash
# Test Gmail (requires valid config)
uv run gmail-collect --dry-run --verbose
# Expected: Loads config, validates, but doesn't process emails

# Test Reddit (requires valid config)
uv run reddit-collect --dry-run --verbose
# Expected: Loads config, connects to Reddit, but doesn't save content

# Test StackExchange (requires valid config)
uv run stackexchange-collect --dry-run --verbose
# Expected: Loads config, queries API, but doesn't save content
```

### Step 4.6: Verify No Old References

```bash
# Search all Python files for old import paths
grep -r "from tools\.gmail\.src\.shared" tools/ --include="*.py"
# Expected: No matches

grep -r "from \.\.\.shared" tools/ --include="*.py"
# Expected: No matches

# Search documentation for old paths
grep -r "gmail/src/shared" tools/ --include="*.md"
# Expected: No matches

# Verify new imports are present
grep -r "from tools\._shared" tools/ --include="*.py" | wc -l
# Expected: 41 matches (all import statements updated)
```

### Step 4.7: Import Testing

Create temporary test script to verify all imports work:

```bash
# Create test script
cat > /tmp/test_imports.py << 'EOF'
"""Test that all shared module imports work after migration."""

# Test direct imports
from tools._shared.config import load_yaml_config, get_env_var
from tools._shared.exceptions import (
    SignalCollectorError,
    ConfigurationValidationError,
    AuthenticationFailureError,
    StateManagementError,
)
from tools._shared.filters import apply_content_filter, matches_keywords
from tools._shared.http_client import RateLimitedHttpClient
from tools._shared.output import (
    ensure_folder_structure,
    write_markdown_file,
    update_existing_file,
)
from tools._shared.security import (
    validate_url_for_ssrf,
    sanitize_filename,
    sanitize_text_content,
    validate_email_address,
)
from tools._shared.storage import JsonStateManager, SqliteStateManager

print("✅ All shared module imports successful!")
print(f"✅ Config module: {load_yaml_config.__name__}")
print(f"✅ Exceptions module: {SignalCollectorError.__name__}")
print(f"✅ Filters module: {apply_content_filter.__name__}")
print(f"✅ HTTP client: {RateLimitedHttpClient.__name__}")
print(f"✅ Output module: {write_markdown_file.__name__}")
print(f"✅ Security module: {validate_url_for_ssrf.__name__}")
print(f"✅ Storage module: {JsonStateManager.__name__}")
EOF

# Run test
uv run python /tmp/test_imports.py
# Expected: All imports successful, no errors

# Clean up
rm /tmp/test_imports.py
```

---

## Phase 5: Git Operations

**Responsibility:** Lead Engineer
**Duration:** 10 minutes

### Step 5.1: Review Changes

```bash
# Check git status
git status

# Review all changes
git diff --staged

# Count changed files
git diff --staged --name-only | wc -l
# Expected: 16 files (13 .py, 1 .toml, 3 .md)
```

### Step 5.2: Stage All Changes

```bash
# Stage all updated files (if not already staged)
git add tools/_shared/
git add tools/gmail/src/collectors/gmail/*.py
git add tools/reddit/src/collectors/reddit/*.py
git add tools/stackexchange/src/collectors/stackexchange/*.py
git add tools/web_articles/src/collectors/web_articles/*.py
git add tools/gmail/tests/test_config.py
git add pyproject.toml
git add tools/README.md
git add tools/INTEGRATION_GUIDE.md
git add tools/CLAUDE.md
git add tools/_shared/CURRENT_STATE.md
git add tools/_shared/REFACTORING_PLAN.md

# Verify staging
git status
```

### Step 5.3: Commit Changes

```bash
# Create detailed commit message
git commit -m "refactor: migrate shared modules to tools/_shared/

Move shared utilities from tools/gmail/src/shared/ to tools/_shared/ to
eliminate architectural debt and establish clear separation between tool
code and shared libraries.

Changes:
- Move 8 shared modules (2,146 LOC) using git mv to preserve history
- Update 13 Python files with new import paths
  - Gmail: Convert relative imports to absolute (5 files)
  - Reddit: Update import paths (3 files)
  - StackExchange: Update import paths (3 files)
  - Web Articles: Update import paths (1 file)
  - Tests: Update import paths (1 file)
- Update pyproject.toml mypy override for http_client
- Update documentation with new paths (3 files)
- Remove notion-todoist references (non-existent tool)

Benefits:
- Shared utilities now in neutral location
- All tools use consistent absolute imports
- Clear separation of concerns
- Improved discoverability

Testing:
- All existing tests pass
- All console scripts verified with --help
- Dry-run testing completed for all tools
- Type checking passes (mypy strict mode)
- Linting passes (ruff)

Co-authored-by: Team 1 Gmail <gmail-team@example.com>
Co-authored-by: Team 2 Reddit <reddit-team@example.com>
Co-authored-by: Team 3 StackExchange <stackexchange-team@example.com>
Co-authored-by: Team 4 Web Articles <web-articles-team@example.com>
Co-authored-by: Team 5 Tests <tests-team@example.com>
Co-authored-by: Team 6 Docs <docs-team@example.com>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Step 5.4: Final Verification

```bash
# Run all checks one more time
uv run ruff check . && uv run ruff format . && uv run mypy .

# Run tests
uv run pytest tools/gmail/tests/

# Verify commit
git log -1 --stat
```

---

## Rollback Plan

If issues are discovered after migration:

### Quick Rollback (Git Reset)

```bash
# If changes not yet pushed
git reset --hard HEAD~1

# Verify rollback
git status
# Should be clean, back to pre-migration state
```

### Selective Rollback (Git Revert)

```bash
# If changes already pushed to remote
git revert HEAD

# Add explanatory message
git commit --amend
```

### Manual Rollback

If automated rollback fails:

1. **Restore shared modules:**
   ```bash
   git mv tools/_shared/* tools/gmail/src/shared/
   ```

2. **Revert import changes:**
   - Gmail: Change `from tools._shared` back to `from ...shared`
   - Others: Change `from tools._shared` back to `from tools.gmail.src.shared`

3. **Test thoroughly:**
   ```bash
   uv run pytest tools/gmail/tests/
   uv run gmail-collect --help
   ```

---

## Post-Migration Validation

### Success Criteria

- [ ] All 16 files updated correctly
- [ ] No import errors in any tool
- [ ] All console scripts work: `--help` flag
- [ ] All console scripts work: `--dry-run` flag
- [ ] All tests pass: `pytest tools/gmail/tests/`
- [ ] Type checking passes: `mypy .`
- [ ] Linting passes: `ruff check . && ruff format .`
- [ ] No references to old path: `grep -r "gmail/src/shared"`
- [ ] Git history preserved: `git log --follow tools/_shared/config.py`
- [ ] Documentation updated and accurate

### Monitoring Post-Deployment

For the first week after merge:

1. **Monitor for import errors** in tool execution
2. **Watch for** any remaining references to old path
3. **Collect feedback** from tool users
4. **Document any issues** in GitHub issues

---

## Appendix A: File Manifest

### Moved Files (8 files, 2,146 LOC)

| Original Path | New Path | LOC |
|--------------|----------|-----|
| `tools/gmail/src/shared/__init__.py` | `tools/_shared/__init__.py` | 65 |
| `tools/gmail/src/shared/config.py` | `tools/_shared/config.py` | 201 |
| `tools/gmail/src/shared/exceptions.py` | `tools/_shared/exceptions.py` | 141 |
| `tools/gmail/src/shared/filters.py` | `tools/_shared/filters.py` | 243 |
| `tools/gmail/src/shared/http_client.py` | `tools/_shared/http_client.py` | 151 |
| `tools/gmail/src/shared/output.py` | `tools/_shared/output.py` | 300 |
| `tools/gmail/src/shared/security.py` | `tools/_shared/security.py` | 523 |
| `tools/gmail/src/shared/storage.py` | `tools/_shared/storage.py` | 522 |

### Updated Python Files (13 files)

| File | Changes | Complexity |
|------|---------|-----------|
| `tools/gmail/src/collectors/gmail/collector.py` | 10 imports | Medium |
| `tools/gmail/src/collectors/gmail/config.py` | 3 imports | Low |
| `tools/gmail/src/collectors/gmail/auth.py` | 2 imports | Low |
| `tools/gmail/src/collectors/gmail/send_cli.py` | 2 imports | Low |
| `tools/gmail/src/collectors/gmail/cli.py` | 1 import | Low |
| `tools/reddit/src/collectors/reddit/collector.py` | 6 imports | Low |
| `tools/reddit/src/collectors/reddit/config.py` | 1 import | Low |
| `tools/reddit/src/collectors/reddit/cli.py` | 1 import | Low |
| `tools/stackexchange/src/collectors/stackexchange/collector.py` | 6 imports | Low |
| `tools/stackexchange/src/collectors/stackexchange/config.py` | 3 imports | Low |
| `tools/stackexchange/src/collectors/stackexchange/cli.py` | 2 imports | Low |
| `tools/web_articles/src/collectors/web_articles/config.py` | 1 import | Low |
| `tools/gmail/tests/test_config.py` | 1 import | Low |

### Updated Configuration Files (1 file)

| File | Changes |
|------|---------|
| `pyproject.toml` | 1 mypy override path |

### Updated Documentation Files (3 files)

| File | References Updated |
|------|-------------------|
| `tools/README.md` | ~10 references |
| `tools/INTEGRATION_GUIDE.md` | ~2 references |
| `tools/CLAUDE.md` | ~5 references + notion-todoist removal |

---

## Appendix B: Import Pattern Reference

### Before Migration

**Gmail (relative imports):**
```python
from ...shared.config import load_yaml_config
from ...shared.exceptions import ConfigurationValidationError
```

**Reddit, StackExchange, Web Articles (absolute imports):**
```python
from tools.gmail.src.shared.config import load_yaml_config
from tools.gmail.src.shared.exceptions import ConfigurationValidationError
```

### After Migration

**All tools (standardized absolute imports):**
```python
from tools._shared.config import load_yaml_config
from tools._shared.exceptions import ConfigurationValidationError
```

---

## Appendix C: Team Communication Template

### Daily Standup Template

```
Team: [Team Name]
Status: [In Progress / Blocked / Complete]
Files Updated: [X/Y completed]
Issues Encountered: [None / Description]
Blockers: [None / Description]
ETA: [Time remaining]
```

### Integration Checklist

Before merging your changes:

- [ ] All assigned files updated
- [ ] Local tests pass
- [ ] Console scripts work (`--help` flag)
- [ ] No references to old path in your files
- [ ] Changes committed to feature branch
- [ ] Pull request created with detailed description
- [ ] Reviewers assigned
- [ ] CI/CD pipeline passes

---

## Appendix D: Troubleshooting

### Common Issues

#### Issue 1: Import Error After Migration

**Symptom:**
```
ImportError: No module named 'tools.gmail.src.shared'
```

**Cause:** File not updated with new import path

**Solution:**
```bash
# Find remaining old imports
grep -r "tools\.gmail\.src\.shared" tools/ --include="*.py"

# Update the file manually
```

#### Issue 2: Relative Import Errors in Gmail

**Symptom:**
```
ImportError: attempted relative import beyond top-level package
```

**Cause:** Still using `from ...shared` instead of absolute import

**Solution:**
Change to absolute import: `from tools._shared`

#### Issue 3: Test Failures

**Symptom:**
```
pytest: ImportError in test_config.py
```

**Cause:** Test file not updated with new import path

**Solution:**
Update `tools/gmail/tests/test_config.py` with new path

#### Issue 4: Mypy Errors

**Symptom:**
```
error: Cannot find implementation or library stub for module named "tools.gmail.src.shared.http_client"
```

**Cause:** `pyproject.toml` mypy override not updated

**Solution:**
Update line 123 in `pyproject.toml`:
```toml
module = "tools._shared.http_client"
```

---

## Document Metadata

**Version:** 1.0
**Created:** 2025-10-30
**Authors:** Platform Team + Claude Code
**Status:** Ready for Execution
**Last Updated:** 2025-10-30

**Related Documents:**
- `tools/_shared/CURRENT_STATE.md` - Pre-migration codebase snapshot
- `tools/README.md` - Tools directory overview
- `tools/INTEGRATION_GUIDE.md` - Pattern for adding new tools

**Success Metrics:**
- Zero breaking changes for end users
- All tests pass
- All tools remain functional
- Code quality metrics maintained (mypy, ruff)
- Git history preserved

---

**END OF REFACTORING PLAN**
