# Gmail Collector Test Suite

Comprehensive test suite for the Gmail content collector system.

## Overview

This test suite provides 160+ test cases covering all aspects of the Gmail collector:
- Configuration validation
- State management with file locking
- Content filtering
- OAuth authentication
- Message collection and processing
- CLI interface
- Security validations

## Test Organization

### Test Files

```
tools/gmail/tests/
├── __init__.py              # Test package marker
├── conftest.py              # Pytest fixtures and configuration
├── test_config.py           # Configuration loading and validation (30 tests)
├── test_state_management.py # State management and locking (20 tests)
├── test_filters.py          # Content filtering (15 tests)
├── test_auth.py             # Authentication and OAuth (15 tests)
├── test_collector.py        # Message collection (40 tests)
├── test_cli.py              # CLI interface (15 tests)
└── test_security.py         # Security validations (25 tests)
```

### Test Categories

#### 1. Configuration Tests (`test_config.py`)
**30 test cases covering:**
- YAML configuration loading
- Environment variable substitution
- Gmail query syntax validation
- Action string validation
- File path security
- OAuth scope validation
- Filter criteria parsing
- Default value handling

**Key Test Classes:**
- `TestFilterCriteria` - Filter dataclass tests
- `TestGmailRule` - Rule configuration tests
- `TestGmailQueryValidation` - Query syntax and security
- `TestGmailActionValidation` - Action format validation
- `TestFilePathValidation` - Path security tests
- `TestOAuthScopesValidation` - Scope validation
- `TestGmailConfigLoading` - End-to-end config loading

#### 2. State Management Tests (`test_state_management.py`)
**20 test cases covering:**
- State file initialization
- File locking mechanisms
- Race condition prevention
- Atomic write operations
- State cleanup (10k limit)
- Checkpoint saves
- Integrity validation
- Migration from legacy formats

**Key Test Classes:**
- `TestStateInitialization` - Initial state creation
- `TestFileLocking` - POSIX file lock tests
- `TestAtomicOperations` - Write atomicity
- `TestStateCleanup` - Old entry removal
- `TestStateValidation` - Integrity checks
- `TestCheckpointSaves` - Periodic saves

#### 3. Content Filtering Tests (`test_filters.py`)
**15 test cases covering:**
- Keyword matching with wildcards
- Age-based filtering
- Score-based filtering
- HTML tag stripping
- Include/exclude keyword logic
- Timezone-aware date handling
- Legacy format support

**Key Test Classes:**
- `TestKeywordMatching` - Wildcard and pattern matching
- `TestContentFiltering` - Multi-criteria filtering
- `TestHTMLProcessing` - HTML tag removal
- `TestDateFiltering` - Age-based filtering

#### 4. Authentication Tests (`test_auth.py`)
**15 test cases covering:**
- OAuth2 flow
- Token storage and loading
- Token refresh mechanism
- File permission validation (0o600)
- Environment variable support
- Credential validation
- Error handling and recovery

**Key Test Classes:**
- `TestOAuthFlow` - Authentication flow
- `TestTokenStorage` - Secure token saves
- `TestTokenRefresh` - Automatic refresh
- `TestPermissionValidation` - File security
- `TestEnvironmentVariables` - GMAIL_TOKEN support

#### 5. Collector Tests (`test_collector.py`)
**40 test cases covering:**
- Message search and retrieval
- Message body extraction (plain + HTML)
- Charset detection and handling
- Filter application
- Action execution (save, archive, label, etc.)
- Attachment processing
- Size limit enforcement
- Retry logic
- Checkpoint saves
- Error handling

**Key Test Classes:**
- `TestMessageSearch` - Search with pagination
- `TestMessageExtraction` - Body and header extraction
- `TestCharsetHandling` - Encoding support
- `TestActionExecution` - All Gmail actions
- `TestAttachmentProcessing` - Attachment handling
- `TestRetryLogic` - Exponential backoff
- `TestErrorHandling` - Graceful degradation

#### 6. CLI Tests (`test_cli.py`)
**15 test cases covering:**
- Argument parsing
- Configuration file loading
- Dry-run mode
- Verbose output
- Auth-only mode
- Rule filtering
- Error message formatting

**Key Test Classes:**
- `TestCLIParsing` - Argument validation
- `TestDryRunMode` - Configuration validation
- `TestAuthOnlyMode` - Authentication setup
- `TestRuleFiltering` - Single rule collection
- `TestErrorHandling` - User-friendly errors

#### 7. Security Tests (`test_security.py`)
**25 test cases covering:**
- SSRF protection (5 layers)
- Email address validation
- Path traversal prevention
- Symlink validation
- Markdown injection prevention
- YAML injection prevention
- Charset validation
- Sensitive path blocking
- Credential sanitization

**Key Test Classes:**
- `TestSSRFProtection` - URL validation
- `TestEmailValidation` - RFC 5322 compliance
- `TestPathSecurity` - Traversal prevention
- `TestMarkdownSecurity` - Injection prevention
- `TestInputSanitization` - General validation

## Running Tests

