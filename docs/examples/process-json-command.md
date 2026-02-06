---
name: process-json
description: Process JSON data with json-processor subagent (supports --background and --foreground flags)
aliases: [pjson]
---

# Command Logic

This unified command handles both synchronous and asynchronous JSON processing based on user-provided flags.

## Steps

1. **Parse Arguments**:
   - Check for `--background` or `--bg` flag → set `run_in_background: true`
   - Check for `--foreground` or `--fg` flag → set `run_in_background: false`
   - If no flag provided → default to foreground mode
   - Extract remaining arguments as JSON data

2. **Validate Input**:
   - Ensure JSON data is provided after flags
   - If empty: return error message with usage instructions

3. **Invoke Subagent**:

   **Tool Invocation Template:**
   ```xml
   <invoke name="Task">
   <parameter name="subagent_type">json-processor</parameter>
   <parameter name="description">Transform JSON data</parameter>
   <parameter name="prompt">Process the following JSON data:

   <input_json>
   ```json
   $JSON_DATA
   ```
   </input_json>

   Apply any transformations or validations as needed.</parameter>
   <parameter name="run_in_background">$RUN_IN_BACKGROUND</parameter>
   </invoke>
   ```

   Where:
   - `$JSON_DATA` = JSON extracted from arguments (after flag removal)
   - `$RUN_IN_BACKGROUND` = `true` if --background flag detected, `false` otherwise

4. **Respond to User**: Use appropriate template based on mode

## Response Templates

### Foreground Mode (--foreground or no flag)

```
✓ JSON processing complete

[Display the <output_json> content from agent response]

💡 Tip: Use --background flag for async processing of large datasets
```

### Background Mode (--background)

```
⏳ Background task launched: $TASK_ID

Monitor progress:
  • Read output: Read $OUTPUT_FILE
  • Stream logs: tail -f $OUTPUT_FILE
  • List all tasks: /tasks

Results will be available in <output_json> tags when complete.
```

### Error Cases

**No JSON data provided:**
```
❌ Error: No JSON data provided

Usage: /process-json [--background|--foreground] <json_data>

Examples:
  /process-json {"user": "alice", "action": "login"}
  /process-json --background {"batch": [1,2,3,4,5]}
  /process-json --fg {"status": "active"}
  /pjson --bg {"large_dataset": [...]}
```

**Conflicting flags:**
```
❌ Error: Cannot specify both --background and --foreground

Please use one mode or omit flags (defaults to foreground).
```

## Argument Parsing Logic

Example pseudo-logic for flag detection:

```
if "--background" in $ARGUMENTS or "--bg" in $ARGUMENTS:
    run_mode = "background"
    remove flag from arguments
elif "--foreground" in $ARGUMENTS or "--fg" in $ARGUMENTS:
    run_mode = "foreground"
    remove flag from arguments
else:
    run_mode = "foreground"  # default

json_data = remaining arguments after flag removal
```

## Usage Examples

**Foreground (immediate results):**
```bash
/process-json {"id": 123, "name": "test"}
/process-json --foreground {"status": "active"}
/pjson {"key": "value"}
```

**Background (async processing):**
```bash
/process-json --background {"batch_id": 456, "items": [1,2,3]}
/process-json --bg {"large_dataset": [...]}
/pjson --bg {"data": [...]}
```

## When to Use Each Mode

**Foreground (default):**
- Small to medium JSON datasets
- Need immediate results
- Interactive workflows

**Background (--background):**
- Large JSON datasets
- Long-running transformations
- Want to continue other work during processing
