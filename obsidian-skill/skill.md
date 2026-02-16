---
name: managing-obsidian-vault
description: "Executes Obsidian CLI commands to read, write, search notes, manage daily notes, query tags/tasks, and control plugins in an Obsidian vault. Use when the user asks to interact with their Obsidian vault, notes, or anything Obsidian-related."
allowed-tools: "Bash(curl *)"
---

# Obsidian Vault Access

Commands are executed via HTTPS POST to a command service running inside the Obsidian container. Each command is an Obsidian CLI invocation.

## Setup

Before running any command, you need an **endpoint** and a **token**.

### Endpoint

1. Check your memory/notes for a saved Obsidian command API endpoint.
2. If not found, ask the user for the endpoint URL (e.g. `https://obs-api.example.com`).
3. Validate it works: `curl -s -o /dev/null -w "%{http_code}" <endpoint>/` — expect `401` (auth required).
4. Once confirmed, save the endpoint to your memory so you don't have to ask again.

### Token

**Ask the user for a bearer token.** Do not proceed without one.

- `permanent:<token>` — reusable across sessions
- `<token>` — single-use, starts a 10-minute session on first use

Include the same token in every request.

## API

```bash
TOKEN="<token>"
ENDPOINT="<endpoint>"

# Execute commands (POST, JSON body)
curl -s -X POST "$ENDPOINT" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"commands": ["obsidian vault"]}'

# Multiple commands in one request
curl -s -X POST "$ENDPOINT" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"commands": ["obsidian read file=Recipe", "obsidian tags all counts"]}'

# Validate token (GET)
curl -s -H "Authorization: Bearer $TOKEN" "$ENDPOINT"

# Upload non-markdown files to the vault (PUT, raw bytes)
curl -s -X PUT "$ENDPOINT/vault/attachments/image.png" \
  -H "Authorization: Bearer $TOKEN" \
  --data-binary @image.png
```

**POST vs PUT:**
- **POST** — use for **all markdown operations**. CLI commands (`create`, `append`, `prepend`) integrate with Obsidian's file index, trigger plugins, and update caches. Always prefer POST for notes.
- **PUT `/vault/<path>`** — use for **non-markdown files** (images, PDFs, attachments). Content is sent as raw bytes directly to disk. Also available as a **fallback** for markdown if POST fails due to escaping issues.

## Obsidian CLI Syntax

Commands follow the pattern: `obsidian <command> [param=value ...] [flags ...]`

- **Parameters** take values: `file=Recipe`, `content="Hello world"`
- **Flags** are bare switches: `silent`, `overwrite`, `counts`
- Wrap values containing spaces in quotes: `query="meeting notes"`
- Use `\n` for newlines, `\t` for tabs in content

### Targeting files

- `file=<name>` — wikilink-style resolution (by filename, no path/extension needed)
- `path=<path>` — exact path from vault root (e.g. `Notes/Recipe.md`)
- If neither given, defaults to the active file

**Always verify the filepath** before editing or creating files:
- Before editing, use `read` to confirm you have the right file.
- Before creating, use `files` or `search` to verify the destination path and check for existing files.
- When multiple files share the same name, use `path=` instead of `file=` to target the correct one.
- When creating files, specify the full path (e.g. `path=Notes/Subfolder/NewNote.md`) to ensure it lands in the right location.

## Writing Notes

Obsidian uses CommonMark with extensions. Standard markdown works as expected. Key Obsidian-specific syntax:

- **Wikilinks**: `[[Note Name]]` or `[[Note Name|display text]]`
- **Embeds**: `![[Note Name]]` or `![[image.png]]`
- **Highlights**: `==highlighted text==`
- **Comments**: `%%hidden in reading view%%`
- **Tags**: `#tag` or `#nested/tag` (in text or YAML frontmatter)
- **Callouts**: `> [!note]`, `> [!warning]`, `> [!tip]`, etc.
- **Tasks**: `- [ ] incomplete`, `- [x] complete`
- **Block references**: `[[Note^block-id]]`
- **Footnotes**: `[^1]` with `[^1]: text` definition

**Important**: Do not write unclosed XML-style tags like `<open>` without closing them. Obsidian renders HTML inline, so unclosed tags break the rendering of everything after them. Either close the tag (`<open></open>`), escape it (`\<open>`), or wrap it in a code span (`` `<open>` ``).

**Markdown inside HTML is not rendered**: Text like `**bold**` inside `<div>` tags will appear as literal asterisks.

### YAML Frontmatter Pitfalls

