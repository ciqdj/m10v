#!/usr/bin/env bash
# Run once as root in the existing production checkout. Secret is supplied as a file.
set -Eeuo pipefail
[[ $(id -u) == 0 ]]
repo=/www/wwwroot/m10v
cd "$repo"
[[ $(git remote get-url origin) =~ ^https://github.com/zhaoo/m10v(\.git)?$ ]]
[[ -s ${1:-} ]]
[[ $(wc -c < "$1") -ge 32 ]]
install -d -m 700 /etc/m10v-deploy /var/lib/m10v-deploy
install -d -m 755 /usr/local/lib/m10v-deploy
install -m 600 "$1" /etc/m10v-deploy/secret
install -m 644 deploy/github-webhook.mjs /usr/local/lib/m10v-deploy/webhook.mjs
install -m 700 skills/m10v-baota-publish/scripts/update-server.sh /usr/local/lib/m10v-deploy/update-server.sh
cat > /etc/systemd/system/m10v-deploy.service <<'UNIT'
[Unit]
Description=M10V signed GitHub deployment receiver
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
User=root
WorkingDirectory=/var/lib/m10v-deploy
ExecStart=/usr/local/bin/m10v-node /usr/local/lib/m10v-deploy/webhook.mjs
Restart=on-failure
RestartSec=5
UMask=0077
PrivateTmp=true
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now m10v-deploy
systemctl is-active m10v-deploy
printf 'WEBHOOK_INSTALLED loopback=3001 repository=zhaoo/m10v branch=main\n'
