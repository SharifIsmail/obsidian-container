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

## First Use: Understand the Vault

On your first interaction with a vault, **read the vault's README or equivalent guide** (e.g. `obsidian read file=README`) to understand the vault's rules, conventions, and structure. Look for:

- Folder organization and naming conventions
- Tagging schemes and property conventions
- Templates in use
- Any rules or preferences the user has documented

**Follow existing conventions consistently.** Match the folder structure, naming patterns, frontmatter format, and tagging style already in use. If you believe a different approach would be better, propose it explicitly to the user — never silently diverge from established patterns.

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
- **Embeds**: `![[Note Name]]`, `![[image.png]]`, `![[image.png|300]]` (width)
- **Heading links**: `[[Note#Heading]]`, `[[#Heading]]` (same note)
- **Block references**: `[[Note#^block-id]]` — define with `^id` at end of paragraph
- **Highlights**: `==highlighted text==`
- **Comments**: `%%hidden in reading view%%`
- **Tags**: `#tag` or `#nested/tag` (in text or YAML frontmatter)
- **Callouts**: `> [!note]`, `> [!warning]`, `> [!tip]`, etc. Add `-` for collapsed, `+` for expanded
- **Tasks**: `- [ ] incomplete`, `- [x] complete`
- **Footnotes**: `[^1]` with `[^1]: text` definition

### Key Pitfalls

- **Unclosed HTML tags break rendering.** `<details>` without `</details>` corrupts everything after it. Always close tags, escape with `\<tag>`, or wrap in backticks.
- **Markdown inside HTML is not rendered.** `<div>**bold**</div>` shows literal asterisks.
- **HTML blocks must not contain blank lines.** Blank lines within `<table>...</table>` break the block.
- **Pipe characters in table links must be escaped**: `[[Note\|alias]]`, `![[img.png\|200]]`.
- **Block identifiers** use only Latin letters, numbers, and dashes. For paragraphs, add ` ^id` at end of line. For lists/blockquotes, put `^id` on a separate line with blank lines around it.

### YAML Frontmatter Pitfalls

- **No inline `#` comments.** YAML treats `#` as a comment delimiter and silently truncates the value. `source: "[[Files]]" # keep this` stores only `Files`. Place instructions in the note body instead.
- **Always quote wikilinks.** Write `source: "[[Note Name]]"`, not `source: [[Note Name]]`. Unquoted `[[` and `]]` break YAML parsing. This applies to both text and list properties.
- **Tags must contain at least one non-numeric character.** `2025` is invalid; `y2025` is valid. Allowed characters: letters, numbers, `_`, `-`, `/`.
- **Property types are not discoverable via CLI.** Refer to existing notes or templates to determine expected types. Supported types: `text`, `list`, `number`, `checkbox`, `date`, `datetime`.
- **Default properties**: `tags` (list), `aliases` (list — alternative names for link suggestions), `cssclasses` (list — CSS styling).

### Detailed References

- [formatting.md](formatting.md) — Complete syntax reference (tables, math, diagrams, callout types, code blocks, HTML, escaping)
- [links-and-embeds.md](links-and-embeds.md) — Internal links, embeds (images, PDFs, audio, search results), aliases, block references
- [properties.md](properties.md) — Property types, formats, defaults, Publish properties, search syntax

## Bases

Bases is a core plugin that creates database-like views of notes. Each base defines filters, formulas, and views — all stored as YAML in `.base` files or embedded in code blocks. All data stays in your Markdown files and their properties; Bases just provides structured views.

### Key Concepts

- **Filters** narrow results from the vault using property comparisons and functions like `file.hasTag()`, `file.inFolder()`, `file.hasLink()`
- **Formulas** define calculated properties: `total: "price * quantity"`, `overdue: 'if(due_date < now(), "Late", "")'`
- **Views** display results as table, cards, list, or map — each with its own filters, sorting, and grouping
- **Properties** — three kinds: note properties (frontmatter), file properties (`file.name`, `file.mtime`), and formula properties
- **`this`** — refers to the file where the base is displayed (the embedding note, not the base itself)

### Embedding Bases

```markdown
![[Projects.base]]              Embed first view
![[Projects.base#Kanban]]       Embed specific view
```

Or inline as a code block:

````markdown
```base
filters:
  and:
    - file.hasTag("project")
    - 'status != "done"'
views:
  - type: table
    name: Active Projects
```
````

### Common Filter Patterns

```yaml
file.hasTag("project")           # files with tag
file.inFolder("Notes")           # files in folder (recursive)
file.hasLink("[[Reference]]")    # files linking to a note
file.mtime > now() - "7d"        # modified in last week
status == "active"               # property value match
```

### CLI Commands

```
obsidian bases                                          # list .base files
obsidian base:query file=Projects view=Table format=md  # query a base
obsidian base:create name="New Item" silent             # create item
```

### Detailed References

- [bases.md](bases.md) — Syntax, filters, formulas, views (table/cards/list/map), summaries, operators, types
- [bases-functions.md](bases-functions.md) — Complete function reference (global, string, number, date, list, link, file, object, regex)

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
| **Unique notes** | `unique [name=] [content=] [silent]` |
| **Diff/History** | `diff [file=] [from=] [to=]`, `history`, `history:read`, `history:restore` |
| **Plugins** | `plugins`, `plugin id=<id>`, `plugin:enable`, `plugin:disable`, `plugin:reload` |
| **Workspace** | `workspace`, `workspaces`, `tabs`, `recents` |
| **Word count** | `wordcount [file=] [words] [characters]` |
| **Web viewer** | `web url=<url> [newtab]` |
| **Developer** | `dev:screenshot path=<f>`, `eval code=<js>`, `dev:console`, `dev:errors` |

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
