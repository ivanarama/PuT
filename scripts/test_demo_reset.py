#!/usr/bin/env python3
"""Regression: an old demo refreshes to today without duplicate documents."""
import argparse
from contextlib import closing
import datetime as dt
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import os
import zipfile


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--onebase', required=True)
    args = p.parse_args()
    binary = str(Path(args.onebase).resolve())
    project = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='put-rolling-demo-') as tmp:
        assert Path(tmp).resolve().parent == Path(tempfile.gettempdir()).resolve()
        # An obsolete archive must be rejected before any database operation.
        legacy = Path(tmp)/'legacy.obz'
        with zipfile.ZipFile(legacy, 'w') as archive:
            archive.writestr('META.txt', 'onebase_full_export\nversion=1\n')
        guard_env = dict(os.environ, DATABASE_URL='postgres://invalid.invalid/never_connect')
        rejected = subprocess.run([sys.executable, '-X', 'utf8', str(project/'scripts/reset_demo.py'),
                                   '--onebase', binary, '--baseline', str(legacy), '--demo-only'],
                                  env=guard_env, capture_output=True, text=True, encoding='utf8', timeout=10)
        assert rejected.returncode != 0 and 'universal v2' in rejected.stderr, rejected.stderr
        print('LEGACY BASELINE REJECTED BEFORE DATABASE ACCESS')
        database = str(Path(tmp) / 'demo.db')
        def run(*command):
            result = subprocess.run([binary, '--no-gui', *command], cwd=project,
                                    capture_output=True, text=True, encoding='utf8', timeout=120)
            if result.returncode:
                raise AssertionError(result.stdout + result.stderr)
            return result.stdout
        target = ['--project', str(project), '--sqlite', database]
        run('migrate', *target)
        old = dt.date.today().replace(year=dt.date.today().year - 1, day=1)
        run('procrun', *target, '--proc', 'ЗаполнитьТестовуюБазу', '--set', 'ОпорнаяДата='+old.isoformat())
        def sales():
            with closing(sqlite3.connect(database)) as db:
                total = db.execute('select count(*) from реализациятоваров').fetchone()[0]
                current = db.execute('select count(*) from реализациятоваров where posted=1 and дата>=?',
                                     (dt.date.today().replace(day=1).isoformat(),)).fetchone()[0]
            return total, current
        assert sales()[1] == 0, 'old fixture must have no current-month sales'
        for repeat in range(2):
            result = subprocess.run([sys.executable, '-X', 'utf8', str(project/'scripts/reset_demo.py'),
                                     '--onebase', binary, '--sqlite', database, '--demo-only'],
                                    cwd=project, capture_output=True, text=True, encoding='utf8', timeout=120)
            assert result.returncode == 0, result.stdout+result.stderr
            metrics = json.loads(result.stdout.strip().splitlines()[-1])
            assert metrics['sales'] > 0 and metrics['revenue'] > 0, metrics
            assert sales()[0] == 7, 'repeat reset must not duplicate sales'
            verify_stage_examples(database)
            print('rolling reset', repeat+1, metrics)
        before = sales()
        run('procrun', *target, '--proc', 'ЗаполнитьТестовуюБазу')
        assert sales() == before, 'additive refill must not duplicate fulfillment documents'
        verify_stage_examples(database)
        run('procrun', *target, '--proc', 'ДополнитьДемоЗаказы', '--set', 'ДемоБаза=true')
        assert sales() == before, 'dedicated additive refill must not duplicate fulfillment documents'
        verify_stage_examples(database)
        # The first day of a month and leap day still contain an anchor-day sale.
        for anchor in ['2026-01-01', '2024-02-29']:
            run('procrun', *target, '--proc', 'ЗаполнитьТестовуюБазу', '--set', 'Очистить=true',
                '--set', 'ОпорнаяДата='+anchor)
            with closing(sqlite3.connect(database)) as db:
                boundary = dt.datetime.fromisoformat(anchor).astimezone().astimezone(dt.timezone.utc)
                start = boundary.isoformat().replace('+00:00', 'Z')
                end = (boundary + dt.timedelta(days=1)).isoformat().replace('+00:00', 'Z')
                count = db.execute('select count(*) from реализациятоваров where posted=1 and дата>=? and дата<?',
                                   (start, end)).fetchone()[0]
                assert count > 0, anchor
        # The queued import uses the same procedure; retries must not duplicate items.
        def import_items(items):
            return subprocess.run([binary, '--no-gui', 'procrun', *target,
                                   '--proc', 'ИмпортНоменклатуры', '--set',
                                   'ФайлJSON='+json.dumps(items, ensure_ascii=False)],
                                  cwd=project, capture_output=True, text=True, encoding='utf8', timeout=30)
        item = {'Наименование':'Regression: imported item', 'Артикул':'PUT-IMPORT-REGRESSION'}
        for _ in range(2):
            imported = import_items([item])
            assert imported.returncode == 0, imported.stderr
        failed = import_items([{'Наименование':'Must roll back', 'Артикул':'PUT-ROLLBACK'}, {}])
        assert failed.returncode != 0, 'invalid import must fail'
        with closing(sqlite3.connect(database)) as db:
            assert db.execute('select count(*) from номенклатура where артикул=?',
                              ('PUT-IMPORT-REGRESSION',)).fetchone()[0] == 1
            assert db.execute('select count(*) from номенклатура where артикул=?',
                              ('PUT-ROLLBACK',)).fetchone()[0] == 0
        print('IMPORT IDEMPOTENCY AND ROLLBACK OK')
        print('DEMO RESET REGRESSION OK')


def verify_stage_examples(database):
    expected = {'Новый', 'Принят', 'НаОбеспечении', 'ВРаботе', 'Готов', 'Завершён', 'Отменён'}
    with closing(sqlite3.connect(database)) as db:
        for table,register,dimension in [
            ('заказпокупателя', 'рег_резервытоваров', 'заказпокупателя_id'),
            ('заказпоставщику', 'рег_товарывпути', 'заказпоставщику_id'),
        ]:
            orders = db.execute(f'SELECT id,состояние,posted FROM {table} WHERE комментарий LIKE ?',
                                ('Демо этапов: %',)).fetchall()
            assert len(orders) == 7 and {row[1] for row in orders} == expected, (table, orders)
            for identity,stage,posted in orders:
                assert bool(posted) == (stage != 'Новый'), (table, stage, posted)
                balance = db.execute(f'''SELECT coalesce(sum(CASE WHEN вид_движения='Приход'
                    THEN CAST(количество AS NUMERIC) ELSE -CAST(количество AS NUMERIC) END),0)
                    FROM {register} WHERE {dimension}=?''', (identity,)).fetchone()[0]
                assert balance == (1 if stage in {'Принят','НаОбеспечении','ВРаботе','Готов'} else 0), (table, stage, balance)
                if stage == 'Завершён':
                    fulfillment = 'реализациятоваров' if table == 'заказпокупателя' else 'поступлениетоваров'
                    assert db.execute(f'SELECT count(*) FROM {fulfillment} WHERE {dimension}=? AND posted=1',
                                      (identity,)).fetchone()[0] == 1, (table, stage)


if __name__ == '__main__':
    main()
