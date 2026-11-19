"""Check the PuT receiving and cash-sale workstations against an isolated demo database."""
import argparse
from contextlib import closing
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import secrets
import shutil
import socket
import sqlite3
import subprocess
import tempfile
import time
from urllib.error import URLError
from urllib.request import urlopen
import uuid

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = 'Табурет «Шаткий-2000»'
BARCODE = '012345678905'


def sql_one(db, query, *args):
    return db.execute(query, args).fetchone()[0]


def form_event(page, action):
    with page.expect_response(lambda r: '/form-event' in r.url and r.request.method == 'POST') as event:
        action()
    response = event.value
    assert response.ok
    response.body()
    return response


def open_workplace(page, base, workplace):
    form_event(page, lambda: page.goto(base + '/ui/processor/' + workplace))


def purchase_plan(context, db, base):
    owner, vendor = db.execute("select организация_id, поставщик_id from заказпоставщику where комментарий='workplace-test'").fetchone()
    other = sql_one(db, "select id from организация where наименование='Владелец инвентаризации АРМ'")
    store = sql_one(db, "select id from склад where наименование='Общий склад для плана закупок'")
    products = dict(db.execute("select артикул,id from номенклатура where наименование='Одноимённый товар для закупок'"))
    expected = {products['PLAN-1']: (10, 0, 0, 10), products['PLAN-2']: (5, 0, 2, 3)}

    def calculate(page):
        form_event(page, page.get_by_role('button', name='Рассчитать потребность', exact=False).click)
        rows = json.loads(page.locator('[name="tp_json.Потребность"]').input_value())
        return {r['Номенклатура']: tuple(float(r[k]) for k in ('Заказано', 'Остаток', 'ВПути', 'КЗаказу')) for r in rows}

    def select_owner(page, org):
        field = page.locator('[name="Организация"]')
        if field.input_value() != org:
            form_event(page, lambda: field.select_option(org))

    def open_plan(org):
        page = context.new_page()
        open_workplace(page, base, 'ПланЗакупок')
        select_owner(page, org)
        form_event(page, lambda: page.locator('[name="Склад"]').select_option(store))
        page.locator('[name="Поставщик"]').select_option(vendor)
        page.get_by_role('button', name='Потребность', exact=True).click()
        return page

    page = open_plan(other)
    # Simulate balances recorded before the owner attribute existed.
    backfill = (ROOT / 'scripts/backfill_reservation_owners.sql').read_text(encoding='utf8')
    for old_key in (None, ''):
        missing = db.execute("update рег_резервытоваров set ключорганизации=? where склад_id=?", (old_key, store)).rowcount
        db.commit()
        response = form_event(page, page.get_by_role('button', name='Рассчитать потребность', exact=False).click).json()
        assert not response['ok'] and 'выполнить перенос владельцев резервов' in response['error'], response
        assert missing == 3 and db.execute(backfill).rowcount == missing
        assert db.execute(backfill).rowcount == 0
        db.commit()
    current = calculate(page)
    assert current == {products['PLAN-1']: (12, 7, 4, 1)}, (current, page.locator('body').inner_text()[-1000:])
    page.get_by_role('button', name='Параметры', exact=True).click()
    select_owner(page, owner)
    page.get_by_role('button', name='Потребность', exact=True).click()
    assert json.loads(page.locator('[name="tp_json.Потребность"]').input_value()) == []
    assert calculate(page) == expected
    stale = open_plan(owner)
    assert calculate(stale) == expected

    def orders():
        return db.execute("""select id, posted from заказпоставщику where организация_id=? and склад_id=?
                             and комментарий='Создан из АРМ Закупок по дефициту'""", (owner, store)).fetchall()

    create = page.get_by_role('button', name='Создать заказ поставщику', exact=False)
    db.execute("""create trigger reject_purchase_movement before insert on рег_товарывпути
                  begin select raise(abort, 'purchase test failure'); end""")
    db.commit()
    form_event(page, create.click)
    page.get_by_text('purchase test failure', exact=False).first.wait_for()
    assert orders() == []
    db.execute('drop trigger reject_purchase_movement')
    db.commit()
    form_event(page, create.click)
    [(order, posted)] = orders()
    assert posted == 1
    amount = float(sql_one(db, "select сумма from заказпоставщику where id=?", order))
    assert amount == 653, amount
    requested = {product: row[3] for product, row in expected.items()}
    for table, field in [('заказпоставщику_товары', 'parent_id'), ('рег_товарывпути', 'recorder')]:
        lines = db.execute(f'select номенклатура_id, cast(количество as numeric) from {table} where {field}=?', (order,)).fetchall()
        assert len(lines) == len(requested) and dict(lines) == requested, lines
    form_event(stale, stale.get_by_role('button', name='Создать заказ поставщику', exact=False).click)
    stale.get_by_text('Потребность изменилась', exact=False).first.wait_for()
    assert orders() == [(order, 1)]
    assert calculate(page) == {products['PLAN-1']: (10, 0, 10, 0), products['PLAN-2']: (5, 0, 5, 0)}


