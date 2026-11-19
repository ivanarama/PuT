"""Check the operational reports against a populated PostgreSQL demo."""
import argparse
from datetime import date
from decimal import Decimal
import json
import os
from pathlib import Path
import subprocess

import psycopg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--onebase', required=True)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    today = date.today().isoformat()

    def rows(name, **params):
        result = subprocess.run(
            [args.onebase, '--no-gui', 'report', 'explain', name, '--project', str(project),
             '--sample', '1000', '--json', '--params', json.dumps(params, ensure_ascii=False)],
            stdout=subprocess.PIPE, text=True, encoding='utf8', check=True,
        )
        report = json.loads(result.stdout)
        assert not report.get('error'), (name, report['error'])
        assert report.get('rows'), (name, 'empty demo result')
        print(name, len(report['rows']))
        return report['rows']

    with psycopg.connect(os.environ['DATABASE_URL']) as database:
        # Exercise the update for installations that already have reserve movements.
        with database.transaction(force_rollback=True):
            missing = database.execute("UPDATE рег_резервытоваров SET ключорганизации=NULL").rowcount
            assert missing > 0
            backfill = (project / 'scripts/backfill_reservation_owners.sql').read_text(encoding='utf8')
            assert database.execute(backfill).rowcount == missing
            assert database.execute(backfill).rowcount == 0
            assert database.execute("""SELECT count(*) FROM рег_резервытоваров р
                                      JOIN заказпокупателя з ON р.заказпокупателя_id=з.id
                                      WHERE р.ключорганизации IS DISTINCT FROM CAST(з.организация_id AS TEXT)""").fetchone()[0] == 0
        for report, field, table, accrual in (
            ('ОплатыРеализаций', 'документреализации', 'реализациятоваров', 'Приход'),
            ('ОплатыПоступлений', 'документпоступления', 'поступлениетоваров', 'Расход'),
        ):
            entries = database.execute(
                f'SELECT d.номер, r.period, r.вид_движения, r.сумма FROM рег_взаиморасчеты r '
                f'JOIN {table} d ON d.id = r.{field}_id ORDER BY r.period'
            )
            amounts = {}
            for number, moment, direction, amount in entries:
                amounts.setdefault(number, []).append((moment.astimezone().date(), amount if direction == accrual else -amount))
            number, items = next((n, v) for n, v in amounts.items() if v[0][0] < v[-1][0] and v[-1][1] < 0)
            cutoff = items[-1][0]
            day = cutoff.isoformat()
            line = next(row for row in rows(report, НачалоПериода=day, КонецПериода=day, НаДату=day) if row[field] == number)
            opening = sum(amount for moment, amount in items if moment < cutoff)
            assert Decimal(str(line['начальныйостаток'])) == opening and opening > 0, (report, number, line)
            assert Decimal(str(line['остаток'])) == sum(amount for _, amount in items), (report, number, line)

    abc = rows('ABCАнализПродаж', ПорогА=75, ПорогБ=90)
    profits = [Decimal(str(r['валоваяприбыль'])) for r in abc]
    assert profits == sorted(profits, reverse=True)
    total = sum(max(profit, 0) for profit in profits)
    cumulative = 0
    for row, profit in zip(abc, profits):
        grade = 'C'
        if profit > 0:
            if cumulative * 100 < 75 * total:
                grade = 'A'
            elif cumulative * 100 < 90 * total:
                grade = 'B'
        assert row['классabc'] == grade, row
        cumulative += max(profit, 0)
        share = Decimal(str(row['накопленнаядоляпроцент']))
        assert abs(share - (100 * cumulative / total if total else 0)) <= Decimal('0.005'), row

    stock = rows('СвободныеОстатки', НаДату=today)
    assert all(Decimal(str(r['наскладе'])) - Decimal(str(r['резерв'])) == Decimal(str(r['количество'])) for r in stock)
    rows('АнализЗаказовПоставщикам')
    rows('АнализЗаказовПокупателей', НаДату=today)
    rows('ПлатежныйКалендарь', НаДату=today)


if __name__ == '__main__':
    main()
