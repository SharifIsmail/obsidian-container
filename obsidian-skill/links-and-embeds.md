# Internal Links & Embeds

Obsidian's linking system connects notes into a knowledge graph. This covers all link types, embed syntax, and aliases.

## Link Formats

Obsidian supports two formats:

| Format | Syntax | Example |
|--------|--------|---------|
| Wikilink | `[[target]]` | `[[Three laws of motion]]` |
| Markdown | `[text](target)` | `[Three laws](Three%20laws%20of%20motion.md)` |

Wikilinks are the default (more compact). For Markdown format, URL-encode spaces as `%20` or wrap in angle brackets: `[text](<path with spaces.md>)`.

## Linking to Notes

```markdown
[[Note Name]]                     Link by name
[[Note Name|display text]]        Link with custom text
[[Note Name.md]]                  Explicit extension
```

Link resolution uses wikilink-style matching: filename only, no path or extension needed. If multiple files share a name, use the full path.

## Linking to Headings

```markdown
[[Note Name#Heading]]             Link to heading in another note
[[#Heading]]                      Link to heading in same note
[[Note#Heading#Subheading]]       Link to nested heading
```

Vault-wide heading search: `[[## search term]]` searches all headings across the vault.

## Linking to Blocks

A block is a paragraph, list item, blockquote, or other discrete unit of content.

### Defining block identifiers

For paragraphs, add `^id` at the end of the line (with a space before `^`):

```markdown
This is an important paragraph. ^my-block
```

For structured blocks (lists, blockquotes, callouts, tables), the identifier goes on a separate line with blank lines around it:

```markdown
> A blockquote with important content.

^quote-id

Next paragraph.
```

For list items, the identifier can go directly on the bullet:

```markdown
- Item one ^item-1
- Item two ^item-2
```

Block identifiers can only contain: Latin letters, numbers, and dashes.

### Linking to blocks

```markdown
[[Note Name#^block-id]]           Link to block in another note
[[#^block-id]]                    Link to block in same note
```

Vault-wide block search: `[[^^search term]]` searches all blocks across the vault.

**Note:** Block references are Obsidian-specific and won't work outside Obsidian.

## Display Text

Customize how a link appears:

```markdown
[[Note Name|Custom text]]                    Wikilink
[[Note Name#Heading|Section]]                Heading link
[Custom text](Note%20Name.md)                Markdown
```

For one-off display changes, use display text. For reusable alternative names, use aliases (see below).

## Aliases

Aliases are alternative names for a note, defined in the `aliases` property:

```yaml
---
aliases:
  - AI
  - Machine Intelligence
---

# Artificial Intelligence
```

When typing `[[AI`, Obsidian suggests the aliased note and creates `[[Artificial Intelligence|AI]]`. Aliases also appear in backlink searches for unlinked mentions.

## Embeds

Prefix a link with `!` to embed content inline:

### Notes

```markdown
![[Note Name]]                    Embed entire note
![[Note Name#Heading]]            Embed specific section
![[Note Name#^block-id]]          Embed specific block
```

### Images

```markdown
![[image.png]]                    Full size
![[image.png|300]]                Width 300px (aspect ratio preserved)
![[image.png|640x480]]            Explicit width x height
```

External images with dimensions:

```markdown
![Alt text](https://example.com/image.png)
![Alt|300](https://example.com/image.png)
```

### PDFs

```markdown
![[document.pdf]]                 Embed PDF
![[document.pdf#page=3]]          Open at specific page
![[document.pdf#height=400]]      Set viewer height in pixels
```

### Audio

```markdown
![[recording.ogg]]                Embed audio player
```

### Lists

Embed a specific list from another note using block identifiers:

```markdown
![[My Note#^my-list-id]]
```

### Search Results

Embed live search results using a `query` code block:

````markdown
```query
tag:#project status:active
```
````

## External Links

```markdown
[Obsidian Help](https://help.obsidian.md)
```

Link to files in other vaults using Obsidian URIs:

```markdown
[Note](obsidian://open?vault=MainVault&file=Note.md)
[Note](obsidian://open?vault=MainVault&file=My%20Note.md)
```

## Embed Web Pages

Use `<iframe>` to embed web content:

```html
<iframe src="https://example.com"></iframe>
```

YouTube videos and tweets can be embedded with image syntax:

```markdown
![](https://www.youtube.com/watch?v=VIDEO_ID)
![](https://twitter.com/user/status/TWEET_ID)
```

Not all websites allow iframe embedding. Search for "[site name] embed iframe" if direct embedding fails.

## Links in Tables

Pipe characters inside wikilinks in tables must be escaped with `\`:

```markdown
| Link | Description |
|------|-------------|
| [[Note\|Custom text]] | Escaped pipe |
| ![[image.png\|200]] | Resized embed |
```

## Invalid Characters in Links

These characters may not work in link targets: `# | ^ : %% [[ ]]`. Avoid them in filenames.

## Automatic Link Updates

Obsidian automatically updates internal links when you rename a file. This behavior can be disabled under Settings → Files & Links → Automatically update internal links.
