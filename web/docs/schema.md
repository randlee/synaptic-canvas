# Plugin Diagram Schema

This document defines the data schema for plugin workflow diagrams.

## Overview

Each plugin's workflow is defined as a directed graph with:
- **Nodes** — States in the workflow (entry, agents, gates, outcomes)
- **Edges** — Transitions between states

## Node Schema

```typescript
interface Node {
  // Required
  id: string                    // Unique identifier
  label: string                 // Display name
  type: NodeType                // Node category

  // Optional
  subtitle?: string             // Secondary label (e.g., agent name)
  details?: NodeDetails         // Expanded information
}

type NodeType = 'entry' | 'agent' | 'gate' | 'success' | 'error'

interface NodeDetails {
  description?: string          // Human-readable explanation

  // For agents
  input?: object                // Input schema
  output?: object               // Output schema

  // For gates
  gatePrompt?: GatePrompt       // JSON prompt structure
  gateResponse?: object         // Expected response schema
  skipCondition?: string        // When this gate is skipped

  // Context
  context?: string[]            // Fields added to workflow context

  // Errors
  errorCodes?: ErrorCode[]      // Possible errors at this stage
}

interface GatePrompt {
  type: 'confirmation_gate' | 'decision_gate'
  gate_id: string
  message: string
  context?: object
  options: Record<string, string>
}

interface ErrorCode {
  code: string                  // e.g., "GH.AUTH.REQUIRED"
  recoverable: boolean
  action: string                // Suggested recovery action
}
```

## Edge Schema

```typescript
interface Edge {
  from: string                  // Source node ID
  to: string                    // Target node ID
  label?: string                // Transition label
}
```

## Example: sc-github-issue

```json
{
  "nodes": [
    {
      "id": "command",
      "label": "/sc-github-issue",
      "subtitle": "--fix --issue 42",
      "type": "entry",
      "details": {
        "description": "Entry point for GitHub issue workflow",
        "input": {
          "flags": {
            "--fix": "boolean",
            "--issue": "number|URL"
          }
        },
        "context": ["flags", "repo", "operation"]
      }
    },
    {
      "id": "intake",
      "label": "Intake Agent",
      "subtitle": "sc-github-issue-intake",
      "type": "agent",
      "details": {
        "description": "Fetches issue details from GitHub",
        "input": { "issue_number": "number" },
        "output": { "issue": "{ number, title, body, labels }" },
        "context": ["issue"],
        "errorCodes": [
          { "code": "GH.ISSUE.NOT_FOUND", "recoverable": false, "action": "Verify issue number" }
        ]
      }
    },
    {
      "id": "gate1",
      "label": "Confirm Fix",
      "type": "gate",
      "details": {
        "gatePrompt": {
          "type": "confirmation_gate",
          "gate_id": "fix_confirmation",
          "message": "Ready to fix issue #42?",
          "options": { "proceed": "Create worktree", "cancel": "Abort" }
        },
        "gateResponse": { "proceed": true },
        "skipCondition": "--yolo"
      }
    }
  ],
  "edges": [
    { "from": "command", "to": "intake", "label": "parse flags" },
    { "from": "intake", "to": "gate1", "label": "issue fetched" },
    { "from": "gate1", "to": "worktree", "label": "proceed" },
    { "from": "gate1", "to": "abort", "label": "cancel" }
  ]
}
```

## Visual Styling

Nodes are styled based on type:

| Type | Fill Color | Border Color | Border Style |
|------|------------|--------------|--------------|
| entry | `#e1f5ff` | `#0ea5e9` | Solid |
| agent | `#fff4e1` | `#f59e0b` | Solid |
| gate | `#f0e1ff` | `#a855f7` | Dashed |
| success | `#e1ffe1` | `#22c55e` | Solid |
| error | `#ffe1e1` | `#ef4444` | Solid |

## Layout Algorithm

The visualizer uses a hierarchical layout:

1. **Level assignment** — BFS from entry nodes
2. **Horizontal positioning** — Distribute nodes evenly per level
3. **Edge routing** — Bezier curves between node centers

## Integration

### In Markdown (VitePress)

```vue
<script setup>
const nodes = [/* node definitions */]
const edges = [/* edge definitions */]
</script>

<PluginFlowVisualizer
  plugin-name="My Plugin"
  :nodes="nodes"
  :edges="edges"
/>
```

### From External JSON

```vue
<script setup>
import flowData from './my-plugin-flow.json'
</script>

<PluginFlowVisualizer
  plugin-name="My Plugin"
  :nodes="flowData.nodes"
  :edges="flowData.edges"
/>
```
