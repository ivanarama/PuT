#!/usr/bin/env python3
"""Offline native PostgreSQL reset for the isolated PuT demo (run as root)."""
import argparse
from contextlib import contextmanager
import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlparse


@contextmanager
def switch_demo_files(live, baseline, backup, owner):
    """Keep the original directory available for rollback until validation finishes."""
    # Both renames must stay on the filesystem containing the live directory.
    stage = Path(tempfile.mkdtemp(prefix='.put-reset-', dir=live.parent))
    previous = stage / 'original'
    incoming = stage / 'incoming'
    try:
        shutil.copytree(live, backup, symlinks=True)
        shutil.copytree(baseline, incoming)
        if owner:
            for directory, _, files in os.walk(incoming):
                shutil.chown(directory, user=owner, group=owner)
                for name in files:
                    shutil.chown(Path(directory)/name, user=owner, group=owner)
        live.rename(previous)
        try:
            incoming.rename(live)
            yield
        except BaseException:
            if live.exists():
                live.rename(stage / 'failed')
            previous.rename(live)
            raise
        shutil.rmtree(previous)
    finally:
        # Leave the original in place for recovery if a rollback rename failed.
        if not previous.exists():
            shutil.rmtree(stage)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--onebase', required=True)
    p.add_argument('--project', type=Path, required=True)
    p.add_argument('--baseline', type=Path, required=True, help='Native pg_dump -Fc archive')
    p.add_argument('--baseline-files', type=Path, required=True)
    p.add_argument('--backups', type=Path, required=True)
    p.add_argument('--demo-only', action='store_true', required=True)
    args = p.parse_args()
    dsn = os.environ.get('DATABASE_URL', '')
    address = urlparse(dsn)
    dbname = address.path.lstrip('/')
    if address.hostname not in ('localhost', '127.0.0.1') or address.port not in (None, 5432):
        p.error('Only the local PostgreSQL instance is supported')
    if not re.fullmatch(r'put_(demo|release)_[0-9]+', dbname):
        p.error('Only isolated put_demo_<version> / put_release_<version> databases are accepted')
    if os.geteuid() != 0:
        p.error('Native restore requires root to run PostgreSQL tools as postgres')
    os.umask(0o077)
    live_files = Path(os.environ.get('ONEBASE_FILES_DIR', '')).resolve()
    expected_root = Path('/var/lib/onebase-put').resolve()
    if live_files == expected_root or expected_root not in live_files.parents or not live_files.is_dir():
        p.error('ONEBASE_FILES_DIR must be inside /var/lib/onebase-put')
    if not args.baseline.is_file() or not args.baseline_files.is_dir():
        p.error('Both native baseline and its binary files snapshot are required')
    for other in (args.baseline_files.resolve(), args.backups.resolve()):
        if other == live_files or live_files in other.parents or other in live_files.parents:
            p.error('Live files, baseline files and backups must be separate directories')
    project = args.project.resolve()
    env = dict(os.environ)
    args.backups.mkdir(parents=True, exist_ok=True)
    import fcntl
    lease = (args.backups/('reset-'+dbname+'.lock')).open('a')
    fcntl.flock(lease.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def run(command, *, stdin=None, stdout=None):
        result = subprocess.run(command, env=env, stdin=stdin, stdout=stdout or subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=1800)
        output = (result.stdout or b'').decode('utf-8', errors='replace')
        error = result.stderr.decode('utf-8', errors='replace')
        if dsn:
            output, error = output.replace(dsn, '[DATABASE_URL]'), error.replace(dsn, '[DATABASE_URL]')
        if result.returncode:
            raise RuntimeError((error or output or 'Command failed: '+command[0]).strip())
        return output

    def pg(command, *tail, **kwargs):
        return run(['runuser', '-u', 'postgres', '--', command, *tail], **kwargs)

    def sql(text):
        return pg('psql', '-d', dbname, '-At', '-v', 'ON_ERROR_STOP=1', '-c', text).strip()

    # Validate all inputs before replacing any database.
    connected = sql("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND backend_type='client backend' AND pid<>pg_backend_pid()")
    if connected != '0':
        raise RuntimeError('Stop all clients and the demo service before resetting this database')
    with args.baseline.open('rb') as source:
        pg('pg_restore', '--list', stdin=source)
    run(['python3', str(project/'scripts/check_runtime.py'), '--onebase', args.onebase])
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = args.backups.resolve()/('reset-'+dbname+'-'+stamp)
    backup.mkdir(parents=True, mode=0o700)
    os.chmod(backup, 0o700)
    available = set(sql("SELECT tablename FROM pg_tables WHERE schemaname='public'").splitlines())
    auth = [t for t in ['_users', '_roles', '_user_roles', '_sessions', '_auth_backup_codes'] if t in available]
    if not {'_users', '_roles', '_user_roles', '_sessions'}.issubset(auth):
        raise RuntimeError('Authentication tables are incomplete')
    auth_before = sql('SELECT count(*) FROM _users')
    with (backup/'before.dump').open('xb') as output:
        pg('pg_dump', '-Fc', '-d', dbname, stdout=output)
    with (backup/'auth.dump').open('xb') as output:
        pg('pg_dump', '-Fc', '--data-only', '-d', dbname,
           *[v for t in auth for v in ['-t', t]], stdout=output)

    def replace_database(dump):
        pg('dropdb', '--force', dbname)
        pg('createdb', '-O', 'onebase', dbname)
        with Path(dump).open('rb') as source:
            pg('pg_restore', '--no-owner', '--no-acl', '--role=onebase', '-d', dbname, stdin=source)

    with switch_demo_files(live_files, args.baseline_files, backup/'before-files', 'onebase'):
        try:
            replace_database(args.baseline)
            sql('TRUNCATE '+','.join(auth)+' CASCADE')
            with (backup/'auth.dump').open('rb') as source:
                pg('pg_restore', '--no-owner', '--no-acl', '--role=onebase', '-d', dbname, stdin=source)
            run(['runuser', '-u', 'onebase', '--', args.onebase, '--no-gui', 'deploy',
                          '--project', str(project), '--db', dsn, '--message', 'PuT native rolling demo reset'])
            output = run(['runuser', '-u', 'onebase', '--', 'python3', str(project/'scripts/reset_demo.py'),
                          '--onebase', args.onebase, '--project', str(project), '--demo-only'])
            summary = json.loads(output.strip().splitlines()[-1])
            if sql('SELECT count(*) FROM _users') != auth_before:
                raise RuntimeError('User count changed during demo reset')
        except BaseException:
            replace_database(backup/'before.dump')
            raise
    print(json.dumps(dict(summary, backup=str(backup), users_preserved=True), ensure_ascii=False), flush=True)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from None
