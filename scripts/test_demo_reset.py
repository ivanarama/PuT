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
import uuid


def check_file_rollback(root):
    from reset_demo_postgres import switch_demo_files

    live, baseline = root/'live', root/'baseline'
    live.mkdir()
    baseline.mkdir()
    (live/'same.bin').write_bytes(b'before')
    (live/'extra.bin').write_bytes(b'user attachment')
    (baseline/'same.bin').write_bytes(b'baseline')
    (baseline/'new.bin').write_bytes(b'new')
    try:
        with switch_demo_files(live, baseline, root/'backup-failure', owner=None):
            assert (live/'same.bin').read_bytes() == b'baseline'
            assert not (live/'extra.bin').exists()
            raise RuntimeError('simulated validation failure')
    except RuntimeError as error:
        assert str(error) == 'simulated validation failure'
    assert (live/'same.bin').read_bytes() == b'before'
    assert (live/'extra.bin').is_file() and not (live/'new.bin').exists()
    with switch_demo_files(live, baseline, root/'backup-success', owner=None):
        assert (live/'new.bin').is_file()
    assert (root/'backup-success'/'same.bin').read_bytes() == b'before'
    assert (live/'same.bin').read_bytes() == b'baseline' and not (live/'extra.bin').exists()


def check_goods_in_transit(run, project, root, database):
    # Older orders kept transit on the header warehouse even when the line
    # routed the physical receipt to another warehouse.
    legacy = root/'transit.db'
    order, receipt, partial, last_closure = [str(uuid.uuid4()) for _ in range(4)]
    dates = ['2030-01-10', '2030-01-11', '2030-01-12', '2030-01-13']
    with closing(sqlite3.connect(database)) as source, closing(sqlite3.connect(legacy)) as db:
        source.backup(db)
        warehouses = [row[0] for row in db.execute('SELECT id FROM склад LIMIT 2')]
        main, remote = warehouses
        item = db.execute('SELECT id FROM номенклатура LIMIT 1').fetchone()[0]
        def insert(table, **fields):
            fields.setdefault('id', str(uuid.uuid4()))
            db.execute(f"INSERT INTO {table} ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})",
                       list(fields.values()))
        for day, kind, doc, qty, moved in zip(
            dates,
            ['ЗаказПоставщику', 'ПоступлениеТоваров', 'ЗакрытиеЗаказовПоставщикам', 'ЗакрытиеЗаказовПоставщикам'],
            [order, receipt, partial, last_closure], [10, 2, 3, 12], [10, 2, 3, 5]
        ):
            moment = day+' 12:00:00+00:00'
            header = dict(id=doc, дата=moment, номер='CI-'+day, posted=1, склад_id=main)
            line = dict(parent_id=doc, строка=1, количество=qty, номенклатура_id=item, склад_id=remote)
            if kind == 'ПоступлениеТоваров':
                header['заказпоставщику_id'] = order
            if kind == 'ЗакрытиеЗаказовПоставщикам':
                line.update(заказпоставщику_id=order, склад_id=main)
            insert(kind.lower(), **header)
            suffix = '_заказы' if kind == 'ЗакрытиеЗаказовПоставщикам' else '_товары'
            insert(kind.lower()+suffix, **line)
            insert('рег_товарывпути', recorder_type=kind, recorder=doc, period=moment, заказпоставщику_id=order,
                   line_number=1, номенклатура_id=item, склад_id=main, количество=moved, сумма=0,
                   вид_движения='Приход' if kind == 'ЗаказПоставщику' else 'Расход')
        db.commit()

    label = 'Количество в пути расходится со строками документа'
    def findings(day):
        output = run('procrun', '--project', str(project), '--sqlite', str(legacy), '--proc', 'ЗакрытиеМесяца',
                     '--set', 'ТолькоСверка=true', '--set', 'ДатаОкончания='+day)
        return [line for line in output.splitlines() if label in line]

    # Requested 12 after receiving 2 and cancelling 3 legitimately closes 5.
    assert findings(dates[-1]) == []
    with closing(sqlite3.connect(legacy)) as db:
        db.execute('UPDATE рег_товарывпути SET количество=1 WHERE recorder=?', (receipt,))
        db.commit()
    assert findings(dates[0]) == []
    errors = findings(dates[1])
    assert len(errors) == 1 and receipt in errors[0] and 'значение 1' in errors[0], errors
    # At the last date the closing document should have removed 6 given the
    # actual recorded receipt of 1. Both offending registrars must be locatable.
    errors = findings(dates[-1])
    assert len(errors) == 2 and any(receipt in e for e in errors) and any(last_closure in e for e in errors), errors
    print('POSTED TRANSIT QUANTITIES, LEGACY WAREHOUSE, PARTIAL CLOSURE AND DATE CUTOFF OK')


