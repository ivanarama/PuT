"""Generate the complete PuT -> BP3 wire contract from configuration metadata.

The generated DSL reads actual objects; it never substitutes presentations for UUIDs.
"""
from pathlib import Path
import argparse, json
import yaml

ROOT = Path(__file__).resolve().parents[1]

EXCLUDED = {"ЗаказПокупателя", "ЗаказПоставщику", "ЗакрытиеЗаказовПокупателей", "ЗакрытиеЗаказовПоставщикам"}


def q(value):
    return '"' + value.replace('"','""') + '"'

def expression(field, variable):
    kind = field.get('type','string')
    value = variable + '.' + field['name']
    if kind.startswith('reference:'):
        return 'БП3УИН(' + value + ')'
    if kind.startswith('number'):
        return 'БП3Число(' + value + ')'
    if kind == 'date':
        return 'БП3Дата(' + value + ')'
    return value

def generate():
    definitions=[]
    for folder,kind in [('catalogs','catalog'),('documents','document')]:
        for path in sorted((ROOT/folder).glob('*.yaml')):
            entity=yaml.safe_load(path.read_text(encoding='utf-8-sig'))
            if kind == 'catalog' and entity['name'] in ('ЖурналОбменов', 'ЗагрузкиОбменов'):
                continue
            if entity['name'] in ('ПоступлениеНаРасчётныйСчёт', 'СписаниеСРасчётногоСчёта'):
                entity['fields'] = [field for field in entity['fields'] if field['name'] != 'КлючИмпортаБанка']
            definitions.append((kind,entity))
    lines=[(ROOT/'tools/bp3/exporter-common.os').read_text(encoding='utf-8-sig').rstrip(),'']
    catalogs = [entity['name'] for kind, entity in definitions if kind == 'catalog']
    documents = [entity['name'] for kind, entity in definitions if kind == 'document']
    lines += ['Функция БП3Справочники()', '  Результат = Новый Соответствие;']
    for name in catalogs:
        lines.append(f'  Результат.Вставить({q(name)}, БП3Объект_{name}());')
    lines += ['  Возврат Результат;', 'КонецФункции', '']
    lines += ['Функция БП3Документы(ДатаН, ДатаК, ТолькоПроведенные)',
              '  Результат = Новый Соответствие;',
              '  Включены = Новый Соответствие;', '  Очередь = Новый Массив;']
    for name in documents:
        lines.append(f'  Результат.Вставить({q(name)}, Новый Массив);')
    lines += ['  Для Каждого Раздел Из Результат Цикл',
              '    Если БП3ПереносимыйВид(Раздел.Ключ) Тогда',
              '      Для Каждого Стр Из БП3ВыбратьДокументы(Раздел.Ключ, ДатаН, ДатаК, ТолькоПроведенные) Цикл',
              '        БП3ДобавитьОснование(Раздел.Ключ, Стр.ИД, Включены, Очередь, Результат, Ложь);',
              '      КонецЦикла;', '    КонецЕсли;', '  КонецЦикла;',
              '  Индекс = 0;', '  Пока Индекс < Очередь.Количество() Цикл',
              '    Шаг = Очередь[Индекс];',
              '    БП3ОснованияЗаписи(Шаг.Вид, Шаг.Запись, Включены, Очередь, Результат);',
              '    Индекс = Индекс + 1;', '  КонецЦикла;', '  Возврат Результат;', 'КонецФункции', '']
    lines.append('Функция БП3ПрочитатьДокумент(Вид, УИН)')
    for name in documents:
        if name in EXCLUDED:
            continue
        lines.append(f'  Если Вид = {q(name)} Тогда Возврат БП3Объект_{name}(УИН); КонецЕсли;')
    lines += ['  ВызватьИсключение "Неизвестный вид документа " + Вид;', 'КонецФункции', '']
    schema={}
    for kind,e in definitions:
        name=e['name']; fields=e.get('fields',[]);tables=e.get('tableparts',[])
        schema[name]={'kind':kind,'fields':{f['name']:f.get('type','string') for f in fields},'tables':{t['name']:{f['name']:f.get('type','string') for f in t.get('fields',[])} for t in tables}}
        if kind == 'document' and name in EXCLUDED:
            continue
        manager=('Справочники.' if kind=='catalog' else 'Документы.')+name
        source=('Справочник.' if kind=='catalog' else 'Документ.')+name
        if kind == 'catalog':
            lines += [f'Функция БП3Объект_{name}()', '  Результат = Новый Массив;', '  Запрос = Новый Запрос;',
                      f'  Запрос.Текст = {q("ВЫБРАТЬ Ссылка КАК ИД ИЗ "+source+" УПОРЯДОЧИТЬ ПО Ссылка")};',
                      '  Для Каждого Идентификатор Из Запрос.Выполнить() Цикл', '    УИН = Идентификатор.ИД;']
        else:
            lines.append(f'Функция БП3Объект_{name}(УИН)')
        body_start = len(lines)
        lines += [f'    Объект = {manager}.НайтиПоИдентификатору(УИН).ПолучитьОбъект();',
                  '    Запись = Новый Соответствие;', '    Запись.Вставить("uid", УИН);']
        if kind == 'document':
            lines.append('    Запись.Вставить("posted", Объект.Проведён);')
        if e.get('hierarchical'):
            lines += ['    Запись.Вставить("parent", БП3УИН(Объект.Родитель));','    Запись.Вставить("isGroup", Объект.ЭтоГруппа);']
        for f in fields:
            lines += [f'    Запись.Вставить({q(f["name"])}, {expression(f,"Объект")});']
        if kind=='document' and name=='КорректировкаДолга':
            lines += ['    Запись.Вставить("СальдоДоДокумента", БП3СальдоДоДокумента(Объект));']
        for t in tables:
            lines += ['    Строки = Новый Массив;',f'    Для Каждого СтрокаТаблицы Из Объект.{t["name"]} Цикл','      СтрокаВыгрузки = Новый Соответствие;']
            for f in t.get('fields',[]):lines += [f'      СтрокаВыгрузки.Вставить({q(f["name"])}, {expression(f,"СтрокаТаблицы")});']
            lines += ['      Строки.Добавить(СтрокаВыгрузки);', '    КонецЦикла;']
            if t['name'] == 'РаспределениеПлатежа':
                lines.append('    Если Строки.Количество() > 0 Тогда Запись.Вставить("РаспределениеПлатежа", Строки); КонецЕсли;')
            else:
                lines.append(f'    Запись.Вставить({q(t["name"])}, Строки);')
        if kind == 'catalog':
            lines += ['    Результат.Добавить(Запись);', '  КонецЦикла;', '  Возврат Результат;']
        else:
            lines[body_start:] = [line[2:] for line in lines[body_start:]]
            lines.append('  Возврат Запись;')
        lines += ['КонецФункции', '']
    docs={e['name'] for kind,e in definitions if kind=='document'}
    lines += ['Процедура БП3ОснованияЗаписи(Вид, Запись, Включены, Очередь, Результат)']
    for kind,e in definitions:
        if kind != 'document' or e['name'] in EXCLUDED:
            continue
        refs=[f for f in e.get('fields',[]) if f.get('type','').startswith('reference:') and f['type'].split(':',1)[1] in docs]
        row_refs = [(table['name'], field['name'], field['type'].split(':', 1)[1])
                    for table in e.get('tableparts', []) for field in table.get('fields', [])
                    if field.get('type', '').startswith('reference:') and field['type'].split(':', 1)[1] in docs - EXCLUDED]
        if not refs and not row_refs:
            continue
        lines += [f'  Если Вид = {q(e["name"])} Тогда']
        for f in refs:lines += [f'    БП3ДобавитьОснование({q(f["type"].split(":",1)[1])}, Запись.Получить({q(f["name"])}), Включены, Очередь, Результат);']
        for table, field, target in row_refs:
            lines += [f'    Строки = Запись.Получить({q(table)});',
                      '    Если Строки <> Неопределено Тогда',
                      '      Для Каждого Стр Из Строки Цикл',
                      f'        БП3ДобавитьОснование({q(target)}, Стр.Получить({q(field)}), Включены, Очередь, Результат);',
                      '      КонецЦикла;', '    КонецЕсли;']
        lines += ['  КонецЕсли;']
    lines += ['КонецПроцедуры','']
    return '\n'.join(lines),schema

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
    code,schema=generate()
    outputs={ROOT/'src/выгрузкабп3.proc.os':code,ROOT/'docs/bp3-schema.json':json.dumps(schema,ensure_ascii=False,indent=2)+'\n'}
    for path,text in outputs.items():
        if a.check:
            assert path.read_text(encoding='utf-8-sig')==text,f'Regenerate {path}'
        else:
            path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8')
