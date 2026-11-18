"""Exercise bank replay, EDI buyer identity and migration atomicity on an isolated SQLite."""
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
import argparse
import os
import uuid
import json
import sqlite3
import subprocess
import tempfile
import secrets
import socket
import time
from urllib.parse import quote
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACCOUNT = "66666666-6666-4666-8666-666666666666"


def verify(executable, tmp, browser_path=None):
    db = tmp / "exchange.db"

    def run(cmd, *args, ok=True):
        result = subprocess.run([executable, cmd, "--project", str(ROOT), "--sqlite",
                                 str(db), *args], capture_output=True, text=True, encoding="utf-8")
        assert (result.returncode == 0) == ok, result.stderr + result.stdout
        return result.stdout if ok else result.stderr

    def scalar(sql, *params):
        with closing(sqlite3.connect(db)) as connection, connection:
            return connection.execute(sql, params).fetchone()[0]

    def process(proc, source_name, source_file, ok=True, **params):
        args = ["--proc", proc, "--file", source_name + "=" + str(source_file)]
        for key, value in params.items():
            args.extend(["--set", key + "=" + value])
        return run("procrun", *args, ok=ok)

    run("migrate")
    with closing(sqlite3.connect(db)) as connection, connection:
        connection.executescript((ROOT / "tests/fixtures/seed.sql").read_text(encoding="utf-8"))
        connection.execute("INSERT INTO касса (id, наименование, вид, номерсчёта) VALUES (?,?,?,?)",
                           (ACCOUNT, "Банк", "БанковскийСчёт", "40702810900000001234"))

    statement = tmp / "bank.json"
    payment = dict(Дата="2026-06-25", Контрагент="Новый получатель", Тип="Поступление",
                   Сумма=137.25, НазначениеПлатежа="Товар", НомерПлатёжки="P124")
    statement.write_text(json.dumps([payment], ensure_ascii=False), encoding="utf-8")

    def bank(operation, source=""):
        return json.loads(process("ЗагрузкаВыписки", "ТекстВыгрузки", statement,
                                  Действие=operation, БанковскийСчёт=ACCOUNT, Формат="JSON", ИсточникОбмена=source))

    assert bank("Предпросмотр")["всего"] == 1
    assert scalar("SELECT count(*) FROM контрагент WHERE наименование=?", payment["Контрагент"]) == 0
    assert bank("Записать")["поступлений"] == 1
    assert bank("ЗаписатьИПровести")["проведено"] == 1
    assert bank("ЗаписатьИПровести")["пропущено"] == 1
    assert scalar("SELECT sum(сумма) FROM поступлениенарасчётныйсчёт WHERE posted=1") == 137.25
    # Imports created before this version have no dedicated idempotency key.
    with closing(sqlite3.connect(db)) as connection, connection:
        connection.execute("UPDATE поступлениенарасчётныйсчёт SET ключимпортабанка=NULL WHERE номерплатёжки='P124'")
    assert bank("ЗаписатьИПровести")["пропущено"] == 1
    assert scalar("SELECT count(*) FROM поступлениенарасчётныйсчёт") == 1

    statement.write_text(json.dumps([{**payment, "Сумма": 250}], ensure_ascii=False), encoding="utf-8")
    assert bank("ЗаписатьИПровести")["ошибки"]
    assert scalar("SELECT count(*) FROM поступлениенарасчётныйсчёт") == 1
    # Restore funds for a failed debit, then retry the original, unchanged bank row.
    debit = {**payment, "Тип": "Списание", "Сумма": 250, "Дата": "2026-06-27", "НомерПлатёжки": "OUT-01"}
    statement.write_text(json.dumps([payment] * 100 + [debit], ensure_ascii=False), encoding="utf-8")
    batch_result = bank("ЗаписатьИПровести", "bank-101.json")
    assert len(batch_result["ошибки"]) == 1 and batch_result["пропущено"] == 100, batch_result
    error_id = scalar("SELECT id FROM журналобменов WHERE статус='Ошибка' AND наименование LIKE '%OUT-01%'")
    funding = {**payment, "Дата": "2026-06-26", "Сумма": 200, "НомерПлатёжки": "IN-02"}
    statement.write_text(json.dumps([funding], ensure_ascii=False), encoding="utf-8")
    assert bank("ЗаписатьИПровести")["проведено"] == 1
    if browser_path:
        retry_in_browser(executable, db, browser_path, tmp)
    else:
        retried = run("procrun", "--proc", "СверкаОбменов", "--set", "ЗаписьЖурнала=" + error_id)
        assert json.loads(retried)["проведено"] == 1, retried
    assert scalar("SELECT статус FROM журналобменов WHERE id=?", error_id) == "Исправлено"
    assert scalar("SELECT count(*) FROM журналобменов WHERE загрузка_id=(SELECT загрузка_id FROM журналобменов WHERE id=?)",
                  error_id) == 102
    assert scalar("SELECT count(*) FROM списаниесрасчётногосчёта WHERE posted=1 AND номерплатёжки='OUT-01'") == 1

    upd = (ROOT / "tests/fixtures/upd_test.xml").read_text(encoding="utf-8")
    wrong_buyer = tmp / "foreign.xml"
    wrong_buyer.write_text(upd.replace("<ТаблСчФ>", '<СвПокуп><ИдСв><СвЮЛУч ИННЮЛ="7800000111"/>'
                                      '</ИдСв></СвПокуп><ТаблСчФ>'), encoding="utf-8")
    err = process("ЗагрузкаЭДО", "ФайлЭДО", wrong_buyer, ok=False, Действие="Создать и провести")
    assert "7800000111" in err, err
    assert scalar("SELECT count(*) FROM поступлениетоваров") == 0
    assert scalar("SELECT count(*) FROM журналобменов WHERE обмен='ЭДО' AND статус='Ошибка'") == 1
    process("ЗагрузкаЭДО", "ФайлЭДО", ROOT / "tests/fixtures/upd_test.xml", Действие="Создать и провести")
    assert float(scalar("SELECT сумма FROM поступлениетоваров WHERE posted=1")) == 290

    dump = tmp / "migration.json"
    header = dict(type="ПоступлениеТоваров", id="receipt-1", date="2026-06-10", number="M-01",
                  organization="org-1", warehouse="wh-1", counterparty="partner-1", posted=True)
    line = dict(item="goods-1", quantity=2, price=100, amount=200, vatRate="7%", vatAmount=14)
    catalogs = {"Организации": [dict(id="org-1", name="Компания")],
                "Склады": [dict(id="wh-1", name="Склад")],
                "Контрагенты": [dict(id="partner-1", name="Поставщик")],
                "Номенклатура": [dict(id="goods-1", name="Товар", vatRate="7%")]}
    def migrate_doc(lines):
        dump.write_text(json.dumps(dict(catalogs=catalogs, documents=[dict(header, lines=lines)]),
                                   ensure_ascii=False), encoding="utf-8")
        return process("ЗагрузкаДампа1С", "ФайлJSON", dump)

    migrate_doc([line, {**line, "item": "неизвестный"}])
    assert scalar("SELECT count(*) FROM поступлениетоваров WHERE номер='M-01'") == 0
    assert scalar("SELECT count(*) FROM журналобменов WHERE обмен='1С' AND статус='Ошибка'") == 1
    migrate_doc([line])
    assert scalar("SELECT count(*) FROM поступлениетоваров WHERE номер='M-01' AND posted=1") == 1
    repeated = migrate_doc([line])
    assert "Ошибок: 0" in repeated, repeated
    conflict = migrate_doc([line, {**line, "quantity": 1, "amount": 100}])
    assert "число товарных строк" in conflict, conflict
    assert scalar("SELECT count(*) FROM поступлениетоваров_товары WHERE parent_id IN "
                  "(SELECT id FROM поступлениетоваров WHERE номер='M-01')") == 1
    assert float(scalar("SELECT процент FROM ставкандс WHERE наименование='7%'")) == 7
    for count, (raw, normalized, rate) in enumerate([("Без НДС", "Без НДС", 0),
                                                   ("НДС 20%", "20%", 20),
                                                   ("7/107", "7%", 7)]):
        header["id"] = f"rate-{count}"
        header["number"] = f"RATE-{count}"
        result = migrate_doc([{**line, "vatRate": raw, "vatAmount": 2 * rate}])
        assert "Ошибок: 0" in result, result
        actual = scalar("SELECT с.наименование FROM поступлениетоваров_товары т "
                        "JOIN ставкандс с ON с.id=т.ставкандс_id JOIN поступлениетоваров д "
                        "ON д.id=т.parent_id WHERE д.номер=?", header["number"])
        assert actual == normalized, (raw, actual)
    header.update(id="rate-invalid", number="RATE-INVALID")
    result = migrate_doc([{**line, "vatRate": "Неразобранная ставка"}])
    assert "Неизвестная ставка НДС" in result, result
    assert scalar("SELECT COUNT(*) FROM поступлениетоваров WHERE номер='RATE-INVALID'") == 0



    # One bank account in a multi-company dataset requires an explicit company
    # unless the account number identifies its owner.
    statement.write_text(json.dumps([payment], ensure_ascii=False), encoding="utf-8")
    err = process("ЗагрузкаВыписки", "ТекстВыгрузки", statement, ok=False, Действие="ЗаписатьИПровести",
                  БанковскийСчёт=ACCOUNT, Формат="JSON")
    assert "Укажите организацию" in err, err
    org2 = scalar("SELECT id FROM организация WHERE идентификатор1с='org-1'")
    output = process("ЗагрузкаВыписки", "ТекстВыгрузки", statement, Организация=org2,
                     Действие="ЗаписатьИПровести", БанковскийСчёт=ACCOUNT, Формат="JSON")
    assert json.loads(output)["проведено"] == 1, output
    assert scalar("SELECT count(*) FROM поступлениенарасчётныйсчёт WHERE номерплатёжки='P124' AND posted=1") == 2


