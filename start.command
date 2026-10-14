#!/bin/zsh
cd "$(dirname "$0")" || exit 1
NODE_BIN="$(command -v node 2>/dev/null)"
if [[ -z "$NODE_BIN" && -x /opt/homebrew/bin/node ]]; then NODE_BIN=/opt/homebrew/bin/node; fi
if [[ -z "$NODE_BIN" && -x /usr/local/bin/node ]]; then NODE_BIN=/usr/local/bin/node; fi
if [[ -z "$NODE_BIN" ]] || ! "$NODE_BIN" -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 20 ? 0 : 1)'; then
  echo '需要 Node.js 20 或更高版本。'
  read -r '?按回车退出…'
  exit 1
fi
"$NODE_BIN" node/server.mjs
