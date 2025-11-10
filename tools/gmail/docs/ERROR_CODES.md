# Error Codes and Troubleshooting Guide

## Exit Codes

The Gmail collector uses standard Unix exit codes:

| Exit Code | Meaning | Common Causes |
|-----------|---------|---------------|
| 0 | Success | Collection completed without errors |
| 1 | General Error | Configuration error, authentication failure, or runtime error |

## Error Messages

### Authentication Errors

#### `AuthenticationFailureError: Gmail authentication failed`

**Cause:** Unable to authenticate with Gmail API.

**Possible Issues:**
1. Missing or invalid `GMAIL_TOKEN` environment variable
2. Expired OAuth token
3. Invalid credentials file
4. Network connectivity issues

**Troubleshooting:**
```bash
# Check if GMAIL_TOKEN is set
echo $GMAIL_TOKEN

# Verify token format (should be JSON)
echo $GMAIL_TOKEN | python -m json.tool

# Check credentials file permissions (should be 0600)
ls -la data/gmail_credentials.json

# Test with fresh authentication
rm data/gmail_token.json
gmail-collect --config tools/gmail/settings/gmail.yaml
```

**Solution:**
- Ensure GMAIL_TOKEN environment variable is set in `.env` file
- Regenerate OAuth token if expired
- Check credentials file exists and has correct permissions
- Verify network connectivity to Google APIs

---

#### `AuthenticationFailureError: Credential file has insecure permissions`

**Cause:** Token or credentials file permissions allow access by group or others.

**Required Permissions:** `0600` (read/write by owner only)

**Fix:**
```bash
chmod 600 data/gmail_token.json
chmod 600 data/gmail_credentials.json
```

---

#### `InputValidationError: GMAIL_TOKEN format is invalid`

**Cause:** GMAIL_TOKEN environment variable is not valid JSON or base64-encoded JSON.

**Expected Formats:**
1. Direct JSON: `{"token": "...", "refresh_token": "...", ...}`
2. Base64-encoded JSON: `eyJ0b2tlbiI6IC4uLn0=`

**Fix:**
```bash
# Validate JSON format
echo $GMAIL_TOKEN | python -m json.tool

# If base64 encoded, decode and validate
echo $GMAIL_TOKEN | base64 -d | python -m json.tool
```

---

### Configuration Errors

#### `ConfigurationValidationError: Missing required 'output_dir' field`

**Cause:** Configuration file missing required field.

**Required Fields:**
- `output_dir`
- `token_file` (or GMAIL_TOKEN env var)

**Fix:**
Add missing fields to `tools/gmail/settings/gmail.yaml`:
```yaml
output_dir: "output/gmail"
token_file: "data/gmail_token.json"
```

---

#### `ConfigurationValidationError: Gmail query contains invalid operators`

**Cause:** Gmail search query uses unsupported operators.

**Valid Operators:**
- `from:`, `to:`, `subject:`, `label:`, `has:`, `is:`, `in:`
- `after:`, `before:`, `newer:`, `older:`
- `category:`, `size:`, `larger:`, `smaller:`
- `filename:`, `cc:`, `bcc:`, `deliveredto:`

**Example Fix:**
```yaml
# Bad
query: "sender:user@example.com"  # 'sender:' is invalid

# Good
query: "from:user@example.com"
```

---

#### `ConfigurationValidationError: batch_size must be positive integer <= 100`

**Cause:** Batch size exceeds Gmail API limits.

**Recommended Value:** `50`

**Fix:**
```yaml
batch_size: 50  # Recommended: 50 (values >100 may cause rate limiting)
```

---

#### `ConfigurationValidationError: Invalid action`

**Cause:** Rule action not recognized.

**Valid Actions:**
- Simple: `save`, `archive`, `mark_read`, `delete`, `delete_permanent`
- Parametrized: `label:<name>`, `remove_label:<name>`, `forward:<email>`

**Example Fix:**
```yaml
# Bad
actions:
  - "trash"  # Invalid action

# Good
actions:
  - "delete"  # Moves to trash
  - "delete_permanent"  # Permanently deletes
```

---

### Network Errors

#### `NetworkConnectionError: API call failed after X attempts`

**Cause:** Gmail API request failed after all retry attempts.

**Common Causes:**
1. Network connectivity issues
2. Gmail API rate limiting
3. Temporary Gmail service issues
4. Firewall blocking Google API access

**Troubleshooting:**
```bash
# Test network connectivity
ping www.googleapis.com
curl -I https://gmail.googleapis.com

# Check rate limiting
# Wait 60 seconds and retry

# Verify firewall rules allow googleapis.com
```

**Solution:**
- Check internet connection
- Reduce `batch_size` in config (default: 50)
- Increase `rate_limit_seconds` (default: 1.0)
- Wait if rate limited (429 status code)

---

#### `RateLimitExceededError: Gmail API rate limit exceeded`

**Cause:** Too many requests to Gmail API.

**Gmail API Limits:**
- 250 quota units per second per user
- 1 billion quota units per day

**Fix Configuration:**
```yaml
rate_limit_seconds: 2.0  # Increase delay between requests
batch_size: 25           # Reduce messages per request
```

**Temporary Solution:**
```bash
# Wait 60 seconds
sleep 60
gmail-collect --config tools/gmail/settings/gmail.yaml
```

---

### State Management Errors

#### `StateManagementError: Failed to save Gmail collector state`

**Cause:** Cannot write to state file.

**Common Issues:**
1. Disk space full
2. No write permissions on data directory
3. File system error

