#!/usr/bin/env python3
"""Offline reset of a disposable PuT demo, followed by current-period checks."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--onebase', default='onebase')
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--sqlite', type=Path)
    parser.add_argument('--baseline', type=Path, help='Deprecated; PostgreSQL uses reset_demo_postgres.py')
    parser.add_argument('--demo-only', action='store_true', required=True,
                        help='Confirm this target is disposable demonstration data')
    args = parser.parse_args()
    if not args.sqlite and not os.environ.get('DATABASE_URL'):
        parser.error('Specify --sqlite or DATABASE_URL; credentials are read from the environment')
    if args.baseline and args.sqlite:
        parser.error('--baseline uses the PostgreSQL demo-reset command')
    if args.baseline:
        parser.error('Use reset_demo_postgres.py with a native PostgreSQL dump for this release; universal v2 restore is not used')
    project = args.project.resolve()
    binary = str(Path(args.onebase).resolve()) if Path(args.onebase).exists() else args.onebase
    target = ['--sqlite', str(args.sqlite.resolve())] if args.sqlite else []

    def run(command, *, query=False):
        try:
            result = subprocess.run([binary, '--no-gui', *command], cwd=project,
                                    text=True, encoding='utf-8', capture_output=True, timeout=1800)
        except subprocess.TimeoutExpired:
            raise RuntimeError('onebase: превышено время выполнения операции (1800 секунд)') from None
        if result.returncode:
            # CLI errors may contain DSNs: redact before printing to a timer journal.
            secret = os.environ.get('DATABASE_URL', '')
            error = result.stderr.replace(secret, '[DATABASE_URL]') if secret else result.stderr
            raise RuntimeError(error.strip() or 'onebase command failed')
        if query:
            return json.loads(result.stdout)
        secret = os.environ.get('DATABASE_URL', '')
        output = result.stdout.replace(secret, '[DATABASE_URL]') if secret else result.stdout
        print(output.strip(), flush=True)

    # The service must be stopped: the CLI's database lock also rejects a live server.
    run(['migrate', '--project', str(project), *target])
    run(['procrun', '--project', str(project), *target, '--proc', 'ЗаполнитьТестовуюБазу',
         '--set', 'Очистить=true'])
    beginning = dt.datetime.now().astimezone().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    boundary = beginning.astimezone(dt.timezone.utc).isoformat().replace('+00:00', 'Z')
    # CLI JSON parameters are strings; PostgreSQL requires an explicit date cast.
    boundary_expression = '&Начало' if args.sqlite else 'CAST(&Начало AS TIMESTAMPTZ)'
    queries = {
        'sales': 'ВЫБРАТЬ КОЛИЧЕСТВО(*) КАК Значение ИЗ Документ.РеализацияТоваров '
                 'ГДЕ posted = Истина И Дата >= ' + boundary_expression,
        'revenue': 'ВЫБРАТЬ СУММА(ВЫБОР КОГДА вид_движения = "Приход" ТОГДА Выручка '
                   'ИНАЧЕ -Выручка КОНЕЦ) КАК Значение ИЗ РегистрНакопления.ВаловаяПрибыль '
                   'ГДЕ period >= ' + boundary_expression,
    }
    summary = {}
    for name, query in queries.items():
        data = run(['query', '--project', str(project), *target, '--json',
                    '--params', json.dumps({'Начало': boundary}), query], query=True)
        summary[name] = float(data['rows'][0]['значение'] or 0)
        if summary[name] <= 0:
            raise RuntimeError(f'Demo check failed: current-month {name} is zero')
    expected_stages = {'Новый','Принят','НаОбеспечении','ВРаботе','Готов','Завершён','Отменён'}
    stage_examples = {}
    for entity in ['ЗаказПокупателя', 'ЗаказПоставщику']:
        query = ('ВЫБРАТЬ Д.Состояние КАК Этап, КОЛИЧЕСТВО(*) КАК Количество ИЗ Документ.' + entity +
                 ' КАК Д ГДЕ Д.Комментарий ПОДОБНО &Метка СГРУППИРОВАТЬ ПО Д.Состояние')
        data = run(['query','--project',str(project),*target,'--json','--params',
                    json.dumps({'Метка':'Демо этапов: %'},ensure_ascii=False),query],query=True)
        stages = {row['этап']:int(row['количество']) for row in data['rows']}
        if set(stages) != expected_stages or any(count != 1 for count in stages.values()):
            raise RuntimeError(f'Demo check failed: {entity} stage examples are incomplete or duplicated')
        stage_examples[entity] = len(stages)
    print(json.dumps({'period': beginning.date().isoformat(), **summary, 'order_stages':stage_examples}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    try:
        main()
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from None