- **No inline `#` comments.** YAML treats `#` as a comment delimiter and silently truncates the value. `source: "[[Files]]" # keep this` stores only `Files`. Place instructions in the note body instead.
- **Always quote wikilinks.** Write `source: "[[Note Name]]"`, not `source: [[Note Name]]`. Unquoted `[[` and `]]` break YAML parsing. This applies to both text and list properties.
- **Tags must contain at least one non-numeric character.** `2025` is invalid; `y2025` is valid. Allowed characters: letters, numbers, `_`, `-`, `/`.
- **Property types are not discoverable via CLI.** There is no command to query the type (text, list, number, date, etc.) assigned to a property. Refer to existing notes or templates to determine expected types.

For detailed formatting reference (tables, math, diagrams, properties): See [formatting.md](formatting.md)

## Examples

```bash
# Read a note by name
curl -s -X POST "$ENDPOINT" -H "Authorization: Bearer $TOKEN" \
  -d '{"commands": ["obsidian read file=Recipe"]}'

# Search with context
curl -s -X POST "$ENDPOINT" -H "Authorization: Bearer $TOKEN" \
  -d '{"commands": ["obsidian search query=\"meeting notes\" matches"]}'

# Append task to daily note silently
curl -s -X POST "$ENDPOINT" -H "Authorization: Bearer $TOKEN" \
  -d '{"commands": ["obsidian daily:append content=\"- [ ] Buy groceries\" silent"]}'

# Create note from template
curl -s -X POST "$ENDPOINT" -H "Authorization: Bearer $TOKEN" \
  -d '{"commands": ["obsidian create name=\"Trip to Paris\" template=Travel"]}'
```

## Command Quick Reference

| Category | Commands |
|---|---|
| **Vault** | `vault`, `vaults` |
| **Files** | `read`, `create`, `append`, `prepend`, `open`, `move`, `delete`, `file`, `files`, `folders` |
| **Daily notes** | `daily`, `daily:read`, `daily:append`, `daily:prepend` |
| **Search** | `search query=<text> [matches] [total]` |
| **Tags** | `tags [all] [counts]`, `tag name=<tag>` |
| **Tasks** | `tasks [all] [daily] [todo] [done] [verbose]`, `task ref=<path:line> [toggle] [done]` |
| **Properties** | `properties [file=] [all] [counts]`, `property:set`, `property:read`, `property:remove` |
| **Links** | `backlinks`, `links`, `unresolved`, `orphans`, `deadends` |
| **Outline** | `outline [file=] [format=tree\|md]` |
| **Bookmarks** | `bookmarks`, `bookmark file=<path>` |
| **Templates** | `templates`, `template:read name=<t>`, `template:insert name=<t>` |
| **Diff/History** | `diff [file=] [from=] [to=]`, `history`, `history:read`, `history:restore` |
| **Plugins** | `plugins`, `plugin id=<id>`, `plugin:enable`, `plugin:disable`, `plugin:reload` |
| **Workspace** | `workspace`, `workspaces`, `tabs`, `recents` |
| **Word count** | `wordcount [file=] [words] [characters]` |
| **Developer** | `dev:screenshot path=<f>`, `dev:eval code=<js>`, `dev:console`, `dev:errors` |

**Full command reference with all parameters and flags**: See [reference.md](reference.md)

## Python Helper

For programmatic integrations, see [scripts/obsidian_api.py](scripts/obsidian_api.py) — a standard-library-only helper with two functions:

- `obsidian_cmd(endpoint, token, command, params, flags)` — POST CLI commands. Handles all shlex escaping (only `\` and `"` need it; newlines, `$`, `` ` ``, unicode pass through safely). Rejects null bytes.
- `obsidian_put(endpoint, token, vault_path, content)` — PUT raw bytes to vault. No escaping needed.

```python
from obsidian_api import obsidian_cmd, obsidian_put

# Read a note
obsidian_cmd(EP, TK, "read", params={"file": "Recipe"})

# Create markdown (always use POST for notes)
obsidian_cmd(EP, TK, "create",
    params={"name": "Trip", "content": '---\ntags: [travel]\n---\n# Trip\nNotes.'})

# Upload image (use PUT for non-markdown files)
with open("photo.png", "rb") as f:
    obsidian_put(EP, TK, "attachments/photo.png", f.read())
```

## Troubleshooting

- **No output**: Obsidian app must be running inside the container.
- **401**: Token invalid or session expired. Ask user for a new token.
- **Timeout**: Vault container may be down.