def receipt(page, db, base):
    order = sql_one(db, "select id from заказпоставщику where комментарий='workplace-test'")
    open_workplace(page, base, 'ПриёмкаТовара')
    form_event(page, lambda: page.locator('[name="ЗаказПоставщику"]').select_option(order))
    page.get_by_role('button', name='Товары', exact=True).click()
    fill = page.get_by_role('button', name='Заполнить', exact=False)
    field = page.locator('[name="tp_json.Товары"]')
    fill.click()
    page.wait_for_function('document.querySelector(\'[name="tp_json.Товары"]\').value.includes("СтрокаЗаказа")')
    lines = json.loads(field.input_value())
    assert len(lines) == 2 and {float(r['Цена']) for r in lines} == {50, 100}, lines
    assert all(r['Номенклатура'] == sql_one(db, 'select id from номенклатура where наименование=?', PRODUCT) for r in lines)
    assert len({r['ЗаказПокупателя'] for r in lines}) == 2
    page.get_by_role('button', name='Создать поступление', exact=False).click()
    page.get_by_text('на 240 проведено', exact=False).wait_for()
    row = db.execute('select id, способучетандс, суммабезндс, суммандс, сумма from поступлениетоваров where заказпоставщику_id=? and posted=1', (order,)).fetchone()
    assert row and row[1:] == ('Сверху', '200', '40', '240'), row
    received = db.execute('select строказаказа,заказпокупателя_id,цена from поступлениетоваров_товары where parent_id=? order by строка', (row[0],)).fetchall()
    assert [(int(n), customer, float(price)) for n, customer, price in received] == [
        (int(r['СтрокаЗаказа']), r['ЗаказПокупателя'], float(r['Цена'])) for r in lines
    ]
    fill.click()
    page.get_by_text('По заказу нет товаров в пути', exact=False).wait_for()
    assert json.loads(field.input_value()) == []


def shipment(page, db, base):
    customer = sql_one(db, "select id from контрагент where наименование='Покупатель АРМ'")
    open_workplace(page, base, 'ОтгрузкаЗаказов')
    page.locator('[name="Покупатель"]').select_option(customer)
    page.locator('[name="Склад"]').select_option(sql_one(db, "select id from склад where наименование like '%Главный%'"))
    page.get_by_role('button', name='К отгрузке', exact=True).click()
    page.get_by_role('button', name='Заполнить к отгрузке', exact=False).click()
    page.get_by_text('Заполнено строк к отгрузке: 2', exact=True).first.wait_for()
    lines = json.loads(page.locator('[name="tp_json.Строки"]').input_value())
    assert sorted(float(r['КОтгрузке']) for r in lines) == [1, 2]
    page.get_by_role('button', name='Создать реализации', exact=False).click()
    page.get_by_text('Создано реализаций: 2', exact=True).first.wait_for()
    assert sql_one(db, "select count(*) from реализациятоваров where покупатель_id=? and posted=1", customer) == 2


