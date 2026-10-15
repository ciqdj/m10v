#!/usr/bin/env bash
# Forced command for the dedicated GitHub Actions key; never evaluates remote shell text.
set -Eeuo pipefail
umask 077
if [[ ! ${SSH_ORIGINAL_COMMAND:-} =~ ^deploy\ ([0-9a-f]{40})$ ]]; then
  printf 'Only deploy FULL_COMMIT_SHA is permitted.\n' >&2; exit 2
fi
expected=${BASH_REMATCH[1]}
work=$(mktemp -d /var/lib/m10v-deploy/ssh.XXXXXX)
trap 'rm -rf -- "$work"' EXIT
python3 -c 'import sys,pathlib; data=sys.stdin.buffer.read(24*1024*1024+1); assert 0<len(data)<=24*1024*1024, "bundle size out of bounds"; pathlib.Path(sys.argv[1]).write_bytes(data)' "$work/release.bundle"
bash /usr/local/lib/m10v-deploy/update-server.sh --deploy "$expected" "$work/release.bundle" 2>&1 | tee -a /var/log/m10v-deploy-ssh.log
