#!/usr/bin/env bash
# Run the native root/postgres/onebase reset with the release's Linux executable.
set -euo pipefail

if [[ $1 != --inside-container ]]; then
    binary=$(realpath "$1")
    project=$(cd "$(dirname "$0")/.." && pwd)
    image=$(docker build --quiet - <<'DOCKERFILE'
FROM ubuntu:24.04
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends postgresql-16 python3 util-linux && rm -rf /var/lib/apt/lists/* && useradd --create-home --user-group onebase
DOCKERFILE
    )
    exec docker run --rm --network=none \
        --mount "type=bind,src=$project,dst=/project,readonly" \
        --mount "type=bind,src=$binary,dst=/usr/local/bin/onebase,readonly" \
        "$image" bash /project/scripts/test_demo_reset_postgres.sh --inside-container
fi

[[ $(id -u) == 0 && -f /.dockerenv && ! -e /var/lib/onebase-put ]]
export PATH="/usr/lib/postgresql/16/bin:$PATH" LC_ALL=C.UTF-8 TZ=UTC ONEBASE_NO_GUI=1
work=$(mktemp -d)
chmod 755 "$work"
install -d -o postgres -g postgres "$work/db" "$work/socket"
export PGHOST="$work/socket" PGPORT=5432
runuser -u postgres -- initdb -D "$work/db" --encoding=UTF8 --locale=C.UTF-8 --auth=trust >/dev/null
runuser -u postgres -- pg_ctl -w -D "$work/db" -l "$work/db/server.log" \
    -o "-p 5432 -k $PGHOST -h 127.0.0.1" start >/dev/null
trap 'runuser -u postgres -- pg_ctl -w -m fast -D "$work/db" stop >/dev/null' EXIT

dbname=put_demo_987654
sql() { runuser -u postgres -- psql -X -qAt -v ON_ERROR_STOP=1 -d "$dbname" "$@"; }
[[ $(runuser -u postgres -- psql -XAt -d postgres -c 'show data_directory') == "$work/db" ]]
runuser -u postgres -- createuser onebase
runuser -u postgres -- createdb -O onebase "$dbname"
export DATABASE_URL="postgres://onebase@127.0.0.1:5432/$dbname?sslmode=disable"
export ONEBASE_FILES_DIR=/var/lib/onebase-put/files
install -d -o onebase -g onebase "$ONEBASE_FILES_DIR" "$work/baseline-files"
cd /tmp
binary=/usr/local/bin/onebase
runuser -u onebase -- "$binary" migrate --project /project
runuser -u onebase -- "$binary" procrun --project /project --proc ЗаполнитьТестовуюБазу >/dev/null
cp -a "$ONEBASE_FILES_DIR/." "$work/baseline-files/"
sql -c "SET ROLE onebase; CREATE TABLE reset_test_marker (value text); INSERT INTO reset_test_marker VALUES ('baseline')"
runuser -u postgres -- pg_dump -Fc -d "$dbname" >"$work/baseline.dump"
printf 'baseline\0bytes' >"$work/baseline-files/shared.bin"
printf 'baseline only' >"$work/baseline-files/baseline-only.bin"
printf 'live\0bytes' >"$ONEBASE_FILES_DIR/shared.bin"
printf 'user upload' >"$ONEBASE_FILES_DIR/upload.bin"
sql -c "UPDATE reset_test_marker SET value='live'"
printf 'native-reset-test-passphrase\n' | runuser -u onebase -- "$binary" user add smoke-operator --project /project --admin --password-stdin

reset_args=(--project /project --baseline "$work/baseline.dump" --baseline-files "$work/baseline-files" --backups "$work/backups" --demo-only)
reset=/project/scripts/reset_demo_postgres.py
auth_before=$(sql -c 'SELECT row_to_json(u)::text FROM _users u ORDER BY 1')
[[ $auth_before == *smoke-operator* ]]
python3 "$reset" --onebase "$binary" "${reset_args[@]}" >"$work/success.json"
python3 - "$work/success.json" <<'PY'
import json
import sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_text())
assert r['users_preserved'] and r['sales'] > 0 and r['revenue'] > 0, r
before = Path(r['backup']) / 'before-files'
assert (before / 'shared.bin').read_bytes() == b'live\0bytes'
assert (before / 'upload.bin').read_bytes() == b'user upload'
PY
[[ $(sql -c 'TABLE reset_test_marker') == baseline ]]
[[ $(sql -c 'SELECT row_to_json(u)::text FROM _users u ORDER BY 1') == "$auth_before" ]]
diff -qr "$work/baseline-files" "$ONEBASE_FILES_DIR"

# The only injected fault is at deploy. This point is reached after the real
# drop/create, pg_restore, auth restore and file swap have all succeeded.
sql -c "UPDATE reset_test_marker SET value='before failure'"
printf 'changed\0after success' >"$ONEBASE_FILES_DIR/shared.bin"
mkdir "$ONEBASE_FILES_DIR/incoming"
printf 'must survive rollback' >"$ONEBASE_FILES_DIR/incoming/new.bin"
rm "$ONEBASE_FILES_DIR/baseline-only.bin"
cp -a "$ONEBASE_FILES_DIR" "$work/files-before-failure"
cat >"$work/fail-on-deploy" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
if [[ ${1:-} == --no-gui && ${2:-} == deploy ]]; then
    [[ $(psql -XAt "$DATABASE_URL" -c 'TABLE reset_test_marker') == baseline ]]
    [[ -e "$ONEBASE_FILES_DIR/baseline-only.bin" && ! -e "$ONEBASE_FILES_DIR/incoming/new.bin" ]]
    echo 'CI fault after native restore and file swap' >&2
    exit 41
fi
exec /usr/local/bin/onebase "$@"
SH
chmod 755 "$work/fail-on-deploy"

# Compare every public table as a multiset of its full rows, including auth,
# movements and the configuration deployment history. Restore can change row order.
snapshot() {
    sql <<'SQL'
SELECT format('SELECT %L || '' '' || COUNT(*) || '' '' || md5(coalesce(string_agg(h, '''' ORDER BY h), '''')) FROM (SELECT md5(row_to_json(t)::text) h FROM %I.%I t) q',
              tablename, schemaname, tablename)
FROM pg_tables WHERE schemaname='public' ORDER BY tablename
\gexec
SQL
}
snapshot >"$work/db-before-failure"
if python3 "$reset" --onebase "$work/fail-on-deploy" "${reset_args[@]}" >"$work/failure.log" 2>&1; then
    echo 'Reset unexpectedly succeeded during fault injection' >&2
    exit 1
fi
if ! grep -Fq 'CI fault after native restore and file swap' "$work/failure.log"; then
    cat "$work/failure.log" >&2
    exit 1
fi
snapshot >"$work/db-after-failure"
diff -u "$work/db-before-failure" "$work/db-after-failure"
diff -qr "$work/files-before-failure" "$ONEBASE_FILES_DIR"
echo 'PostgreSQL native reset and database/file rollback passed'
