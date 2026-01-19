# sc-roslyn-diff Use Cases

## 1) Compare two files

```
/sc-diff compare Calculator.cs and Calculator.New.cs --files ./Calculator.cs,./Calculator.New.cs
```

Outcome: JSON diff output for AI consumption, with semantic changes for C# files.

## 2) Compare two folders

```
/sc-diff compare before and after folders --folders ./samples/before,./samples/after
```

Outcome: Directory-wide diff using relative paths to pair files. Missing files are treated as empty to surface add/remove changes.

## 3) Generate HTML report

```
/sc-diff generate HTML report --files ./old.cs,./new.cs --html
```

Outcome: HTML report written per pair and opened in the default browser if differences are found.

## 4) Large batch with splitting

```
/sc-diff compare large trees --folders ./old,./new --allow-large --files-per-agent 10
```

Outcome: The diff is split into multiple sub-agents, each handling up to 10 file pairs. The top-level agent aggregates counts and only returns non-identical diffs.

## 5) Ignore whitespace and tune context

```
/sc-diff compare text with whitespace changes --files ./old.txt,./new.txt --mode line --ignore-whitespace --context 6
```

Outcome: Line diff ignores whitespace-only changes and uses 6 lines of context.

## 6) PR diff (GitHub)

Use the `sc-git-diff` agent to compare a PR by URL or number. It resolves base/head refs, collects changed files, and runs semantic diffs.

## 7) PR diff (Azure DevOps)

`sc-git-diff` can use `az repos pr show` to resolve base/head refs. The resolved org/project/repo are cached in `.sc/roslyn-diff/settings.json`.