**Troubleshooting:**
```bash
# Check disk space
df -h

# Check directory permissions
ls -la data/

# Check file permissions
ls -la data/gmail_state.json

# Verify write access
touch data/test_write && rm data/test_write
```

**Fix:**
```bash
# Fix permissions
chmod 755 data/
chmod 644 data/gmail_state.json

# Free disk space if needed
```

---

#### `StateManagementError: State file contains invalid data structure`

**Cause:** State file corrupted or wrong format.

**Solution:**
See `STATE_FILE_FORMAT.md` for manual repair procedures.

**Quick Fix:**
```bash
# Backup current state
cp data/gmail_state.json data/gmail_state.json.backup

# Reset state (will reprocess all messages)
rm data/gmail_state.json
```

---

### Content Processing Errors

#### `ContentProcessingError: Failed to process message`

**Cause:** Error processing individual message.

**Behavior:** Collector logs error but continues with next message.

**Common Causes:**
1. Malformed email content
2. Unsupported charset
3. Attachment download failure
4. Markdown generation error

**Investigation:**
```bash
# Run with verbose logging
gmail-collect --config tools/gmail/settings/gmail.yaml --verbose

# Check logs for specific message ID
grep "MESSAGE_ID" logs/gmail.log
```

---

### Security Errors

#### `PathTraversalError: Path traversal detected`

**Cause:** Input contains path traversal sequences.

**Blocked Patterns:**
- `../` (parent directory)
- Paths resolving outside working directory
- Sensitive system paths (`/etc`, `/sys`, `/proc`, etc.)

**This is expected behavior** - the collector is preventing a security vulnerability.

---

#### `InputValidationError: Invalid email format`

**Cause:** Email address validation failed.

**Common Issues:**
1. Missing @ symbol
2. Invalid domain format
3. Prohibited characters (`<`, `>`, `"`, etc.)
4. Suspicious content patterns

**Example:**
```yaml
# Bad
forward:user<script>@example.com  # Contains <>

# Good
forward:user@example.com
```

---

#### `ConfigurationInjectionError: Nested environment variable reference detected`

**Cause:** Configuration contains nested `${VAR}` references.

**Security:** Nested variables are blocked to prevent injection attacks.

**Example:**
```yaml
# Bad - nested ${VAR}
value: "${OUTER_${INNER_VAR}}"

# Good - single level
value: "${MY_VAR}"
```

---

## Warning Messages

### `Skipping attachment: size exceeds limit`

**Cause:** Attachment larger than max_attachment_size (default: 25MB).

**Behavior:** Attachment is skipped, message is still saved.

**To Change Limit:**
Add to `config.py` dataclass:
```python
max_attachment_size: int = 50 * 1024 * 1024  # 50MB
```

---

### `Invalid charset specified, falling back to utf-8`

**Cause:** Email specifies unknown or invalid charset.

**Behavior:** Collector uses UTF-8 as fallback.

**Impact:** Usually minimal - UTF-8 handles most content correctly.

---

### `Cleaned up X old message entries from state`

**Cause:** State file exceeded 10,000 message limit.

**Behavior:** Oldest messages removed from state tracking.

**Impact:** Very old messages might be reprocessed if they match rules again.

**To Prevent:** Archive processed messages in Gmail.

---

## Common Scenarios

### First Run Issues

**Problem:** "Gmail authentication failed" on first run

**Solution:**
1. Ensure `GMAIL_TOKEN` is set in `.env`
2. Or ensure `credentials_file` exists
3. Run authentication flow interactively

```bash
# Set up environment
cp .env.example .env
# Edit .env and add GMAIL_TOKEN

# First run
gmail-collect --config tools/gmail/settings/gmail.yaml
```

---

### Rate Limiting

**Symptoms:**
- "429 Too Many Requests" errors
- Slow collection performance
- API call failures

**Solutions:**
```yaml
# Option 1: Increase delay
rate_limit_seconds: 2.0

# Option 2: Reduce batch size
batch_size: 25

# Option 3: Reduce max_messages per rule
rules:
  - name: "my-rule"
    max_messages: 50  # Reduce from 100
```

---

### Duplicate Processing

**Problem:** Same messages processed multiple times

**Causes:**
1. State file deleted
2. State file corrupted
3. Different actions being applied (expected)

**Check State:**
```python
import json

with open("data/gmail_state.json") as f:
    state = json.load(f)

# Check if message is tracked
message_id = "YOUR_MESSAGE_ID"
if message_id in state["processed_messages"]:
    print(state["processed_messages"][message_id])
else:
    print("Message not in state")
```

---

### Memory Issues

**Symptoms:**
- Collector crashes with "MemoryError"
- System becomes unresponsive

**Solutions:**
```yaml
# Reduce batch size
batch_size: 10

# Reduce max_messages per rule
rules:
  - name: "my-rule"
    max_messages: 25

# Disable attachment saving
rules:
  - name: "my-rule"
    save_attachments: false
```

---

## Getting Help

### Debug Mode

```bash
gmail-collect --config tools/gmail/settings/gmail.yaml --verbose
```

### Dry Run

Test configuration without making changes:
```bash
gmail-collect --config tools/gmail/settings/gmail.yaml --dry-run --verbose
```

### Log Analysis

Key information to include when reporting issues:
1. Full error message and stack trace
2. Gmail collector version
3. Configuration file (redact sensitive data)
4. Output from `--verbose` flag
5. State file size and structure

### Related Documentation

- Configuration: `tools/gmail/settings/gmail.yaml`
- State file format: `tools/gmail/docs/STATE_FILE_FORMAT.md`
- Architecture: `tools/gmail/README.md`
