# Properties

Properties are structured metadata stored as YAML frontmatter at the top of a note. They enable organization, search, filtering, and integration with plugins like Bases and Dataview.

## Adding Properties

Properties are defined between `---` fences at the very beginning of a file:

```yaml
---
title: My Note
tags:
  - project
  - active
date: 2026-01-15
status: draft
---
```

## Property Types

Each property name has a type that applies vault-wide. Once a type is assigned, all properties with that name use the same type across all notes.

| Type | Format | Example |
|------|--------|---------|
| Text | Single line string | `title: My Note` |
| List | YAML list with `-` items | `tags:\n  - a\n  - b` |
| Number | Integer or decimal | `year: 2026` or `pi: 3.14` |
| Checkbox | `true` or `false` | `favorite: true` |
| Date | `YYYY-MM-DD` | `date: 2026-01-15` |
| Date & time | ISO 8601 | `time: 2026-01-15T10:30:00` |
| Tags | List (exclusive to `tags`) | see Tags below |

**Property types are not discoverable via CLI.** There is no command to query the assigned type. Refer to existing notes or templates.

## Default Properties

Obsidian has built-in properties with special behavior:

| Property | Type | Purpose |
|----------|------|---------|
| `tags` | Tags (list) | Note tags, searchable via `tag:` operator |
| `aliases` | List | Alternative names for the note (used in link suggestions) |
| `cssclasses` | List | Apply CSS snippet classes to individual notes |

### Tags

Tags in frontmatter don't use `#`. They are formatted as a list:

```yaml
---
tags:
  - journal
  - personal
  - draft
---
```

Tag rules:
- Must contain at least one non-numeric character (`2025` invalid, `y2025` valid)
- Allowed characters: letters, numbers, `_`, `-`, `/`
- Case-insensitive (`#Tag` and `#tag` are treated as identical)
- Nested tags use `/`: `inbox/to-read`

### Aliases

Aliases let you reference a note by alternative names. They appear in link autocomplete suggestions:

```yaml
---
aliases:
  - AI
  - Machine Intelligence
---

# Artificial Intelligence
```

When linking via an alias, Obsidian creates `[[Artificial Intelligence|AI]]` automatically.

### CSS Classes

Apply custom styling to specific notes:

```yaml
---
cssclasses:
  - wide-page
  - no-inline-title
---
```

## Property Value Formats

### Text

Single-line string. Markdown is **not** rendered in text properties.

URLs and internal links are supported in text properties, but **wikilinks must be quoted**:

```yaml
---
title: A New Hope
link: "[[Episode IV]]"
url: https://www.example.com
---
```

### List

Each value on its own line, preceded by `-` and a space. **Wikilinks in lists must be quoted:**

```yaml
---
cast:
  - Mark Hamill
  - Harrison Ford
related:
  - "[[Note A]]"
  - "[[Note B]]"
---
```

### Number

Literal numbers only (no expressions). Integers and decimals:

```yaml
---
year: 1977
rating: 4.5
---
```

### Checkbox

Boolean values:

```yaml
---
favorite: true
archived: false
---
```

### Date / Date & Time

```yaml
---
date: 2026-01-15
time: 2026-01-15T10:30:00
---
```

With the Daily Notes plugin enabled, date properties function as internal links to the corresponding daily note.

## Common Pitfalls

**Inline `#` comments truncate values.** YAML interprets `#` as a comment:

```yaml
# WRONG — stores "Files" instead of the full value
source: "[[Files]]" # do not change

# CORRECT
source: "[[Files]]"
```

**Wikilinks must always be quoted.** Unquoted `[[` and `]]` break YAML parsing:

```yaml
# WRONG
source: [[My Note]]

# CORRECT
source: "[[My Note]]"
related:
  - "[[Note A]]"
```

Obsidian's UI auto-adds quotes, but when writing programmatically you must add them yourself.

**Purely numeric tags are invalid:**

```yaml
# INVALID
tags:
  - 2025

# VALID
tags:
  - y2025
```

**Nested properties are not supported.** Use source mode to view them if present.

**Markdown in properties is not rendered.** Properties are meant for atomic, machine-readable data.

## JSON Format

Properties can also be defined in JSON (though YAML is recommended):

```
---
{
  "tags": ["journal"],
  "publish": false
}
---
```

JSON blocks are read, interpreted, and saved as YAML.

## Publish Properties

For Obsidian Publish:

| Property | Description |
|----------|-------------|
| `publish` | Whether to publish this note |
| `permalink` | Custom URL path |
| `description` | Page description (meta tag) |
| `image` | Social media preview image |
| `cover` | Cover image |

## Deprecated Properties

Replaced in Obsidian 1.4, support dropped in 1.9:

| Deprecated | Replacement |
|------------|-------------|
| `tag` | `tags` |
| `alias` | `aliases` |
| `cssclass` | `cssclasses` |

## Searching Properties

Properties have dedicated search syntax. Use `[property:value]` in the Search plugin. For example: `[tags:project]`, `[date:2026-01-15]`.

## Setting Properties via CLI

```
obsidian property:set name=status value=done file=MyNote
obsidian property:read name=tags file=MyNote
obsidian property:remove name=draft file=MyNote
```

See [reference.md](reference.md) for all property commands.
