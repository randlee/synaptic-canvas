---
name: process-json-background
description: Process JSON data asynchronously in the background
aliases: [pjson-bg]
---

# Task

Use the `Task` tool to invoke the `json-processor` subagent in background mode.

## Tool Invocation

```xml
<invoke name="Task">
<parameter name="subagent_type">json-processor</parameter>
<parameter name="description">Transform JSON data</parameter>
<parameter name="prompt">Process the following JSON data:

<input_json>
```json
$ARGUMENTS
```
</input_json>

Apply any transformations or validations as needed.</parameter>
<parameter name="run_in_background">true</parameter>
</invoke>
```

**Note:** Setting `run_in_background: true` allows the user to continue working while processing occurs.

## Response Template

After launching the background task, inform the user:

```
⏳ Background task launched: $TASK_ID

Monitor progress:
  • Read output: Read $OUTPUT_FILE
  • Stream logs: tail -f $OUTPUT_FILE
  • List all tasks: /tasks

Results will be available in <output_json> tags when processing completes.
You can continue working while this runs in the background.
```

## Checking Results

The user can retrieve results later using:
- `Read $OUTPUT_FILE` - View complete output
- `tail -f $OUTPUT_FILE` - Stream updates in real-time
- The output will contain `<output_json>` tags with the processed JSON

## Error Handling

The json-processor subagent returns structured errors in the output file:
- Check the output file for `{"status": "error", "detail": "..."}` messages
- Background tasks may timeout - monitor the output file for completion

## Usage Examples

```bash
/process-json-background {"batch_id": 789, "items": [1,2,3,4,5]}
/pjson-bg {"large_dataset": [...]}
```

## When to Use

- Large JSON datasets
- Long-running transformations
- When you want to continue other work during processing
- Batch operations that don't need immediate results