def check_ledger_review(run, project, root, database):
    # Simulate records written by an older release. Keep the rolling-demo fixture intact.
    legacy = root/'legacy-accounting.db'
    with closing(sqlite3.connect(database)) as source, closing(sqlite3.connect(legacy)) as db:
        source.backup(db)
        db.row_factory = sqlite3.Row
        table = 'поступлениенарасчётныйсчёт'
        payment = dict(db.execute(f'SELECT * FROM {table} WHERE posted=1 LIMIT 1').fetchone())
        db.execute(f"UPDATE {table} SET номерплатёжки='LEGACY-11' WHERE id=?", (payment['id'],))
        payment.update(id=str(uuid.uuid4()), номер='LEGACY-SECOND', номерплатёжки='LEGACY-11', ключимпортабанка=None)
        db.execute(f"INSERT INTO {table} ({','.join(payment)}) VALUES ({','.join('?' for _ in payment)})",
                   list(payment.values()))
        db.execute("UPDATE возвратотпокупателя SET сумма='9000000' WHERE posted=1")
        db.execute("UPDATE возвратотпокупателя_товары SET сумма='9000000' WHERE parent_id IN "
                   "(SELECT id FROM возвратотпокупателя WHERE posted=1 AND основание_id IS NOT NULL)")
        accrual = db.execute("SELECT id, recorder FROM рег_взаиморасчеты WHERE recorder_type='РеализацияТоваров' LIMIT 1").fetchone()
        db.execute("DELETE FROM рег_взаиморасчеты WHERE id=?", (accrual['id'],))
        db.commit()
    target = ['--project', str(project), '--sqlite', str(legacy)]
    out = run('procrun', *target, '--proc', 'ЗакрытиеМесяца', '--set', 'ТолькоСверка=true',
              '--set', 'ДатаОкончания='+dt.date.today().isoformat())
    assert 'Возвраты превышают сумму реализации' in out and out.count('Возможный дубль платёжки') >= 2, out
    assert 'Возвраты превышают сумму строки реализации' in out, out
    assert any('Начисленный долг расходится с суммой документа' in line and accrual['recorder'] in line
               for line in out.splitlines()), out
    with closing(sqlite3.connect(legacy)) as db:
        assert db.execute("SELECT count(*) FROM возвратотпокупателя WHERE сумма='9000000'").fetchone()[0] > 0

    empty = ['--project', str(project), '--sqlite', str(root/'closing.db')]
    run('migrate', *empty)
    for until in ['2026-10-31', '2026-09-30']:
        run('procrun', *empty, '--proc', 'ЗакрытиеМесяца', '--set', 'УстановитьДатуЗапрета=true',
            '--set', 'ДатаОкончания='+until)
    with closing(sqlite3.connect(empty[-1])) as db:
        stored = db.execute("SELECT value FROM _constants WHERE name='ДатаЗапретаРедактирования'").fetchone()[0]
        assert json.loads(stored).startswith('2026-10-31'), stored


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--onebase', required=True)
    args = p.parse_args()
    binary = str(Path(args.onebase).resolve())
    project = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='put-rolling-demo-') as tmp:
        assert Path(tmp).resolve().parent == Path(tempfile.gettempdir()).resolve()
        check_file_rollback(Path(tmp))
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
        check_goods_in_transit(run, project, Path(tmp), database)
        check_ledger_review(run, project, Path(tmp), database)
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
