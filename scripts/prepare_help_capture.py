"""Resolve demonstration record IDs for OneBase docs capture; never writes the DB."""
import argparse
import datetime as dt
import json
from pathlib import Path
import sqlite3
from string import Template
from urllib.parse import urlparse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sqlite', type=Path, required=True)
    parser.add_argument('--base-url', default='http://127.0.0.1:8100')
    parser.add_argument('--output', type=Path, default=Path('.local/help-capture.json'))
    args = parser.parse_args()
    url = urlparse(args.base_url)
    if url.scheme not in ('http', 'https') or not url.netloc or url.username or url.password:
        parser.error('--base-url must be an HTTP(S) URL without credentials')
    with sqlite3.connect(args.sqlite.resolve().as_uri() + '?mode=ro', uri=True) as db:
        def scalar(query, params=()):
            row = db.execute(query, params).fetchone()
            if not row or not row[0]:
                raise SystemExit('Demo fixture missing: ' + query)
            return row[0]
        values = {
            'BASE_URL': args.base_url.rstrip('/'),
            'CUSTOMER': scalar('select id from контрагент where наименование like ?', ('%Маленький стульчик%',)),
            'PRODUCT': scalar('select id from номенклатура where наименование like ?', ('%Внезапно Зашатался%',)),
            'ORDER': scalar('select id from заказпокупателя order by номер limit 1'),
            'SPEC': scalar("select с.id from спецификацииноменклатуры с join номенклатура н on н.id=с.номенклатура_id where с.deletion_mark=0 order by case when н.наименование like '%Столовый%' then 0 else 1 end, с.наименование limit 1"),
            'JOB': scalar("select id from _job_queue where job_name='ФонЗакрытиеМесяца' and status='done' order by finished_at desc limit 1"),
            'MONTH_START': dt.date.today().replace(day=1).isoformat(),
            'TODAY': dt.date.today().isoformat(),
        }
        values['ASSEMBLY_PRODUCT'] = scalar('select номенклатура_id from спецификацииноменклатуры where id=?', (values['SPEC'],))
    root = Path(__file__).resolve().parents[1]
    template = (root / 'docs/help/screenshots.template.json').read_text(encoding='utf-8')
    # JSON-escape each replacement rather than interpolating arbitrary text as JSON.
    rendered = Template(template).substitute({k: json.dumps(v, ensure_ascii=False)[1:-1] for k, v in values.items()})
    scenario = json.loads(rendered)
    for shot in scenario['screenshots']:
        shot.setdefault('hide', []).extend(['#ob-ai-btn', '#ob-msg-bar'])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(scenario, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{len(scenario["screenshots"])} screenshots: {args.output}')


if __name__ == '__main__':
    main()
