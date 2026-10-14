"""Process-isolated adapter for the locally cached GRLife browser runtime.

The runtime is not part of m10v. The source BIN and plan are local files; no
firmware bytes are sent to grlife.app by this adapter.
"""

import datetime
import json
from pathlib import Path
import sys

from reconstruction.firmware_store.browser_engine import prepare_build, build


def main():
    action, source_path, plan_path, output_path = sys.argv[1:]
    source = Path(source_path).read_bytes()
    plan = Path(plan_path).read_bytes()
    prepared = prepare_build(source, plan)
    if action == 'prepare':
        print(json.dumps(prepared, ensure_ascii=False))
        return
    if action != 'build' or not prepared['ready']:
        raise ValueError('固件或方案未通过预检。')
    consent = {
        'version': prepared['disclaimer_version'],
        'accepted': True,
        'accepted_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_sha256': prepared['source_sha256'],
        'configuration_sha256': prepared['configuration_sha256'],
    }
    candidate, receipt = build(source, plan, consent)
    Path(output_path).write_bytes(candidate)
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    main()
