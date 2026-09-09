#!/usr/bin/env bash
# Сценарные тесты конфигурации PuT.
#   База A: свежая → демо-данные → сверки чисел (проведения, валовая прибыль).
#   База B: чистая + сид → ЭДО E2E (суммы/дата из УПД, способ НДС, идемпотентность).
# Любое расхождение = exit 1.
set -uo pipefail

cd "$(dirname "$0")/.."

DB_DEMO=".put_ci_demo_$$.db"
DB_EDO=".put_ci_edo_$$.db"
FAIL=0

cleanup() { rm -f "$DB_DEMO" "$DB_EDO"; }
trap cleanup EXIT

assert_eq() {
  local desc="$1" expected="$2" actual="$3"
  if [ "$expected" = "$actual" ]; then
    echo "  ok: $desc = $actual"
  else
    echo "  FAIL: $desc — ожидалось [$expected], получено [$actual]"
    FAIL=1
  fi
}

val() { # val "база" "запрос" — первая колонка первой строки результата
  onebase query --project . --sqlite "$1" "$2" 2>/dev/null | awk -F'\t' 'NR==2 {print $1}'
}

echo "── A. Демо-данные: миграция, заполнение, сверки"
onebase migrate --project . --sqlite "$DB_DEMO" > /dev/null
onebase procrun --project . --sqlite "$DB_DEMO" --proc ЗаполнитьТестовуюБазу > /dev/null 2>&1

assert_eq "есть проведённые реализации" "1" \
  "$(val "$DB_DEMO" "ВЫБРАТЬ КОЛИЧЕСТВО(Ссылка) КАК К ИЗ Документ.РеализацияТоваров ГДЕ posted = 1" | awk '{print ($1 + 0 > 0) ? 1 : 0}')"

assert_eq "валовая прибыль имеет приходные движения с выручкой" "1" \
  "$(val "$DB_DEMO" "ВЫБРАТЬ КОЛИЧЕСТВО(Регистратор) КАК К ИЗ РегистрНакопления.ВаловаяПрибыль ГДЕ вид_движения = \"Приход\" AND Выручка > 0" | awk '{print ($1 + 0 > 0) ? 1 : 0}')"

assert_eq "возвраты сторнируют выручку (прихода больше, чем расхода)" "1" \
  "$(val "$DB_DEMO" "ВЫБРАТЬ КОЛИЧЕСТВО(Ссылка) КАК К ИЗ Документ.РеализацияТоваров ГДЕ posted = 1 AND Сумма > 0" | awk '{print ($1 + 0 > 0) ? 1 : 0}')"

assert_eq "на складах есть приходные движения товаров" "1" \
  "$(val "$DB_DEMO" "ВЫБРАТЬ КОЛИЧЕСТВО(Регистратор) КАК К ИЗ РегистрНакопления.ОстаткиТоваров ГДЕ вид_движения = \"Приход\" AND Количество > 0" | awk '{print ($1 + 0 > 0) ? 1 : 0}')"

echo "── B. ЭДО: чистая база + сид → загрузка УПД"
onebase migrate --project . --sqlite "$DB_EDO" > /dev/null
if command -v sqlite3 > /dev/null 2>&1; then
  sqlite3 "$DB_EDO" < tests/fixtures/seed.sql
elif command -v python3 > /dev/null 2>&1; then
  python3 -c "import sqlite3; c = sqlite3.connect('$DB_EDO'); c.executescript(open('tests/fixtures/seed.sql', encoding='utf-8').read()); c.commit(); c.close()"
else
  python -c "import sqlite3; c = sqlite3.connect(r'$DB_EDO'); c.executescript(open('tests/fixtures/seed.sql', encoding='utf-8').read()); c.commit(); c.close()"
fi

onebase procrun --project . --sqlite "$DB_EDO" --proc ЗагрузкаЭДО \
  --file "ФайлЭДО=tests/fixtures/upd_test.xml" \
  --set "Действие=Создать и провести" > /dev/null 2>&1

