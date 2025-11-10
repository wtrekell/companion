# State File Format Documentation

## Overview

The Gmail collector uses a JSON-based state file to track processed messages and prevent duplicate processing. This document describes the state file schema, fields, and manual repair procedures.

## Location

Default location: `data/gmail_state.json` (relative to token_file directory specified in config)

## Schema

### Root Structure

```json
{
  "processed_messages": {},
  "version": "1.0",
  "_created": "2025-10-27T12:00:00+00:00",
  "_last_updated": "2025-10-27T12:30:00+00:00",
  "_integrity_hash": "abc123..."
}
```

### Fields

#### `processed_messages` (dict)

Maps message IDs to processing records:

```json
{
  "processed_messages": {
    "MESSAGE_ID_1": {
      "actions_applied": ["save", "archive", "label:review"],
      "last_processed": "2025-10-27T12:00:00+00:00"
    },
    "MESSAGE_ID_2": {
      "actions_applied": ["forward:user@example.com"],
      "last_processed": "2025-10-27T12:15:00+00:00"
    }
  }
}
```

**Message Record Fields:**
- `actions_applied` (list[str]): Actions successfully applied to this message
- `last_processed` (str): ISO 8601 timestamp of last processing

**Valid Actions:**
- `save` - Message saved to markdown file
- `archive` - Message archived (INBOX label removed)
- `mark_read` - Message marked as read (UNREAD label removed)
- `label:<name>` - Label added to message
- `remove_label:<name>` - Label removed from message
- `forward:<email>` - Message forwarded to email address
- `delete` - Message moved to trash
- `delete_permanent` - Message permanently deleted

#### `version` (str)

State file format version. Current: `"1.0"`

#### `_created` (str)

ISO 8601 timestamp when state file was first created.

#### `_last_updated` (str)

ISO 8601 timestamp of last state update.

#### `_integrity_hash` (str)

SHA-256 hash of state data (excluding metadata fields starting with `_`) for integrity validation.

## State Management

### Automatic Cleanup

The collector automatically cleans up old state entries:
- Keeps only the 10,000 most recently processed messages
- Sorts by `last_processed` timestamp
- Cleanup occurs during each collection run

### Checkpoint Saves

State is saved:
- Every 10 messages during processing (checkpoint)
- At the end of each rule's collection
- After all rules complete

### Migration

The collector automatically migrates old state formats:

**Legacy Format (list):**
```json
{
  "processed_messages": ["MESSAGE_ID_1", "MESSAGE_ID_2"]
}
```

**Migrated to:**
```json
{
  "processed_messages": {
    "MESSAGE_ID_1": {"actions_applied": ["save"]},
    "MESSAGE_ID_2": {"actions_applied": ["save"]}
  }
}
```

## Manual Repair Procedures

### Corrupted State File

**Symptoms:**
- Collector fails to start with state loading errors
- JSON parsing errors
- Invalid state structure warnings

**Repair Steps:**

1. **Backup existing state:**
   ```bash
   cp data/gmail_state.json data/gmail_state.json.backup
   ```

2. **Validate JSON:**
   ```bash
   python -m json.tool data/gmail_state.json > /dev/null
   ```

3. **If JSON is invalid, create fresh state:**
   ```bash
   echo '{"processed_messages": {}, "version": "1.0"}' > data/gmail_state.json
   ```

4. **If JSON is valid but structure is wrong:**
   ```python
   import json

   # Load and fix structure
   with open("data/gmail_state.json", "r") as f:
       state = json.load(f)

   # Ensure processed_messages is dict
   if isinstance(state.get("processed_messages"), list):
       old_list = state["processed_messages"]
       state["processed_messages"] = {
           msg_id: {"actions_applied": ["save"]}
           for msg_id in old_list
       }

   # Add missing fields
   state.setdefault("version", "1.0")

   # Save fixed state
   with open("data/gmail_state.json", "w") as f:
       json.dump(state, f, indent=2)
   ```

### Reset State (Force Reprocessing)

**Warning:** This will cause all messages to be reprocessed according to current rules.

**To reset completely:**
```bash
rm data/gmail_state.json
```

**To reset specific messages:**
```python
import json

with open("data/gmail_state.json", "r") as f:
    state = json.load(f)

# Remove specific message
if "MESSAGE_ID" in state["processed_messages"]:
    del state["processed_messages"]["MESSAGE_ID"]

with open("data/gmail_state.json", "w") as f:
    json.dump(state, f, indent=2)
```

**To reset specific actions:**
```python
import json

with open("data/gmail_state.json", "r") as f:
    state = json.load(f)

# Remove specific action from message
if "MESSAGE_ID" in state["processed_messages"]:
    actions = state["processed_messages"]["MESSAGE_ID"]["actions_applied"]
    if "archive" in actions:
        actions.remove("archive")

with open("data/gmail_state.json", "w") as f:
    json.dump(state, f, indent=2)
```

### Integrity Hash Mismatch

If integrity validation fails, the collector will:
1. Log a warning
2. Continue with current state data
3. Regenerate hash on next save

**To manually fix:**
```python
import json
import hashlib

with open("data/gmail_state.json", "r") as f:
    state = json.load(f)

# Remove all metadata fields for hashing
hashable_data = {k: v for k, v in state.items() if not k.startswith("_")}

# Calculate new hash
json_string = json.dumps(hashable_data, sort_keys=True, separators=(",", ":"))
new_hash = hashlib.sha256(json_string.encode("utf-8")).hexdigest()

# Update state
state["_integrity_hash"] = new_hash

with open("data/gmail_state.json", "w") as f:
    json.dump(state, f, indent=2)
```

## Performance Considerations

### State File Size

With 10,000 message limit:
- Average size: 1-2 MB
- Maximum size: ~5 MB (with long action lists)

### Read/Write Operations

- State is loaded once at collector initialization
- Updates are atomic (write to temp file, then rename)
- Checkpoint saves every 10 messages prevent data loss

### Concurrency

**Warning:** Running multiple collector instances simultaneously is not supported and may cause:
- Lost state updates
- Race conditions
- Duplicate processing

**Recommended:** Use file locking or orchestration if parallel runs are needed.

## Troubleshooting

### State not persisting

**Check:**
1. File permissions on `data/` directory
2. Disk space availability
3. No filesystem errors in logs

### Duplicate messages being processed

**Possible causes:**
1. State file was deleted or reset
2. Message ID changed (rare)
3. Different actions being applied (expected behavior)

**Solution:**
- Check state file contains message ID
- Verify actions_applied list includes expected actions

### Old messages reappearing

**Cause:** State cleanup removed entries that are still matching rules

**Solution:**
- Adjust rule filters (max_age_days)
- Increase cleanup limit (requires code modification)
- Archive processed messages in Gmail

## Best Practices

1. **Backup state file regularly** if long-term tracking is important
2. **Monitor state file size** - shouldn't grow beyond 5-10 MB
3. **Don't manually edit** unless necessary (use scripts above)
4. **Test rule changes** with `--dry-run` flag before applying
5. **Keep logs** to correlate state changes with collector runs

## Related Documentation

- Configuration: `tools/gmail/settings/gmail.yaml`
- Error codes: `tools/gmail/docs/ERROR_CODES.md`
- Architecture: `tools/gmail/README.md`