def verify_parallel_postgres(executable, dsn_path, tmp):
    """Use an isolated disposable database supplied by the operator."""
    import psycopg

    env = os.environ.copy()
    env["DATABASE_URL"] = Path(dsn_path).read_text(encoding="utf-8-sig").strip()
    def run(*args):
        result = subprocess.run([executable, *args, "--project", str(ROOT)], env=env,
                                capture_output=True, text=True, encoding="utf-8")
        assert result.returncode == 0, result.stderr.replace(env["DATABASE_URL"], "<database>")
        return result.stdout

    run("migrate")
    suffix = uuid.uuid4().hex
    account = str(uuid.uuid4())
    org = str(uuid.uuid4())
    partner = "Плательщик " + suffix
    with psycopg.connect(env["DATABASE_URL"]) as connection:
        writer_tables = connection.execute(
            "SELECT to_regclass('_audit') IS NOT NULL, to_regclass('_stage_history') IS NOT NULL"
        ).fetchone()
        assert writer_tables == (True, True), f"migrate must prepare the processor schemas: {writer_tables}"
        connection.execute("INSERT INTO касса(id,наименование,вид) VALUES (%s,%s,%s)",
                           (account, "Банк " + suffix, "БанковскийСчёт"))
        connection.execute("INSERT INTO организация(id,наименование) VALUES (%s,%s)",
                           (org, "Организация " + suffix))
    statement = tmp / "parallel-bank.json"
    statement.write_text(json.dumps([dict(Дата="2026-06-25", Сумма=137.25, Контрагент=partner,
                                              Тип="Поступление", НомерПлатёжки="P124")], ensure_ascii=False),
                         encoding="utf-8")
    def import_file():
        output = run("procrun", "--proc", "ЗагрузкаВыписки", "--file", "ТекстВыгрузки=" + str(statement),
                     "--set", "БанковскийСчёт=" + account, "--set", "Организация=" + org, "--set", "Формат=JSON",
                     "--set", "Действие=ЗаписатьИПровести")
        return json.loads(output)
    with ThreadPoolExecutor(max_workers=2) as executor:
        attempts = [executor.submit(import_file) for _ in range(2)]
        outcomes = [attempt.result() for attempt in attempts]
    assert all(not row["ошибки"] for row in outcomes), outcomes
    assert sum(row["проведено"] for row in outcomes) == 1, outcomes
    assert sum(row["пропущено"] for row in outcomes) == 1, outcomes
    with psycopg.connect(env["DATABASE_URL"]) as connection:
        count, amount = connection.execute(
            "SELECT COUNT(*),SUM(сумма) FROM поступлениенарасчётныйсчёт WHERE банковскийсчёт_id=%s AND posted",
            (account,)).fetchone()
    assert count == 1 and float(amount) == 137.25, (count,amount)
    print("PostgreSQL concurrent imports: 1 posted, 1 skipped; amount 137.25")