def checkout(page, db, base):
    item = sql_one(db, 'select id from номенклатура where наименование=?', PRODUCT)
    customer = sql_one(db, "select id from контрагент where вид='Покупатель' and типценпродажи_id is not null limit 1")
    store = sql_one(db, "select id from склад where наименование like '%Главный%'")
    cash = sql_one(db, "select id from касса where вид='Касса' limit 1")
    bank = sql_one(db, "select id from касса where вид='БанковскийСчёт' limit 1")
    db.execute('insert into штрихкоды (id,штрихкод,номенклатура_id,deletion_mark,_version) values (?,?,?,0,1)', (str(uuid.uuid4()), BARCODE, item))
    db.commit()
    open_workplace(page, base, 'РабочееМестоПродаж')
    form_event(page, lambda: page.locator('[name="Покупатель"]').select_option(customer))
    page.locator('[name="Склад"]').select_option(store)
    cashier = page.locator('[name="Касса"]')
    form_event(page, lambda: cashier.select_option(bank))
    page.get_by_text('Для оплаты наличными выберите кассу.', exact=True).wait_for()
    assert not cashier.input_value()
    form_event(page, lambda: cashier.select_option(cash))
    page.locator('input[type=checkbox][name="ОплатитьСразу"]').check()
    scan = page.locator('[name="Штрихкод"]')
    scan.fill(BARCODE)
    form_event(page, lambda: scan.press('Tab'))
    page.get_by_text('Добавлено: ' + PRODUCT, exact=True).first.wait_for()
    page.get_by_role('button', name='Товары', exact=True).click()
    finish = page.get_by_role('button', name='Оформить продажу', exact=False)

    def counts():
        return tuple(sql_one(db, 'select count(*) from ' + table) for table in
                     ('реализациятоваров', 'приходныйкассовыйордер', 'рег_партиитоваров', 'рег_денежныесредства'))

    before = counts()
    db.execute("""create trigger reject_test_payment before insert on приходныйкассовыйордер
                  begin select raise(abort, 'payment test failure'); end""")
    db.commit()
    form_event(page, finish.click)
    assert 'payment test failure' in page.locator('body').inner_text(), page.locator('body').inner_text()[-950:]
    assert counts() == before
    assert len(json.loads(page.locator('[name="tp_json.Товары"]').input_value())) == 1
    db.execute('drop trigger reject_test_payment')
    db.commit()
    finish.click()
    page.get_by_text('проведена; ПКО №', exact=False).first.wait_for()
    after = counts()
    assert after[0:2] == (before[0] + 1, before[1] + 1)
    assert after[2] > before[2] and after[3] == before[3] + 1


def director_view(page, base):
    page.goto(base + '/ui/')
    links = page.locator('a[href]').evaluate_all('(links) => links.map(a => decodeURIComponent(new URL(a.href).pathname))')
    assert '/ui/processor/ПробитьЧек' not in links
    response = page.goto(base + '/ui/page/СверкаУчета')
    assert response.ok and 'Строк для проверки:' in page.locator('body').inner_text(), (response.status, page.locator('body').inner_text()[-1100:])
    response = page.goto(base + '/ui/report/АнализЗаказовПокупателей')
    assert response.ok
    page.get_by_role('button', name='Сформировать', exact=False).first.click()
    page.get_by_text(PRODUCT, exact=True).first.wait_for()
    available = page.locator('tr').filter(has_text='Можно отгрузить на выбранную дату').first
    assert datetime.now().strftime('%d.%m.%Y') in available.inner_text()


def inventory(page, db, base):
    open_workplace(page, base, 'ИнвентаризацияСклада')
    owner = sql_one(db, "select id from организация where наименование='Владелец инвентаризации АРМ'")
    store = sql_one(db, "select id from склад where наименование like '%Главный%'")
    form_event(page, lambda: page.locator('[name="Организация"]').select_option(owner))
    if page.locator('[name="Склад"]').input_value() != store:
        form_event(page, lambda: page.locator('[name="Склад"]').select_option(store))
    page.get_by_role('button', name='Ведомость', exact=True).click()
    form_event(page, page.get_by_role('button', name='Заполнить учётные остатки', exact=False).click)
    assert 'Заполнено позиций: 2' in page.locator('body').inner_text(), page.locator('body').inner_text()[-1000:]
    contents = page.locator('[name="tp_json.Ведомость"]')
    rows = json.loads(contents.input_value())
    assert len(rows) == 2 and all(float(r['Учёт']) == 5 for r in rows)
    assert sql_one(db, 'select id from номенклатура where наименование=?', PRODUCT) in {r['Номенклатура'] for r in rows}
    for number, actual in enumerate((6, 4)):
        cell = page.locator('.slick-row').nth(number).locator('.slick-cell').nth(2)
        cell.dblclick()
        editor = cell.locator('input')
        editor.fill(str(actual))
        form_event(page, lambda: editor.press('Tab'))
    finish = page.get_by_role('button', name='Оформить излишки и недостачи', exact=False)
    def counts():
        return tuple(sql_one(db, 'select count(*) from ' + name + ' where организация_id=?', owner)
                     for name in ('оприходованиетоваров', 'списаниетоваров'))
    before = counts()
    db.execute("""create trigger reject_test_loss before insert on списаниетоваров
                  begin select raise(abort, 'inventory test failure'); end""")
    db.commit()
    finish.click()
    page.get_by_text('inventory test failure', exact=False).first.wait_for()
    assert counts() == before and len(json.loads(contents.input_value())) == 2
    db.execute('drop trigger reject_test_loss')
    db.commit()
    finish.click()
    page.get_by_text('Оформлено: Оприходование', exact=False).first.wait_for()
    assert counts() == (before[0] + 1, before[1] + 1)
    assert json.loads(contents.input_value()) == []
    assert sql_one(db, """select cast(т.цена as numeric) from оприходованиетоваров_товары т
                          join оприходованиетоваров д on д.id=т.parent_id
                          where д.организация_id=? and д.причина='Излишки по инвентаризации (АРМ)'""", owner) == 321



