# Claude Code Settings for Haconiwa Project

## Available Commands

### ripgrep (rg)
Fast file content search tool is available at:
```bash
~/bin/rg
```

Example usage:
```bash
~/bin/rg "search_pattern" /path/to/search
~/bin/rg "function_name" src/ -A5 -B5
```

## Lint and Type Check Commands

When making code changes, always run:
```bash
# Python linting
ruff check src/

# Type checking
mypy src/
```