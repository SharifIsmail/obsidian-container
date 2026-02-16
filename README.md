# Obsidian Container

Run [Obsidian](https://obsidian.md) in a Docker container with a headless desktop and an HTTP command API for programmatic vault access.

Based on the [linuxserver/obsidian](https://docs.linuxserver.io/images/docker-obsidian/) image. No custom Docker build required.

## What's included

- **Obsidian desktop** accessible via browser (Selkies on ports 3000/3001)
- **Command service** (port 9999) — HTTP API to execute [Obsidian CLI](https://github.com/czottmann/obsidian-cli) commands with token-based auth
- **Binary patch** — automatically fixes an [Electron bug](https://github.com/electron/electron/issues/49801) where CLI commands containing emoji/CJK characters with spaces hang indefinitely

## Quick start

```bash
git clone https://github.com/SharifIsmail/obsidian-container.git
cd obsidian-container
./setup.sh
```

On first run, `setup.sh` creates `.env` from the template. Edit it with your credentials and run again:

```bash
vi .env          # set CUSTOM_USER and PASSWORD
./setup.sh
```

## Configuration

### `.env`

| Variable | Description |
|----------|-------------|
| `CUSTOM_USER` | Web UI username |
| `PASSWORD` | Web UI password |
| `PUID` / `PGID` | Container user/group IDs (default: 1000) |
| `TZ` | Timezone (default: `Etc/UTC`) |

### Config volume

The config volume (default `./config`, override with `CONFIG_PATH`) stores Obsidian's data and the command service config:

```
config/
  cmd-service/
    tokens.md           # auth tokens
    allowed-commands.md  # command allowlist
    vault-path.md       # vault root path
  ...                   # Obsidian app data, vaults, plugins
```

### Tokens (`tokens.md`)

```
permanent:my-secret-token          # always valid
some-one-time-token                # single-use, starts 10-min session on first use
```

### Allowed commands (`allowed-commands.md`)

One command name per line. Defaults to `obsidian` if empty/missing.

## Command API

```bash
# Health check
curl -s -H "Authorization: Bearer <token>" http://localhost:9999/

# Execute commands
curl -s -X POST http://localhost:9999 \
  -H "Authorization: Bearer <token>" \
  -d '{"commands": ["obsidian vault"]}'

# Multiple commands
curl -s -X POST http://localhost:9999 \
  -H "Authorization: Bearer <token>" \
  -d '{"commands": ["obsidian read file=Recipe", "obsidian tags all counts"]}'
```

### File upload

```bash
# Write a file to the vault
curl -s -X PUT http://localhost:9999/vault/notes/hello.md \
  -H "Authorization: Bearer <token>" \
  -d "# Hello World"

# Upload binary content
curl -s -X PUT http://localhost:9999/vault/attachments/image.png \
  -H "Authorization: Bearer <token>" \
  --data-binary @image.png
```

Parent directories are created automatically. The vault root defaults to `/config` and can be overridden in `config/cmd-service/vault-path.md`.

## Using with AI agents

Download `obsidian-skill.zip` from this repo and extract the two files (`skill.md` and `reference.md`) into your Obsidian vault. These provide instructions and a command reference that AI agents can read to interact with your vault through the command API.

## Ports

| Port | Service |
|------|---------|
| 3000 | Selkies web UI (HTTP) |
| 3001 | Selkies web UI (HTTPS) |
| 9999 | Command service API |

All ports bind to `127.0.0.1` by default. Use a reverse proxy (e.g. nginx) to expose them externally with TLS.

## Reverse proxy (nginx)

Example server blocks for exposing the services:

```nginx
# Obsidian desktop
server {
    listen 443 ssl;
    server_name obs.example.com;

    ssl_certificate     /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}

# Command API
server {
    listen 443 ssl;
    server_name obs-api.example.com;

    ssl_certificate     /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:9999;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Authorization $http_authorization;
        proxy_read_timeout 60;
        proxy_send_timeout 60;
    }
}
```
