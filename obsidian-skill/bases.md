# Bases

Bases is a core plugin that creates database-like views of your notes. It lets you view, edit, sort, filter, and group files and their properties. All data lives in your local Markdown files — Bases just provides structured views on top.

## Contents

- [Creating a Base](#creating-a-base)
- [Syntax Overview](#syntax-overview)
- [Filters](#filters)
- [Formulas](#formulas)
- [Properties in Bases](#properties-in-bases)
- [Views](#views)
- [Summaries](#summaries)
- [Operators](#operators)
- [Types](#types)

For the complete function reference: See [bases-functions.md](bases-functions.md)

## Creating a Base

### As a `.base` file

Create via Command palette (`Bases: Create new base`), File explorer (right-click → New base), or the ribbon icon. Base files use YAML syntax.

### Embedded in a note

Embed an existing base file:

```markdown
![[File.base]]
![[File.base#ViewName]]
```

Or embed directly as a code block:

````markdown
```base
filters:
  and:
    - file.hasTag("project")
views:
  - type: table
    name: Projects
```
````

### Via CLI

```
obsidian bases                                    # list all .base files
obsidian base:views                               # list views in current base
obsidian base:create name=<n> [content=] [silent] # create item in current view
obsidian base:query [file=] [view=] [format=json|csv|tsv|md|paths]
```

## Syntax Overview

A base file is valid YAML with these top-level sections:

```yaml
filters:       # Global filters (apply to all views)
formulas:      # Calculated properties
properties:    # Display configuration per property
summaries:     # Custom summary formulas
views:         # List of view configurations
```

### Full Example

```yaml
filters:
  or:
    - file.hasTag("book")
    - file.inFolder("Reading")

formulas:
  price_display: 'if(price, "$" + price.toFixed(2), "")'
  cost_per_page: "(price / pages).toFixed(2)"

properties:
  status:
    displayName: Status
  formula.price_display:
    displayName: "Price"

summaries:
  customAvg: 'values.mean().round(3)'

views:
  - type: table
    name: "Reading List"
    limit: 20
    groupBy:
      property: status
      direction: ASC
    filters:
      and:
        - 'status != "done"'
    order:
      - file.name
      - note.status
      - formula.price_display
    summaries:
      formula.cost_per_page: Average
```

## Filters

By default, a base includes **every file in the vault**. Filters narrow results to matching files.

### Placement

- **Global** (`filters:` at top level) — applies to all views
- **Per-view** (`filters:` inside a view) — applies to that view only

Both are combined with AND when evaluating a view.

### Conjunctions

```yaml
filters:
  and:                            # ALL conditions must be true
    - file.hasTag("project")
    - 'status != "done"'

  or:                             # ANY condition must be true
    - file.hasTag("urgent")
    - 'priority > 3'

  not:                            # NONE of the conditions must be true
    - file.hasTag("archived")
    - file.inFolder("Archive")
```

Conjunctions can be nested:

```yaml
filters:
  or:
    - file.hasTag("active")
    - and:
        - file.hasTag("book")
        - file.hasLink("Textbook")
    - not:
        - file.inFolder("Archive")
```

### Filter Statements

Each filter is either a function call or a comparison using operators:

```yaml
# Function-based
- file.hasTag("project")
- file.inFolder("Notes")
- file.hasLink("[[Reference]]")

# Comparison-based
- 'status == "active"'
- 'priority > 3'
- 'file.mtime > now() - "7d"'
- 'price >= 10 && price <= 50'
```

### Advanced Filter Editor

In the UI, click the code button to edit raw filter syntax. This supports complex functions that the point-and-click interface can't represent.

## Formulas

Formulas define calculated properties that can be displayed in any view.

```yaml
formulas:
  total: "price * quantity"
  deadline: 'start_date + "2w"'
  display_price: 'if(price, "$" + price.toFixed(2), "")'
  overdue: 'if(due_date < now() && status != "Done", "Overdue", "")'
  full_name: 'first_name + " " + last_name'
  item_count: "tasks.length"
  priority_score: "(impact * urgency) / effort"
```

### Referencing Properties

| Prefix | Type | Example |
|--------|------|---------|
| (none) | Note property (shorthand) | `price`, `status` |
| `note.` | Note property (explicit) | `note.price`, `note["price"]` |
| `file.` | File property | `file.name`, `file.mtime` |
| `formula.` | Another formula | `formula.total` |

Formulas can reference other formulas (no circular references allowed).

### Text Literals

Since formulas are YAML strings, use nested quotes for text literals:

```yaml
formulas:
  greeting: '"Hello " + name'                    # outer double, inner double
  label: "'Status: ' + status"                    # outer double, inner single
  display: 'if(price, price.toFixed(2) + " dollars")'
```

### Creating Formulas via UI

1. Click **Properties** in the toolbar
2. Click **Add formula**
3. Enter name and formula expression
4. The editor autocompletes and validates as you type

## Properties in Bases

Three kinds of properties:

### Note Properties

From YAML frontmatter. Access as `author`, `note.author`, or `note["author"]`.

### File Properties

Available for all file types:

| Property | Type | Description |
|----------|------|-------------|
| `file.name` | String | File name |
| `file.basename` | String | Name without extension |
| `file.path` | String | Full path from vault root |
| `file.folder` | String | Parent folder path |
| `file.ext` | String | File extension |
| `file.size` | Number | Size in bytes |
| `file.ctime` | Date | Created time |
| `file.mtime` | Date | Modified time |
| `file.tags` | List | All tags (content + frontmatter) |
| `file.links` | List | All internal links |
| `file.embeds` | List | All embeds |
| `file.backlinks` | List | Files linking to this file (expensive) |
| `file.properties` | Object | All properties |
| `file.file` | File | File object (for functions) |

### Formula Properties

Defined in the base's `formulas:` section. Access as `formula.name`.

### The `this` Object

`this` refers to the context where the base is displayed:

- **Base opened directly**: `this` = the base file itself
- **Base embedded in a note**: `this` = the embedding note
- **Base in sidebar**: `this` = the active file in the main area

Example: `file.hasLink(this.file)` replicates a backlinks pane.

### Property Display Configuration

```yaml
properties:
  status:
    displayName: Status
  formula.formatted_price:
    displayName: "Price"
  file.ext:
    displayName: Extension
```

Display names are cosmetic — filters and formulas still use the real property name.

## Views

Each base can have multiple views. The first view loads by default.

```yaml
views:
  - type: table
    name: "My Table"
    limit: 10
    groupBy:
      property: status
      direction: DESC
    filters:
      and:
        - 'status != "done"'
    order:
      - file.name
      - note.status
    summaries:
      formula.cost: Average
```

### View Properties

| Key | Description |
|-----|-------------|
| `type` | Layout type: `table`, `cards`, `list`, `map` |
| `name` | Display name (used in `![[File.base#Name]]`) |
| `limit` | Max number of results |
| `groupBy` | `property` and `direction` (ASC/DESC) |
| `filters` | View-specific filters (AND'd with global) |
| `order` | Column/property display order |
| `summaries` | Map of property → summary formula name |

### Layouts

#### Table

Rows = files, columns = properties. Right-click headers for context menu. Supports summaries at column bottoms.

Settings: row height (short/medium/tall/extra tall).

#### Cards

Gallery-like grid with optional cover images. Good for visual collections.

Settings:
- **Card size**: width of cards
- **Image property**: property containing image link, URL, or hex color
- **Image fit**: `cover` (fill + crop) or `contain` (fit without cropping)
- **Image aspect ratio**: default 1:1

Image property formats:
```yaml
cover: "[[attachments/photo.jpg]]"    # local attachment
cover: "https://example.com/img.png"  # external URL
cover: "#4a90d9"                      # hex color
```

#### List

Bulleted or numbered list view.

Settings:
- **Markers**: bullets, numbers, or none
- **Indent properties**: show properties as indented sub-items
- **Separators**: character between properties when not indented (default: comma)

#### Map

Interactive map with pins. Requires the **Maps** plugin (official community plugin).

Settings:
- **Marker coordinates**: property with `[lat, lng]` (list or comma-separated text)
- **Marker icon**: property with Lucide icon name (e.g. `landmark`)
- **Marker color**: property with CSS color (hex, RGB, named, or CSS variable)
- **Map tiles**: URL to tile service (OpenFreeMap, MapTiler, Mapbox, etc.)

Coordinate formats:
```yaml
# Text property
coordinates: "48.85837, 2.294481"

# List property
coordinates:
  - "48.85837"
  - "2.294481"

# Formula combining separate properties
[latitude, longitude]
```

Free tile URLs (OpenFreeMap):
- Dark: `https://tiles.openfreemap.org/styles/dark`
- Positron: `https://tiles.openfreemap.org/styles/positron`
- Liberty: `https://tiles.openfreemap.org/styles/liberty`

### Embedding Views

```markdown
![[File.base]]              # first view
![[File.base#ViewName]]     # specific view
```

### Results Actions

- **Limit**: restrict number of results
- **Copy to clipboard**: paste into Markdown or spreadsheet apps
- **Export CSV**: save view as CSV file

## Summaries

Summaries aggregate values across all rows in a view.

### Built-in Summaries

| Name | Input Type | Description |
|------|------------|-------------|
| Average | Number | Mean of all values |
| Min | Number | Smallest value |
| Max | Number | Largest value |
| Sum | Number | Total of all values |
| Range | Number | Max − Min |
| Median | Number | Median value |
| Stddev | Number | Standard deviation |
| Earliest | Date | Oldest date |
| Latest | Date | Most recent date |
| Range | Date | Latest − Earliest |
| Checked | Boolean | Count of `true` values |
| Unchecked | Boolean | Count of `false` values |
| Empty | Any | Count of empty values |
| Filled | Any | Count of non-empty values |
| Unique | Any | Count of distinct values |

### Custom Summaries

Define in the top-level `summaries:` section. The `values` keyword contains all values for the property:

```yaml
summaries:
  customAvg: 'values.mean().round(3)'
  total: 'values.reduce(acc + value, 0)'
```

Assign to columns in a view:

```yaml
views:
  - type: table
    summaries:
      price: Sum
      formula.cost: customAvg
```

## Operators

### Arithmetic

| Operator | Description |
|----------|-------------|
| `+` | Addition |
| `-` | Subtraction |
| `*` | Multiplication |
| `/` | Division |
| `%` | Modulo |
| `( )` | Parentheses |

### Comparison

| Operator | Description |
|----------|-------------|
| `==` | Equals |
| `!=` | Not equal |
| `>` | Greater than |
| `<` | Less than |
| `>=` | Greater than or equal |
| `<=` | Less than or equal |

### Boolean

| Operator | Description |
|----------|-------------|
| `!` | Logical NOT |
| `&&` | Logical AND |
| `\|\|` | Logical OR |

### Date Arithmetic

Add/subtract durations from dates:

| Unit | Formats |
|------|---------|
| Year | `y`, `year`, `years` |
| Month | `M`, `month`, `months` |
| Week | `w`, `week`, `weeks` |
| Day | `d`, `day`, `days` |
| Hour | `h`, `hour`, `hours` |
| Minute | `m`, `minute`, `minutes` |
| Second | `s`, `second`, `seconds` |

```yaml
# Examples
now() + "1 day"                    # 24 hours from now
file.mtime > now() - "1 week"     # modified within last week
date("2025-01-01") + "1M" + "4h"  # Feb 1 at 04:00
now() - file.ctime                 # milliseconds since creation
datetime.date()                    # strip time portion
datetime.format("YYYY-MM-DD")     # format as string
```

## Types

### Primitives

- **Strings**: `"hello"` or `'hello'`
- **Numbers**: `42`, `3.14`, `(2.5)`
- **Booleans**: `true`, `false`

### Dates

Construct with `date("YYYY-MM-DD HH:mm:ss")`, `today()`, or `now()`.

Date fields: `.year`, `.month`, `.day`, `.hour`, `.minute`, `.second`, `.millisecond`

### Lists and Objects

- Create list from single value: `list(value)`
- Access by index: `property[0]` (0-based)
- Access object key: `property.subprop` or `property["subprop"]`

### Links

Wikilinks in frontmatter are automatically Link objects. Construct with `link("path")` or `link("path", "display text")`. Compare with `==` and `!=`. Compare to files: `author == this`.

### Files

Access via `file` keyword or `file("path")`. Convert to link: `file.asLink()`.
