"""Verify queue acknowledgement and accounting review in the isolated workplace test."""
import json
import time
import uuid


def check_queue_and_diagnostics(context, base, project, db):
    page = context.new_page()
    try:
        page.goto(base + '/ui/page/СверкаУчета')
        page.get_by_text('Строк для проверки:', exact=False).first.wait_for()

        # A queued request with a future start makes the overlap deterministic.
        busy = str(uuid.uuid4())
        key = 'пут-ВыгрузкаБП3'
        db.execute("""INSERT INTO _job_queue(id, job_name, params, key, status, available_at)
                      VALUES (?, 'ФонВыгрузкаБП3', ?, ?, 'pending', ?)""",
                   (busy, json.dumps({'КодИсточника': 'другая база'}), key,
                    int((time.time() + 3600) * 1000)))
        db.commit()
        page.goto(base + '/ui/processor/ВыгрузкаБП3')
        name = project/'queued-bp3.json'
        page.locator('[name=Путь]').fill(str(name))
        page.locator('[name=КодИсточника]').fill('новый запрос')
        start = page.get_by_role('button', name='Поставить в очередь')
        start.click()
        page.get_by_text('Ваш запрос не поставлен.', exact=False).first.wait_for()
        assert not page.locator('[name=ИдЗадачи]').input_value()
        assert not name.exists()

        db.execute("UPDATE _job_queue SET status='cancelled' WHERE id=?", (busy,))
        db.commit()
        start.click()
        page.wait_for_function("document.querySelector('[name=ИдЗадачи]').value.length > 0")
        identity = page.locator('[name=ИдЗадачи]').input_value()
        assert identity != busy
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            status, error = db.execute('SELECT status,error FROM _job_queue WHERE id=?',
                                       (identity,)).fetchone()
            assert status != 'dead', error
            if status == 'done':
                break
            time.sleep(.25)
        assert status == 'done', status
        assert json.loads(name.read_text(encoding='utf-8-sig'))['sourceId'] == 'новый запрос'
    finally:
        page.close()
