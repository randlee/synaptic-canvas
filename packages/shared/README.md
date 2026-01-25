# sc-shared

Internal shared scripts copied into each package to keep agent/script utilities consistent without cross-package imports.

## What it provides

### Allowed-path validation
Build an allowlist from runtime settings and validate user-supplied paths.

```python
from sc_shared import load_runtime_context, validate_allowed_path

ctx = load_runtime_context()
repo_root = validate_allowed_path("/path/to/repo", ctx.allowed_dirs, label="repo_root")
```

### Runtime context helpers
Resolve project directory and find a git root.

```python
from sc_shared import get_project_dir, find_repo_root

project_dir = get_project_dir()
repo_root = find_repo_root()
```

Validate that a path is a real git repository:

```python
from sc_shared import is_git_repo

if not is_git_repo(repo_root):
    raise SystemExit("Not a git repo")
```

### Hook JSON validation
Extract JSON embedded in tool commands and validate via pydantic.

```python
import json
import sys
from pydantic import BaseModel
from sc_shared import validate_hook_json

class Params(BaseModel):
    branch: str
    base: str

payload = json.load(sys.stdin)
params = validate_hook_json(payload, Params)
```

### Agent Runner helpers
Validate agent files against registry and build Task tool prompts.

```python
from sc_shared import AgentInvokeRequest, invoke_agent_runner

req = AgentInvokeRequest(agent="sc-worktree-create", params={"branch": "feature-x"})
result = invoke_agent_runner(req)
print(result.task_prompt)
```
