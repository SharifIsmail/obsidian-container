# Bases Functions Reference

Complete list of functions for use in Bases filters and formulas. Functions are organized by the type they operate on.

For Bases syntax, operators, and views: See [bases.md](bases.md)

## Contents

- [Global Functions](#global-functions)
- [Any Type](#any-type)
- [String](#string)
- [Number](#number)
- [Date](#date)
- [List](#list)
- [Link](#link)
- [File](#file)
- [Object](#object)
- [Regular Expression](#regular-expression)

## Global Functions

Used without a type prefix.

### `date(string): date`

Parse a date string. Format: `YYYY-MM-DD HH:mm:ss`.

```
date("2025-01-15")
date("2025-01-15 14:30:00")
```

### `duration(string): duration`

Parse a string as a duration. See date arithmetic units in [bases.md](bases.md).

```
duration("1d")
duration("2 weeks")
now() + (duration("1d") * 2)
```

When doing arithmetic with scalars, duration must be on the left: `duration("5h") * 2`.

### `today(): date`

Current date with time set to zero.

### `now(): date`

Current date and time.

### `if(condition, trueResult, falseResult?): any`

Conditional. Returns `trueResult` if condition is truthy, `falseResult` otherwise (defaults to `null`).

```
if(price, "$" + price.toFixed(2), "")
if(status == "Done", "Complete", "In Progress")
if(due_date < now() && status != "Done", "Overdue", "")
```

### `file(path): file`

Returns a file object for the given path.

```
file("path/to/note.md")
file(link("[[filename]]"))
```

### `link(path, display?): Link`

Create a link object. Optional display text or icon.

```
link("filename")
link("filename", "Display Text")
link("filename", icon("plus"))
link("https://obsidian.md")
link("https://google.com/maps/search/" + file.name, "Google Maps")
```

### `list(element): List`

Wrap a value in a list if it isn't one already. Returns lists unmodified.

```
list("value")    # → ["value"]
list([1, 2])     # → [1, 2] (unchanged)
```

Useful when a property may contain a string or a list across different notes.

### `image(path): image`

Returns an image that renders in the view.

```
image(cover_property)
image("https://example.com/photo.jpg")
```

### `icon(name): icon`

Returns a Lucide icon by name.

```
icon("arrow-right")
icon("check")
```

### `html(string): html`

Render a string as HTML in the view.

```
html("<b>Bold</b>")
```

### `escapeHTML(string): string`

Escape special characters for safe HTML inclusion.

### `number(input): number`

Convert to number. Dates → milliseconds since epoch. Booleans → 1/0. Strings → parsed number.

```
number("3.14")    # → 3.14
number(true)      # → 1
```

### `max(n1, n2, ...): number`

Returns the largest of all provided numbers.

### `min(n1, n2, ...): number`

Returns the smallest of all provided numbers.

## Any Type

Functions available on any value.

### `.isTruthy(): boolean`

Coerce value to boolean.

```
1.isTruthy()       # → true
"".isTruthy()      # → false
```

### `.isType(type): boolean`

Check if value is of a specific type.

```
"hello".isType("string")    # → true
42.isType("number")         # → true
```

### `.toString(): string`

String representation of any value.

```
123.toString()    # → "123"
```

## String

Functions on string values. Field: `string.length` (character count).

### `.contains(value): boolean`

```
"hello world".contains("world")    # → true
```

### `.containsAll(...values): boolean`

True if string contains **all** values.

```
"hello world".containsAll("hello", "world")    # → true
```

### `.containsAny(...values): boolean`

True if string contains **any** value.

```
"hello".containsAny("x", "h")    # → true
```

### `.startsWith(query): boolean`

```
"hello".startsWith("he")    # → true
```

### `.endsWith(query): boolean`

```
"hello".endsWith("lo")    # → true
```

### `.isEmpty(): boolean`

True if string has no characters or is not present.

```
"".isEmpty()        # → true
"hello".isEmpty()   # → false
```

### `.lower(): string`

Convert to lowercase.

### `.title(): string`

Convert to title case (first letter of each word capitalized).

```
"hello world".title()    # → "Hello World"
```

### `.trim(): string`

Remove whitespace from both ends.

### `.replace(pattern, replacement): string`

Replace occurrences. Pattern can be string (replaces all) or regex.

```
"a:b:c".replace(":", "-")       # → "a-b-c"
"a:b:c".replace(/:/, "-")       # → "a-b:c" (first only)
"a:b:c".replace(/:/g, "-")      # → "a-b-c" (all, with g flag)
```

### `.repeat(count): string`

```
"abc".repeat(3)    # → "abcabcabc"
```

### `.reverse(): string`

```
"hello".reverse()    # → "olleh"
```

### `.slice(start, end?): string`

Substring from `start` (inclusive) to `end` (exclusive). Omit `end` to go to end of string.

```
"hello".slice(1, 4)    # → "ell"
"hello".slice(2)       # → "llo"
```

### `.split(separator, n?): list`

Split into list. Optional limit `n`.

```
"a,b,c,d".split(",")       # → ["a", "b", "c", "d"]
"a,b,c,d".split(",", 2)    # → ["a", "b"]
```

## Number

Functions on numeric values.

### `.abs(): number`

Absolute value.

```
(-5).abs()    # → 5
```

### `.ceil(): number`

Round up.

```
(2.1).ceil()    # → 3
```

### `.floor(): number`

Round down.

```
(2.9).floor()    # → 2
```

### `.round(digits?): number`

Round to nearest integer, or to `digits` decimal places.

```
(2.5).round()       # → 3
(2.3333).round(2)   # → 2.33
```

### `.toFixed(precision): string`

Fixed-point notation string.

```
(3.14159).toFixed(2)    # → "3.14"
```

### `.isEmpty(): boolean`

True if number is not present.

## Date

Functions on date objects. Construct with `date()`, `today()`, or `now()`.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `.year` | Number | Year |
| `.month` | Number | Month (1–12) |
| `.day` | Number | Day of month |
| `.hour` | Number | Hour (0–23) |
| `.minute` | Number | Minute (0–59) |
| `.second` | Number | Second (0–59) |
| `.millisecond` | Number | Millisecond (0–999) |

### `.date(): date`

Strip time portion.

```
now().date().format("YYYY-MM-DD HH:mm:ss")    # → "2025-12-31 00:00:00"
```

### `.time(): string`

Return time portion as string.

```
now().time()    # → "14:30:45"
```

### `.format(format): string`

Format using Moment.js format string.

```
date.format("YYYY-MM-DD")         # → "2025-05-27"
date.format("MMM D, YYYY")        # → "May 27, 2025"
date.format("dddd")               # → "Tuesday"
```

### `.relative(): string`

Human-readable relative time.

```
file.mtime.relative()    # → "3 days ago"
```

### `.isEmpty(): boolean`

Always returns `false` for dates.

## List

Functions on list values. Field: `list.length` (element count).

### `.contains(value): boolean`

```
[1, 2, 3].contains(2)    # → true
```

### `.containsAll(...values): boolean`

True if list contains **all** values.

```
[1, 2, 3].containsAll(2, 3)    # → true
```

### `.containsAny(...values): boolean`

True if list contains **any** value.

```
[1, 2, 3].containsAny(3, 4)    # → true
```

### `.filter(condition): list`

Filter elements. Uses `value` and `index` variables.

```
[1, 2, 3, 4].filter(value > 2)    # → [3, 4]
```

### `.map(expression): list`

Transform each element. Uses `value` and `index` variables.

```
[1, 2, 3].map(value + 1)       # → [2, 3, 4]
[1, 2, 3].map(value * index)   # → [0, 2, 6]
```

### `.reduce(expression, initial): any`

Reduce to single value. Uses `value`, `index`, and `acc` variables.

```
[1, 2, 3].reduce(acc + value, 0)    # → 6 (sum)
values.filter(value.isType("number")).reduce(
  if(acc == null || value > acc, value, acc), null
)    # → max number or null
```

### `.sort(): list`

Sort ascending.

```
[3, 1, 2].sort()        # → [1, 2, 3]
["c", "a", "b"].sort()  # → ["a", "b", "c"]
```

### `.reverse(): list`

Reverse order.

```
[1, 2, 3].reverse()    # → [3, 2, 1]
```

### `.unique(): list`

Remove duplicates.

```
[1, 2, 2, 3].unique()    # → [1, 2, 3]
```

### `.flat(): list`

Flatten nested lists.

```
[1, [2, 3]].flat()    # → [1, 2, 3]
```

### `.join(separator): string`

Join elements into a string.

```
[1, 2, 3].join(", ")    # → "1, 2, 3"
```

### `.slice(start, end?): list`

Portion of list from `start` (inclusive) to `end` (exclusive).

```
[1, 2, 3, 4].slice(1, 3)    # → [2, 3]
```

### `.isEmpty(): boolean`

```
[].isEmpty()       # → true
[1].isEmpty()      # → false
```

## Link

Functions on link objects. Links are created from wikilinks in frontmatter, or with `link()`.

### `.asFile(): file`

Returns a file object if the link points to a valid local file.

```
link("[[note]]").asFile()
```

### `.linksTo(file): boolean`

Whether the linked file has a link to the given file.

### Comparing Links

Links compare equal if they point to the same file:

```
author == this           # link equals file
authors.contains(this)   # link in list
link1 == link2           # same target
```

## File

Functions on file objects. Access via `file` keyword or `file("path")`.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `.name` | String | File name |
| `.basename` | String | Name without extension |
| `.path` | String | Full path from vault root |
| `.folder` | String | Parent folder path |
| `.ext` | String | File extension |
| `.size` | Number | Size in bytes |
| `.ctime` | Date | Created time |
| `.mtime` | Date | Modified time |
| `.tags` | List | All tags (content + frontmatter) |
| `.links` | List | Internal links |
| `.properties` | Object | All properties |

### `.asLink(display?): Link`

Convert to a clickable link.

```
file.asLink()
file.asLink("Click here")
```

### `.hasTag(...values): boolean`

True if file has any of the tags (includes nested tags).

```
file.hasTag("project")
file.hasTag("tag1", "tag2")    # has #tag1 OR #tag2
# Also matches #tag1/subtag
```

### `.hasLink(otherFile): boolean`

True if file links to the other file.

```
file.hasLink("[[Reference]]")
file.hasLink(this.file)
```

### `.hasProperty(name): boolean`

True if the note has the given property.

```
file.hasProperty("status")
```

### `.inFolder(folder): boolean`

True if file is in the folder or any sub-folder.

```
file.inFolder("Notes")
file.inFolder("Projects/Active")
```

## Object

Functions on key-value objects like `{"a": 1, "b": 2}`.

### `.isEmpty(): boolean`

True if object has no properties.

### `.keys(): list`

List of all keys.

### `.values(): list`

List of all values.

## Regular Expression

Regex patterns written as `/pattern/flags`.

### `.matches(value): boolean`

Test if the regex matches the string.

```
/abc/.matches("abcde")      # → true
/\d+/.matches("abc123")     # → true
```

Use in `.replace()` and `.split()`:

```
"a:b:c".replace(/:/g, "-")    # → "a-b-c"
"a,b;c".split(/[,;]/)         # → ["a", "b", "c"]
```
