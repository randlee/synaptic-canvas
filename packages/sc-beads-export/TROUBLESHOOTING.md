# Troubleshooting

## `bd` is not installed

The top-level export script reads live board data with `bd list --json --all --limit 0`. Install `bd`, or use `--board-json` with a captured board export.

## `ModuleNotFoundError: No module named 'markdown'`

Install the package's Python dependency:

```bash
python3 -m pip install markdown
```

## Zip archive was not created

`zip` is optional. If you requested `--package`, ensure `zip` is available on the machine.
