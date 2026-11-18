"""Check the six operational reports against a populated PostgreSQL demo."""
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

    stock = rows('СвободныеОстатки', НаДату=today)
    assert all(Decimal(str(r['наскладе'])) - Decimal(str(r['резерв'])) == Decimal(str(r['количество'])) for r in stock)
    rows('АнализЗаказовПоставщикам')
    rows('АнализЗаказовПокупателей', НаДату=today)
    rows('ПлатежныйКалендарь', НаДату=today)


if __name__ == '__main__':
    main()