def retry_in_browser(executable, db, browser_path, tmp):
    from playwright.sync_api import sync_playwright
    password = secrets.token_urlsafe(24)
    flags = ["--project", str(ROOT), "--sqlite", str(db)]
    subprocess.run([executable, "user", "add", "reviewer", "--admin", "--password-stdin", *flags],
                   input=password + "\n", capture_output=True, check=True, text=True)
    cashier_password = secrets.token_urlsafe(24)
    subprocess.run([executable, "user", "add", "cashier", "--password-stdin", *flags],
                   input=cashier_password, capture_output=True, check=True, text=True)
    subprocess.run([executable, "user", "role", "assign", "cashier", "Кассир", *flags], check=True,
                   capture_output=True)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    with (tmp / "server.log").open("w", encoding="utf-8") as log:
        server = subprocess.Popen([executable, "--no-gui", "run", "--host", "127.0.0.1", "--port", str(port),
                                   *flags], stdout=log, stderr=log)
        try:
            for _ in range(100):
                try:
                    socket.create_connection(("127.0.0.1", port), timeout=.2).close()
                    break
                except OSError:
                    time.sleep(.2)
            with sync_playwright() as automation:
                browser = automation.chromium.launch(executable_path=browser_path, headless=True)
                page = browser.new_page()
                page.set_default_timeout(8000)
                page.goto(f"http://127.0.0.1:{port}/ui/processor/" + quote("сверкаобменов"))
                page.locator("[name=login]").fill("reviewer")
                page.locator("[name=password]").fill(password)
                page.get_by_role("button", name="Войти", exact=True).click()
                page.wait_for_load_state("networkidle")
                batch = page.locator("[name=Загрузка]")
                batch_option = batch.locator("option", has_text="bank-101.json").first
                with page.expect_response(lambda r: "/form-event" in r.url and r.request.method == "POST") as event:
                    batch.select_option(value=batch_option.get_attribute("value"))
                result = event.value.json()
                assert len(result["tableparts"]["История"]) == 101, result.get("error")
                with page.expect_response(lambda r: "/form-event" in r.url and r.request.method == "POST") as event:
                    page.locator("[name=СтатусОтбора]").select_option(label="Ошибка")
                rows = event.value.json()["tableparts"]["История"]
                assert len(rows) == 1 and "OUT-01" in rows[0]["Документ"]
                assert page.locator("[name=ЗаписьЖурнала]").input_value(), "The single failed payment must be selected"
                with page.expect_response(lambda r: "/form-event" in r.url and r.request.method == "POST") as event:
                    page.get_by_role("button", name="Повторить ошибочную строку банка", exact=True).click()
                assert event.value.ok, event.value.text()
                page.wait_for_load_state("networkidle")
                page.close()
                cashier = browser.new_page()
                cashier.set_default_timeout(12000)
                cashier.goto(f"http://127.0.0.1:{port}/ui/processor/" + quote("загрузкавыписки"))
                cashier.locator("[name=login]").fill("cashier")
                cashier.locator("[name=password]").fill(cashier_password)
                cashier.get_by_role("button", name="Войти", exact=True).click()
                cashier.wait_for_load_state("networkidle")
                assert cashier.get_by_role("link", name="Сверка обменов", exact=True).count() == 0
                assert cashier.get_by_role("link", name="Журнал обменов", exact=True).count() == 0
                cashier.locator("[name=БанковскийСчёт]").select_option(ACCOUNT)
                cashier.locator("input[type=file]").set_input_files({
                    "name": "bank.json", "mimeType": "application/json",
                    "buffer": json.dumps([dict(Дата="2026-07-01", Сумма=31, Контрагент="Новый получатель",
                                               Тип="Поступление", НомерПлатёжки="CASHIER-01")],
                                         ensure_ascii=False).encode("utf-8")})
                for button in ["Загрузить предпросмотр", "Записать и провести"]:
                    with cashier.expect_response(lambda r: "/form-event" in r.url and r.request.method == "POST") as event:
                        cashier.get_by_role("button", name=button, exact=True).click()
                    assert event.value.ok, event.value.text()
                    body = event.value.json()
                    assert body["ok"], body.get("error")
                    cashier.wait_for_load_state("networkidle")
                browser.close()
                with closing(sqlite3.connect(db)) as connection:
                    row = connection.execute("SELECT COUNT(*) FROM поступлениенарасчётныйсчёт "
                                             "WHERE номерплатёжки='CASHIER-01' AND posted=1").fetchone()
                    assert row == (1,), row
        finally:
            server.terminate()
            server.wait(timeout=15)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--onebase", default="onebase")
    parser.add_argument("--browser", help="Run the retry in the managed form using a Chromium executable")
    parser.add_argument("--postgres-dsn-file", help="Additionally test two concurrent CLI workers on an isolated PostgreSQL database")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="put-exchange-") as directory:
        verify(args.onebase, Path(directory), args.browser)
        if args.postgres_dsn_file:
            verify_parallel_postgres(args.onebase, args.postgres_dsn_file, Path(directory))
    print("Bank replay, EDI buyer identity and migration checks passed")
