"""Verify the exact supported platform build before releasing/deploying PuT."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--onebase', required=True)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.project.resolve()
    lock = json.loads((root/'platform-patches/runtime.json').read_text(encoding='utf-8'))
    app = (root/'config/app.yaml').read_text(encoding='utf-8')
    for key, expected in [('version', lock['configuration_version']),
                          ('min_engine_version', lock['minimum_engine_version'])]:
        found = re.search(r'^'+key+r':\s*[\"\x27]?([^\"\x27\s#]+)', app, re.MULTILINE)
        if not found or found[1] != expected:
            raise SystemExit(f'{key} must match platform-patches/runtime.json: {expected}')
    actual_hash = hashlib.sha256((root/lock['patch']).read_bytes()).hexdigest()
    if actual_hash != lock['patch_sha256']:
        raise SystemExit('Platform patch SHA256 differs from the supported release')
    result = subprocess.run([args.onebase, 'version'], capture_output=True, text=True,
                            encoding='utf-8', timeout=30, check=True)
    found = re.search(r'^onebase version (\S+)', result.stdout)
    if not found or found[1] != lock['build']:
        raise SystemExit(f'Unsupported platform build. Required for this release: {lock["build"]}')
    print(f'PuT {lock["configuration_version"]}: supported OneBase {lock["build"]}; patch SHA256 OK')


if __name__ == '__main__':
    main()
