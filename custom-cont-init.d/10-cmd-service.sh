#!/usr/bin/env bash
set -e

echo "[cmd-setup] Starting command service setup..."

# --- Copy command service ---
cp /custom-cont-init.d/cmd_service.py /usr/local/bin/obsidian-cmd-service.py
chmod +x /usr/local/bin/obsidian-cmd-service.py
echo "[cmd-setup] Command service written."

# --- Create s6 service directory ---
mkdir -p /run/service/svc-cmd
cat > /run/service/svc-cmd/run << 'S6EOF'
#!/usr/bin/execlineb -P
/usr/bin/python3 /usr/local/bin/obsidian-cmd-service.py
S6EOF
chmod +x /run/service/svc-cmd/run
cat > /run/service/svc-cmd/type << 'S6EOF'
longrun
S6EOF

echo "[cmd-setup] s6 service directory created."
echo "[cmd-setup] Setup complete!"