def reports(cli, db):
    def rows(name, **params):
        result = cli('report', 'explain', name, '--sample', '300', '--json', '--params',
                     json.dumps(params, ensure_ascii=False), capture_output=True)
        return json.loads(result.stdout)['rows']

    stock = next(r for r in rows('СвободныеОстатки') if r['номенклатура'] == PRODUCT and 'Главный' in r['склад'] and r['резерв'] > 0)
    def quantity(register):
        owner_filter = "" if register == 'рег_резервытоваров' else " and r.организация_id=(select id from организация where наименование=?)"
        params = (PRODUCT, stock['склад']) + ((stock['организация'],) if owner_filter else ())
        return sql_one(db, f"""select sum(case when r.вид_движения='Приход' then r.количество else -r.количество end)
                              from {register} r join номенклатура n on n.id=r.номенклатура_id
                              join склад w on w.id=r.склад_id where n.наименование=? and w.наименование=?{owner_filter}""", *params)
    reserve = quantity('рег_резервытоваров')
    assert reserve > 0 and stock['резерв'] == reserve
    assert stock['количество'] == quantity('рег_партиитоваров') - reserve

    # A negative historical FIFO lot at a different owner must stay visible under its own filter.
    other = str(uuid.uuid4())
    db.execute('insert into организация (id, наименование, deletion_mark, _version) values (?, ?, 0, 1)',
               (other, 'Вторая организация АРМ'))
    db.execute("""insert into рег_партиитоваров
                  (id, recorder, recorder_type, line_number, period, вид_движения, номенклатура_id,
                   склад_id, документпоступления_id, датапоставки, организация_id, количество, сумма, суммасндс)
                  select ?, ?, recorder_type, 1, period, 'Расход', номенклатура_id, склад_id,
                         документпоступления_id, датапоставки, ?, 5, 50, 60 from рег_партиитоваров
                  where номенклатура_id=(select id from номенклатура where наименование=?)
                    and склад_id=(select id from склад where наименование=?) limit 1""",
               (str(uuid.uuid4()), str(uuid.uuid4()), other, PRODUCT, stock['склад']))
    db.commit()
    other_rows = rows('СвободныеОстатки', Организация=other)
    assert len(other_rows) == 1 and other_rows[0]['наскладе'] == -5 and other_rows[0]['резерв'] == 0
    original = next(r for r in rows('СвободныеОстатки') if r['номенклатура'] == PRODUCT and r['склад'] == stock['склад']
                    and r['организация'] == stock['организация'])
    assert original == stock

    for report, field, table, accrual in (
        ('ОплатыРеализаций', 'документреализации', 'реализациятоваров', 'Приход'),
        ('ОплатыПоступлений', 'документпоступления', 'поступлениетоваров', 'Расход'),
    ):
        data = db.execute(f"""select doc.номер, r.period, r.вид_движения, r.сумма
                              from рег_взаиморасчеты r join {table} doc on doc.id=r.{field}_id
                              order by r.period""").fetchall()
        amounts = {}
        for number, moment, movement, amount in data:
            day = datetime.fromisoformat(moment).astimezone().date().isoformat()
            amounts.setdefault(number, []).append((day, Decimal(amount) if movement == accrual else -Decimal(amount)))
        number, entries = next((n, a) for n, a in amounts.items()
                               if a[0][0] < a[-1][0] and a[-1][1] < 0)
        day = entries[-1][0]
        row = next(r for r in rows(report, НачалоПериода=day, КонецПериода=day, НаДату=day) if r[field] == number)
        opening = sum(value for date, value in entries if date < day)
        assert Decimal(str(row['начальныйостаток'])) == opening and opening > 0
        assert Decimal(str(row['остаток'])) == sum(value for _, value in entries), (report, number, entries, row)

    order = sql_one(db, "select номер from заказпоставщику where комментарий='workplace-test'")
    supply = rows('АнализЗаказовПоставщикам')
    received = [r for r in supply if r['заказпоставщику'] == order]
    assert sorted(r['поступило'] for r in received) == [1, 2]
    assert all(r['последнеепоступление'] and r['количествовпути'] == 0 for r in received)
    customers = {r['заказпокупателя'] for r in received}
    demand = [r for r in rows('АнализЗаказовПокупателей') if r['заказпокупателя'] in customers]
    assert sorted(r['поступило'] for r in demand) == [1, 2]
    assert all(r['последнеепоступление'] and r['последняяотгрузка'] and r['впути'] == 0 for r in demand)
    assert sorted(r['отгружено'] for r in demand) == [1, 2]
    calendar = rows('ПлатежныйКалендарь')
    assert any(r['группасрока'] == 'Без срока' and r['предстоящаяоплата'] == 240 for r in calendar)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--onebase', required=True)
    parser.add_argument('--channel', help='Installed browser channel, e.g. msedge')
    args = parser.parse_args()
    exe = str(Path(args.onebase).resolve())
    with tempfile.TemporaryDirectory(prefix='put-workplaces-') as tmp:
        project = Path(tmp)
        for kind in ('catalogs', 'config', 'constants', 'documents', 'enums', 'forms', 'inforegs', 'journals',
                     'pages', 'printforms', 'processors', 'registers', 'reports', 'roles', 'scheduled', 'src', 'subsystems', 'widgets'):
            shutil.copytree(ROOT / kind, project / kind)
        (project / 'processors/сценарийарм.yaml').write_text('name: СценарийАРМ\ntitle: Проверка АРМ\n', encoding='utf8')
        shutil.copyfile(ROOT / 'tests/fixtures/workplaces.os', project / 'src/сценарийарм.proc.os')
        dbfile = project / 'test.db'
        options = ['--project', str(project), '--sqlite', str(dbfile)]

        def cli(*command, **kwargs):
            return subprocess.run([exe, '--no-gui', *command, *options], check=True, timeout=90,
                                  text=True, encoding='utf8', **kwargs)

        cli('migrate')
        cli('procrun', '--proc', 'ЗаполнитьТестовуюБазу')
        cli('procrun', '--proc', 'СценарийАРМ')
        password = secrets.token_hex(18)
        cli('user', 'add', 'test', '--admin', '--password-stdin', input=password)
        for login, role in [('warehouse', 'Кладовщик'), ('seller', 'Менеджер'), ('director', 'Управленец'), ('buyer', 'Снабженец')]:
            cli('user', 'add', login, '--password-stdin', input=password)
            cli('user', 'role', 'assign', login, role)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        base = f'http://127.0.0.1:{port}'
        with (project / 'server.log').open('wb') as log:
            server = subprocess.Popen([exe, '--no-gui', 'run', *options, '--host', '127.0.0.1', '--port', str(port)],
                                      stdout=log, stderr=log, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            try:
                for _ in range(120):
                    try:
                        with urlopen(base + '/login', timeout=1):
                            break
                    except URLError:
                        if server.poll() is not None:
                            raise RuntimeError((project / 'server.log').read_text(encoding='utf8'))
                        time.sleep(.25)
                with sync_playwright() as runtime, closing(sqlite3.connect(dbfile)) as db:
                    browser = runtime.chromium.launch(channel=args.channel)
                    def login_context(login):
                        context = browser.new_context(locale='ru-RU')
                        context.set_default_timeout(10000)
                        response = context.request.post(base + '/login', form={'login': login, 'password': password},
                                                        headers={'Origin': base, 'Referer': base + '/login'})
                        assert response.ok
                        return context

                    warehouse = login_context('warehouse')
                    page = warehouse.new_page()
                    receipt(page, db, base)
                    shipment(page, db, base)
                    inventory(page, db, base)
                    warehouse.close()
                    buyer = login_context('buyer')
                    purchase_plan(buyer, db, base)
                    buyer.close()
                    seller = login_context('seller')
                    checkout(seller.new_page(), db, base)
                    seller.close()
                    director = login_context('director')
                    director_view(director.new_page(), base)
                    director.close()
                    context = login_context('test')
                    from verify_queue_ui import check_queue_and_diagnostics
                    check_queue_and_diagnostics(context, base, project, db)
                    from verify_payment_ui import check_payment_allocation
                    check_payment_allocation(context, db, base)
                    browser.close()
            finally:
                server.terminate()
                server.wait(timeout=20)
        with closing(sqlite3.connect(dbfile)) as db:
            from verify_payment_ui import check_allocated_exchange
            check_allocated_exchange(cli, db, project)
            reports(cli, db)
    print('OK: receiving, settlements, availability, payment calendar and transactional checkout')


if __name__ == '__main__':
    main()
