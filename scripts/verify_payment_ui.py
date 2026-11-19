"""Post one bank receipt through the standard form and read both settled sales in the report."""
from datetime import datetime
from decimal import Decimal
import json


def check_payment_allocation(context, db, base):
    customer = db.execute("SELECT id FROM контрагент WHERE наименование=?", ("Покупатель для распределения платежа",)).fetchone()[0]
    sales = db.execute("SELECT номер, id, CAST(сумма AS INTEGER), организация_id FROM реализациятоваров "
                       "WHERE покупатель_id=? AND posted=1 ORDER BY CAST(сумма AS INTEGER) DESC", (customer,)).fetchall()
    assert [sale[2] for sale in sales] == [6000, 4000]
    bank = db.execute("SELECT id FROM касса WHERE вид='БанковскийСчёт' LIMIT 1").fetchone()[0]
    page = context.new_page()
    try:
        page.goto(base + "/ui/document/ПоступлениеНаРасчётныйСчёт/new")
        for field, uid in [("Организация", sales[0][3]), ("Контрагент", customer), ("БанковскийСчёт", bank)]:
            page.locator(f'select[name="{field}"]').select_option(uid)
        page.locator('[name="Дата"]').fill(datetime.now().isoformat(timespec="minutes"))
        page.locator('[name="Сумма"]').fill("10000")
        page.locator('[name="НомерПлатёжки"]').fill("ALLOC-UI")
        page.locator('[name="НазначениеПлатежа"]').fill("Оплата двух реализаций")
        for row, (_, uid, amount, _) in enumerate(sales):
            page.get_by_role("button", name="Добавить строку", exact=False).click()
            prefix = f"tp.РаспределениеПлатежа.{row}."
            page.locator(f'[name="{prefix}ДокументРеализации"]').select_option(uid)
            page.locator(f'[name="{prefix}Сумма"]').fill(str(amount))
        page.get_by_role("button", name="Провести", exact=True).click()
        [(payment_id,)] = db.execute("SELECT id FROM поступлениенарасчётныйсчёт WHERE контрагент_id=? AND posted=1",
                                     (customer,)).fetchall()
        cash = db.execute("SELECT вид_движения, CAST(сумма AS INTEGER) FROM рег_денежныесредства WHERE recorder=?",
                          (payment_id,)).fetchall()
        assert cash == [("Приход", 10000)], cash
        page.goto(base + "/ui/report/ОплатыРеализаций")
        page.get_by_role("button", name="Сформировать", exact=False).click()
        for number, _, amount, _ in sales:
            report_row = page.get_by_text(number, exact=True).first.locator("xpath=ancestor::tr")
            cells = report_row.locator("td")
            report_row.wait_for()
            # Последние четыре колонки: долг за период, оплачено, остаток, просрочено.
            values = [Decimal("".join(value.split()).replace(",", ".")) for value in cells.all_inner_texts()[-4:]]
            assert values == [amount, amount, 0, 0], (number, values)
    finally:
        page.close()

def check_allocated_exchange(cli, db, project):
    bank, org, uid, date, buyer = db.execute(
        "SELECT д.банковскийсчёт_id, д.организация_id, д.id, д.дата, к.наименование "
        "FROM поступлениенарасчётныйсчёт д JOIN контрагент к ON к.id=д.контрагент_id "
        "WHERE д.номерплатёжки='ALLOC-UI' AND д.posted=1").fetchone()
    day = datetime.fromisoformat(date).astimezone().date().isoformat()
    statement = project / "allocated-statement.json"
    statement.write_text(json.dumps([dict(Дата=day, Тип="Поступление", Сумма=10000, Контрагент=buyer,
                                          НомерПлатёжки="ALLOC-UI", НазначениеПлатежа="Оплата двух реализаций")],
                                    ensure_ascii=False), encoding="utf8")

    def posted_lines():
        return (db.execute("SELECT id,сумма FROM рег_денежныесредства WHERE recorder=?", (uid,)).fetchall(),
                db.execute("SELECT id,документреализации_id,сумма FROM рег_взаиморасчеты "
                           "WHERE recorder=? ORDER BY line_number", (uid,)).fetchall())

    before = posted_lines()
    result = cli("procrun", "--proc", "ЗагрузкаВыписки", "--file", f"ТекстВыгрузки={statement}",
                 "--set", "Формат=JSON", "--set", "Действие=ЗаписатьИПровести",
                 "--set", f"БанковскийСчёт={bank}", "--set", f"Организация={org}", capture_output=True)
    replay = json.loads(result.stdout)
    assert replay["пропущено"] == 1 and replay["проведено"] == 0 and not replay["ошибки"], replay
    assert db.execute("SELECT count(*) FROM поступлениенарасчётныйсчёт WHERE номерплатёжки='ALLOC-UI'").fetchone()[0] == 1
    assert posted_lines() == before
    target = project / "allocated-bp3.json"
    cli("procrun", "--proc", "ВыгрузкаБП3", "--set", f"Путь={target}", "--set", f"ДатаНачала={day}",
        "--set", f"ДатаОкончания={day}", "--set", "ТолькоПроведенные=true", capture_output=True)
    dump = json.loads(target.read_text(encoding="utf-8-sig"))
    assert dump["version"] == "1.1"
    transfers = dump["documents"]["ПоступлениеНаРасчётныйСчёт"]
    [payment] = [row for row in transfers if row["uid"] == uid]
    assert payment["Сумма"] == "10000" and not payment["dependency"]
    assert payment["РаспределениеПлатежа"] == [
        {"ДокументРеализации": sale, "Сумма": amount} for _, sale, amount in before[1]]
    bases = {doc["uid"] for doc in dump["documents"]["РеализацияТоваров"] if doc["dependency"]}
    assert all(sale in bases for _, sale, _ in before[1])
    # The cash sale performed earlier in the same workplace run has one header basis.
    assert any(row.get("ДокументРеализации") and "РаспределениеПлатежа" not in row
               for row in dump["documents"]["ПриходныйКассовыйОрдер"])