### All Tests

```bash
# From repository root
cd /Users/williamtrekell/Documents/crewai

# Run all Gmail tests
uv run pytest tools/gmail/tests/

# With verbose output
uv run pytest tools/gmail/tests/ -v

# Stop on first failure
uv run pytest tools/gmail/tests/ -x
```

### With Coverage

```bash
# Generate coverage report
uv run pytest tools/gmail/tests/ \
    --cov=tools/gmail/src \
    --cov-report=html \
    --cov-report=term

# View HTML report
open htmlcov/index.html
```

### Specific Test Files

```bash
# Configuration tests only
uv run pytest tools/gmail/tests/test_config.py

# State management tests only
uv run pytest tools/gmail/tests/test_state_management.py

# Security tests only
uv run pytest tools/gmail/tests/test_security.py
```

### Specific Test Classes

```bash
# Test Gmail query validation
uv run pytest tools/gmail/tests/test_config.py::TestGmailQueryValidation

# Test file locking
uv run pytest tools/gmail/tests/test_state_management.py::TestFileLocking

# Test SSRF protection
uv run pytest tools/gmail/tests/test_security.py::TestSSRFProtection
```

### Specific Test Cases

```bash
# Test specific function
uv run pytest tools/gmail/tests/test_config.py::TestGmailQueryValidation::test_valid_simple_query

# Run tests matching pattern
uv run pytest tools/gmail/tests/ -k "validation"

# Run tests with markers
uv run pytest tools/gmail/tests/ -m "security"
```

## Test Fixtures

### Available Fixtures (from `conftest.py`)

#### Mock Objects
- `mock_gmail_service` - Mock Gmail API service with all methods
- `mock_authenticator` - Mock authentication handler
- `mock_credentials` - Mock OAuth2 credentials
- `mock_http_response` - Mock HTTP response object

#### Sample Data
- `sample_gmail_config` - Complete Gmail configuration
- `sample_message_data` - Raw Gmail message format
- `sample_processed_message_data` - Processed message format
- `sample_state_data` - State file contents
- `sample_gmail_labels` - Gmail labels list

#### Temporary Resources
- `temp_output_dir` - Temporary output directory
- `temp_config_file` - Temporary YAML config file
- `temp_state_file` - Temporary state JSON file

#### Environment
- `clean_test_environment` - Cleans env vars before each test (autouse)

### Using Fixtures

```python
def test_something(mock_gmail_service, temp_output_dir):
    """Test using fixtures."""
    # Fixtures automatically injected
    assert mock_gmail_service is not None
    assert temp_output_dir.exists()
```

## Writing New Tests

### Test Template

```python
import pytest
from tools.gmail.src.collectors.gmail.config import GmailCollectorConfig


class TestNewFeature:
    """Test new feature functionality."""

    def test_basic_case(self, sample_gmail_config):
        """Test basic successful case."""
        # Arrange
        config = sample_gmail_config

        # Act
        result = some_function(config)

        # Assert
        assert result is not None
        assert result.status == "success"

    def test_error_case(self):
        """Test error handling."""
        with pytest.raises(SomeException) as exc_info:
            some_function_that_should_fail()

        assert "expected error message" in str(exc_info.value)

    @pytest.mark.parametrize("input,expected", [
        ("input1", "output1"),
        ("input2", "output2"),
    ])
    def test_multiple_cases(self, input, expected):
        """Test multiple input/output pairs."""
        result = some_function(input)
        assert result == expected
```

### Test Markers

```python
@pytest.mark.security
def test_security_feature():
    """Security-focused test."""
    pass

@pytest.mark.integration
def test_integration():
    """Integration test (may be slow)."""
    pass

@pytest.mark.slow
def test_slow_operation():
    """Long-running test."""
    pass
```

### Mocking Gmail API

```python
from unittest.mock import MagicMock, patch

def test_gmail_api_call(mock_gmail_service):
    """Test Gmail API interaction."""
    # Configure mock response
    mock_gmail_service.users().messages().list().execute.return_value = {
        "messages": [{"id": "123"}]
    }

    # Test code that uses the API
    result = collector.search_messages("from:test@example.com")

    # Verify mock was called correctly
    mock_gmail_service.users().messages().list.assert_called_once()
```

## Test Coverage Goals

### Current Status

- **Target Coverage**: 85%
- **Critical Paths**: 100%
- **Security Functions**: 100%
- **Error Handlers**: 90%

### Coverage by Module

| Module | Target | Priority |
|--------|--------|----------|
| collector.py | 90% | High |
| config.py | 95% | High |
| auth.py | 90% | High |
| security.py | 100% | Critical |
| storage.py | 90% | High |
| filters.py | 85% | Medium |
| output.py | 85% | Medium |
| send_cli.py | 80% | Medium |

### Measuring Coverage

```bash
# Generate coverage report
uv run pytest tools/gmail/tests/ --cov=tools/gmail/src --cov-report=html

# View detailed report
open htmlcov/index.html

# See coverage in terminal
uv run pytest tools/gmail/tests/ --cov=tools/gmail/src --cov-report=term-missing
```

