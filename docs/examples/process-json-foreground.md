---
name: process-json-foreground
description: Process JSON data synchronously and display results immediately
aliases: [pjson-fg]
---

# Task

Use the `Task` tool to invoke the `json-processor` subagent synchronously.

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
</invoke>
```

**Note:** `run_in_background` parameter is omitted (defaults to false).

## Response Template

Wait for the subagent to complete, then display the `<output_json>` result:

```
✓ JSON processing complete

[Display the <output_json> content from agent response]

💡 Tip: For async processing of large datasets, use /process-json-background
```

## Error Handling

The json-processor subagent returns structured errors:
- If input is invalid JSON: `{"status": "error", "detail": "JSON parse error"}`
- Display error responses clearly to the user

## Usage Examples

```bash
/process-json-foreground {"user_id": 123, "action": "create"}
/pjson-fg {"status": "active", "count": 42}
```

## When to Use

- Small to medium JSON datasets
- When you need immediate results
- Interactive data transformations
- When you want to see output before continuing work
