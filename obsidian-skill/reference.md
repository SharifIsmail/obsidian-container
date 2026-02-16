# Obsidian CLI Command Reference

All commands: `obsidian <command> [params] [flags]`

Parameters take values (`param=value`). Flags are boolean switches (include to enable). Use `\n` for newlines, `\t` for tabs. Wrap values with spaces in quotes.

## Contents

- [Vault & General](#vault--general)
- [Files & Folders](#files--folders)
- [Daily Notes](#daily-notes)
- [Search](#search)
- [Tags](#tags)
- [Tasks](#tasks)
- [Properties](#properties)
- [Links](#links)
- [Outline](#outline)
- [Bookmarks](#bookmarks)
- [Templates](#templates)
- [Word Count](#word-count)
- [File History & Diff](#file-history--diff)
- [Plugins](#plugins)
- [Command Palette](#command-palette)
- [Workspace & Tabs](#workspace--tabs)
- [Unique Notes](#unique-notes)
- [Bases](#bases)
- [Random Notes](#random-notes)
- [Web Viewer](#web-viewer)
- [Sync](#sync)
- [Publish](#publish)
- [Themes & Snippets](#themes--snippets)
- [Developer Commands](#developer-commands)

## Vault & General

| Command | Description |
|---|---|
| `help` | Show all available commands |
| `version` | Show Obsidian version |
| `vault [info=name\|path\|files\|folders\|size]` | Show vault info |
| `vaults [total] [verbose]` | List known vaults |
| `vault:open name=<name>` | Switch to a different vault (TUI only) |
| `reload` | Reload the app window |
| `restart` | Restart the app |

## Files & Folders

| Command | Description |
|---|---|
| `file [file=] [path=]` | Show file info (path, name, extension, size, dates) |
| `files [folder=] [ext=] [total]` | List files in vault |
| `folders [folder=] [total]` | List folders |
| `folder path=<path> [info=files\|folders\|size]` | Show folder info |
| `open [file=] [path=] [newtab]` | Open a file |
| `read [file=] [path=]` | Read file contents |
| `create [name=] [path=] [content=] [template=] [overwrite] [silent] [newtab]` | Create or overwrite a file |
| `append [file=] [path=] content=<text> [inline]` | Append to file |
| `prepend [file=] [path=] content=<text> [inline]` | Prepend after frontmatter |
| `move [file=] [path=] to=<path>` | Move or rename file |
| `delete [file=] [path=] [permanent]` | Delete file (trash by default) |

## Daily Notes

| Command | Description |
|---|---|
| `daily [paneType=tab\|split\|window] [silent]` | Open/create daily note |
| `daily:read` | Read daily note contents |
| `daily:append content=<text> [paneType=tab\|split\|window] [inline] [silent]` | Append to daily note |
| `daily:prepend content=<text> [paneType=tab\|split\|window] [inline] [silent]` | Prepend to daily note |

## Search

| Command | Description |
|---|---|
| `search query=<text> [path=] [limit=] [format=text\|json] [total] [matches] [case]` | Search vault |
| `search:open [query=]` | Open search view |

## Tags

| Command | Description |
|---|---|
| `tags [file=] [path=] [all] [total] [counts] [sort=count]` | List tags |
| `tag name=<tag> [total] [verbose]` | Get tag info |

## Tasks

| Command | Description |
|---|---|
| `tasks [file=] [path=] [all] [daily] [total] [done] [todo] [verbose] [status=<char>]` | List tasks |
| `task [ref=<path:line>] [file=] [path=] [line=] [toggle] [done] [todo] [daily] [status=<char>]` | Show or update a task |

Examples:
```
tasks daily todo           # incomplete tasks from daily note
tasks verbose              # all tasks grouped by file with line numbers
task ref="Recipe.md:8" toggle   # toggle a specific task
task daily line=3 done     # mark daily note task done
```

## Properties

| Command | Description |
|---|---|
| `properties [file=] [path=] [name=] [all] [total] [counts] [sort=count] [format=yaml\|tsv]` | List properties |
| `property:set name=<n> value=<v> [type=text\|list\|number\|checkbox\|date\|datetime] [file=] [path=]` | Set a property |
| `property:remove name=<n> [file=] [path=]` | Remove a property |
| `property:read name=<n> [file=] [path=]` | Read a property value |
| `aliases [file=] [path=] [all] [total] [verbose]` | List aliases |

## Links

| Command | Description |
|---|---|
| `backlinks [file=] [path=] [counts] [total]` | List backlinks |
| `links [file=] [path=] [total]` | List outgoing links |
| `unresolved [total] [counts] [verbose]` | List unresolved links |
| `orphans [total] [all]` | Files with no incoming links |
| `deadends [total] [all]` | Files with no outgoing links |

## Outline

| Command | Description |
|---|---|
| `outline [file=] [path=] [format=tree\|md] [total]` | Show headings |

## Bookmarks

| Command | Description |
|---|---|
| `bookmarks [total] [verbose]` | List bookmarks |
| `bookmark [file=] [subpath=] [folder=] [search=] [url=] [title=]` | Add bookmark |

## Templates

| Command | Description |
|---|---|
| `templates [total]` | List templates |
| `template:read name=<name> [title=] [resolve]` | Read template content |
| `template:insert name=<name>` | Insert template into active file |

## Word Count

| Command | Description |
|---|---|
| `wordcount [file=] [path=] [words] [characters]` | Count words and characters |

## File History & Diff

| Command | Description |
|---|---|
| `diff [file=] [path=] [from=] [to=] [filter=local\|sync]` | List or compare file versions |
| `history [file=] [path=]` | List local history versions |
| `history:list` | List all files with local history |
| `history:read [file=] [path=] [version=]` | Read a history version |
| `history:restore [file=] [path=] version=<n>` | Restore a history version |
| `history:open [file=] [path=]` | Open file recovery |

Examples:
```
diff file=Recipe from=1         # compare latest version to current
diff file=Recipe from=2 to=1    # compare two versions
diff filter=sync                # only sync versions
```

## Plugins

| Command | Description |
|---|---|
| `plugins [filter=core\|community] [versions]` | List installed plugins |
| `plugins:enabled [filter=] [versions]` | List enabled plugins |
| `plugins:restrict [on] [off]` | Toggle restricted mode |
| `plugin id=<id>` | Get plugin info |
| `plugin:enable id=<id> [filter=]` | Enable a plugin |
| `plugin:disable id=<id> [filter=]` | Disable a plugin |
| `plugin:install id=<id> [enable]` | Install community plugin |
| `plugin:uninstall id=<id>` | Uninstall community plugin |
| `plugin:reload id=<id>` | Reload a plugin (for devs) |

## Command Palette

| Command | Description |
|---|---|
| `commands [filter=<prefix>]` | List available command IDs |
| `command id=<command-id>` | Execute an Obsidian command |
| `hotkeys [total] [all] [verbose]` | List hotkeys |
| `hotkey id=<command-id> [verbose]` | Get hotkey for a command |

## Workspace & Tabs

| Command | Description |
|---|---|
| `workspace [ids]` | Show workspace tree |
| `workspaces [total]` | List saved workspaces |
| `workspace:save [name=]` | Save workspace |
| `workspace:load name=<name>` | Load workspace |
| `workspace:delete name=<name>` | Delete workspace |
| `tabs [ids]` | List open tabs |
| `tab:open [group=] [file=] [view=]` | Open a new tab |
| `recents [total]` | List recently opened files |

## Unique Notes

| Command | Description |
|---|---|
| `unique [name=] [content=] [paneType=tab\|split\|window] [silent]` | Create unique note |

## Bases

| Command | Description |
|---|---|
| `bases` | List all .base files |
| `base:views` | List views in current base |
| `base:create [name=] [content=] [silent] [newtab]` | Create item in base view |
| `base:query [file=] [path=] [view=] [format=json\|csv\|tsv\|md\|paths]` | Query a base |

## Random Notes

| Command | Description |
|---|---|
| `random [folder=] [newtab] [silent]` | Open a random note |
| `random:read [folder=]` | Read a random note |

## Web Viewer

| Command | Description |
|---|---|
| `web url=<url> [newtab]` | Open URL in web viewer |

## Sync

| Command | Description |
|---|---|
| `sync [on] [off]` | Pause or resume sync |
| `sync:status` | Show sync status |
| `sync:history [file=] [path=] [total]` | List sync versions |
| `sync:read [file=] [path=] version=<n>` | Read a sync version |
| `sync:restore [file=] [path=] version=<n>` | Restore a sync version |
| `sync:open [file=] [path=]` | Open sync history |
| `sync:deleted [total]` | List deleted files in sync |

## Publish

| Command | Description |
|---|---|
| `publish:site` | Show publish site info |
| `publish:list [total]` | List published files |
| `publish:status [total] [new] [changed] [deleted]` | List publish changes |
| `publish:add [file=] [path=] [changed]` | Publish a file |
| `publish:remove [file=] [path=]` | Unpublish a file |
| `publish:open [file=] [path=]` | Open on published site |

## Themes & Snippets

| Command | Description |
|---|---|
| `themes [versions]` | List installed themes |
| `theme [name=]` | Show active theme or get info |
| `theme:set name=<name>` | Set active theme |
| `theme:install name=<name> [enable]` | Install theme |
| `theme:uninstall name=<name>` | Uninstall theme |
| `snippets` | List CSS snippets |
| `snippets:enabled` | List enabled snippets |
| `snippet:enable name=<name>` | Enable snippet |
| `snippet:disable name=<name>` | Disable snippet |

## Developer Commands

| Command | Description |
|---|---|
| `devtools` | Toggle dev tools |
| `dev:screenshot [path=<filename>]` | Take screenshot (base64 PNG) |
| `eval code=<javascript>` | Execute JavaScript in Obsidian |
| `dev:console [limit=] [level=log\|warn\|error\|info\|debug] [clear]` | Show console messages |
| `dev:errors [clear]` | Show JavaScript errors |
| `dev:css selector=<css> [prop=]` | Inspect CSS |
| `dev:dom selector=<css> [attr=] [css=] [total] [text] [inner] [all]` | Query DOM elements |
| `dev:debug [on] [off]` | Attach/detach CDP debugger |
| `dev:cdp method=<CDP.method> [params=<json>]` | Run CDP command |
| `dev:mobile [on] [off]` | Toggle mobile emulation |