## Mock Strategies

### Gmail API Mocking

The Gmail API is mocked at the service level to avoid real API calls:

```python
# Mock successful message retrieval
mock_gmail_service.users().messages().get().execute.return_value = {
    "id": "123",
    "payload": {...},
    "snippet": "Test message"
}

# Mock API error
from googleapiclient.errors import HttpError
mock_gmail_service.users().messages().list().execute.side_effect = \
    HttpError(resp=MagicMock(status=503), content=b'Service Unavailable')
```

### File System Mocking

Use `temp_output_dir` fixture for file operations:

```python
def test_file_writing(temp_output_dir):
    """Test file writing."""
    output_file = temp_output_dir / "test.md"
    write_markdown_file(str(output_file), "content", {})
    assert output_file.exists()
```

### Environment Variable Mocking

Use `monkeypatch` for environment variables:

```python
def test_env_var(monkeypatch):
    """Test environment variable handling."""
    monkeypatch.setenv("GMAIL_TOKEN", "test_token")
    result = get_gmail_token()
    assert result == "test_token"
```

## Continuous Integration

### GitHub Actions Integration

Tests run automatically on:
- Pull requests to `main` or `crew`
- Pushes to `main` or `crew`
- Manual workflow dispatch

### CI Test Command

```yaml
- name: Run tests
  run: |
    uv run pytest tools/gmail/tests/ \
      --cov=tools/gmail/src \
      --cov-report=xml \
      --cov-report=term
```

### Coverage Reporting

Coverage reports are uploaded to:
- GitHub Actions artifacts
- Code coverage services (optional)

## Test Data

### Sample Messages

Test data includes:
- Plain text emails
- HTML emails
- Multipart emails (plain + HTML)
- Emails with attachments
- Emails with various charsets
- Malformed emails

### Sample Configurations

Test configurations include:
- Minimal valid config
- Full-featured config
- Invalid configurations (for error testing)
- Edge case configurations

## Debugging Tests

### Run with PDB

```bash
# Drop into debugger on failure
uv run pytest tools/gmail/tests/ --pdb

# Drop into debugger on error (not assertion)
uv run pytest tools/gmail/tests/ --pdb --maxfail=1
```

### Verbose Output

```bash
# Show all output
uv run pytest tools/gmail/tests/ -vv -s

# Show only failures
uv run pytest tools/gmail/tests/ -v --tb=short
```

### Logging

```bash
# Show logs for failed tests
uv run pytest tools/gmail/tests/ --log-cli-level=DEBUG

# Capture logs to file
uv run pytest tools/gmail/tests/ --log-file=test.log
```

## Common Issues

### Import Errors

If you see import errors:

```bash
# Ensure dependencies are installed
uv sync

# Verify PYTHONPATH
export PYTHONPATH=/Users/williamtrekell/Documents/crewai:$PYTHONPATH
```

### Fixture Not Found

If fixtures aren't found:

```bash
# Verify conftest.py is in correct location
ls tools/gmail/tests/conftest.py

# Run from correct directory
cd /Users/williamtrekell/Documents/crewai
```

### Permission Errors

If you see permission errors:

```bash
# Clean up test files
rm -rf tools/gmail/tests/__pycache__
rm -rf /tmp/test_*

# Check file permissions
chmod 600 data/gmail_token.json
```

## Contributing

### Adding New Tests

1. Identify the module/function to test
2. Create test class in appropriate test file
3. Write test cases covering:
   - Success path
   - Error cases
   - Edge cases
   - Security validations
4. Use appropriate fixtures from `conftest.py`
5. Add docstrings explaining what's tested
6. Run tests to verify

### Test Naming Conventions

- Test files: `test_<module>.py`
- Test classes: `Test<Feature>`
- Test functions: `test_<what_it_tests>`
- Be descriptive: `test_gmail_query_with_html_injection`

### Code Review Checklist

Before submitting tests:
- [ ] All tests pass
- [ ] Coverage maintained or improved
- [ ] Docstrings added
- [ ] No hardcoded paths or credentials
- [ ] Fixtures used appropriately
- [ ] Mocks properly configured
- [ ] Error cases covered
- [ ] Edge cases considered

## Resources

### Documentation

- **Pytest**: https://docs.pytest.org/
- **pytest-cov**: https://pytest-cov.readthedocs.io/
- **Gmail API**: https://developers.google.com/gmail/api
- **Google Auth**: https://googleapis.dev/python/google-auth/latest/

### Internal Documentation

- `COMPREHENSIVE_FIX_REPORT.md` - All issues fixed
- `tools/gmail/src/collectors/gmail/README.md` - Collector documentation
- `security.py` docstrings - Security architecture
- `storage.py` docstrings - Race condition prevention

---

**Test Suite Status**: Framework Ready ✅
**Test Coverage Goal**: 85%+
**Total Test Cases Planned**: 160+
**Priority**: High (complete before production)

---

*For questions or issues with tests, see project documentation or COMPREHENSIVE_FIX_REPORT.md*