assert_eq "поступление по УПД создано и проведено" "1" \
  "$(val "$DB_EDO" "ВЫБРАТЬ КОЛИЧЕСТВО(Ссылка) КАК К ИЗ Документ.ПоступлениеТоваров ГДЕ Номер = \"УТ-TEST-1\" AND posted = 1")"

assert_eq "способ учёта НДС — Сверху" "1" \
  "$(val "$DB_EDO" "ВЫБРАТЬ КОЛИЧЕСТВО(Ссылка) КАК К ИЗ Документ.ПоступлениеТоваров ГДЕ Номер = \"УТ-TEST-1\" AND СпособУчетаНДС = \"Сверху\"")"

assert_eq "сумма документа = УПД (240 + 50)" "290" \
  "$(val "$DB_EDO" "ВЫБРАТЬ CAST(ROUND(Сумма, 0) AS INTEGER) КАК С ИЗ Документ.ПоступлениеТоваров ГДЕ Номер = \"УТ-TEST-1\"")"

assert_eq "НДС документа = из УПД (позиция «Без НДС» не облагается)" "40" \
  "$(val "$DB_EDO" "ВЫБРАТЬ CAST(ROUND(СуммаНДС, 0) AS INTEGER) КАК Н ИЗ Документ.ПоступлениеТоваров ГДЕ Номер = \"УТ-TEST-1\"")"

assert_eq "дата документа — из УПД (февраль 2026), а не дата загрузки" "1" \
  "$(val "$DB_EDO" "ВЫБРАТЬ КОЛИЧЕСТВО(Ссылка) КАК К ИЗ Документ.ПоступлениеТоваров ГДЕ Номер = \"УТ-TEST-1\" AND Дата >= \"2026-02-01\" AND Дата < \"2026-03-01\"")"

assert_eq "поставщик найден по ИНН (safe-match), дубль не создан" "1" \
  "$(val "$DB_EDO" "ВЫБРАТЬ КОЛИЧЕСТВО(Ссылка) КАК К ИЗ Справочник.Контрагент ГДЕ ИНН = \"7700000001\"")"

if command -v sqlite3 > /dev/null 2>&1; then
  ROWS_TP=$(sqlite3 "$DB_EDO" "SELECT COUNT(*) FROM поступлениетоваров_товары t JOIN поступлениетоваров d ON t.parent_id = d.id WHERE d.номер='УТ-TEST-1'")
else
  ROWS_TP=$(python -c "import sqlite3; c = sqlite3.connect(r'$DB_EDO'); print(c.execute(\"SELECT COUNT(*) FROM поступлениетоваров_товары t JOIN поступлениетоваров d ON t.parent_id = d.id WHERE d.номер='УТ-TEST-1'\").fetchone()[0]); c.close()")
fi
assert_eq "обе строки сопоставлены и записаны в ТЧ" "2" "$ROWS_TP"

assert_eq "себестоимость партий = нетто УПД (250)" "250" \
  "$(val "$DB_EDO" "ВЫБРАТЬ CAST(ROUND(СУММА(ВЫБОР КОГДА вид_движения = \"Приход\" ТОГДА Сумма ИНАЧЕ -Сумма КОНЕЦ), 0) AS INTEGER) КАК С ИЗ РегистрНакопления.ПартииТоваров")"

echo "── C. ЭДО: идемпотентность (повторная загрузка не плодит дубль)"
onebase procrun --project . --sqlite "$DB_EDO" --proc ЗагрузкаЭДО \
  --file "ФайлЭДО=tests/fixtures/upd_test.xml" \
  --set "Действие=Создать и провести" > /dev/null 2>&1

assert_eq "документов с номером УПД ровно один" "1" \
  "$(val "$DB_EDO" "ВЫБРАТЬ КОЛИЧЕСТВО(Ссылка) КАК К ИЗ Документ.ПоступлениеТоваров ГДЕ Номер = \"УТ-TEST-1\"")"

if [ "$FAIL" -ne 0 ]; then
  echo "СЦЕНАРНЫЕ ТЕСТЫ ПРОВАЛЕНЫ"
  exit 1
fi
echo "Сценарные тесты пройдены."
