"""Generate the complete PuT -> BP3 wire contract from configuration metadata.

The generated DSL reads actual objects; it never substitutes presentations for UUIDs.
"""
from pathlib import Path
import argparse, json
import yaml

ROOT = Path(__file__).resolve().parents[1]

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
            definitions.append((kind,entity))
    lines=[(ROOT/'tools/bp3/exporter-common.os').read_text(encoding='utf-8-sig').rstrip(),'']
    for kind,collection in [('catalog','Справочники'),('document','Документы')]:
        lines += [f'Функция БП3{collection}(ДатаН, ДатаК, ТолькоПроведенные)', '  Результат = Новый Соответствие;']
        for k,e in definitions:
            if k==kind:lines += [f'  Результат.Вставить({q(e["name"])}, БП3Объект_{e["name"]}(ДатаН, ДатаК, ТолькоПроведенные));']
        lines += ['  Возврат Результат;','КонецФункции','']
    schema={}
    for kind,e in definitions:
        name=e['name']; fields=e.get('fields',[]);tables=e.get('tableparts',[])
        schema[name]={'kind':kind,'fields':{f['name']:f.get('type','string') for f in fields},'tables':{t['name']:{f['name']:f.get('type','string') for f in t.get('fields',[])} for t in tables}}
        manager=('Справочники.' if kind=='catalog' else 'Документы.')+name
        source=('Справочник.' if kind=='catalog' else 'Документ.')+name
        lines += [f'Функция БП3Объект_{name}(ДатаН, ДатаК, ТолькоПроведенные)', '  Результат = Новый Массив;', '  Запрос = Новый Запрос;', f'  Запрос.Текст = {q("ВЫБРАТЬ Ссылка КАК ИД ИЗ "+source+" УПОРЯДОЧИТЬ ПО Ссылка")};', '  Для Каждого Идентификатор Из Запрос.Выполнить() Цикл',f'    Объект = {manager}.НайтиПоИдентификатору(Идентификатор.ИД).ПолучитьОбъект();']
        if kind=='document':
            lines += ['    Если БП3ВПериоде(Объект.Дата, ДатаН, ДатаК) = Ложь Тогда Продолжить; КонецЕсли;', '    Если ТолькоПроведенные И Объект.Проведён = Ложь Тогда Продолжить; КонецЕсли;']
        lines += ['    Запись = Новый Соответствие;','    Запись.Вставить("uid", Идентификатор.ИД);']
        if kind=='document':lines += ['    Запись.Вставить("posted", Объект.Проведён);']
        if e.get('hierarchical'):
            lines += ['    Запись.Вставить("parent", БП3УИН(Объект.Родитель));','    Запись.Вставить("isGroup", Объект.ЭтоГруппа);']
        for f in fields:
            lines += [f'    Запись.Вставить({q(f["name"])}, {expression(f,"Объект")});']
        if kind=='document' and name=='КорректировкаДолга':
            lines += ['    Запись.Вставить("СальдоДоДокумента", БП3СальдоДоДокумента(Объект));']
        for t in tables:
            lines += ['    Строки = Новый Массив;',f'    Для Каждого СтрокаТаблицы Из Объект.{t["name"]} Цикл','      СтрокаВыгрузки = Новый Соответствие;']
            for f in t.get('fields',[]):lines += [f'      СтрокаВыгрузки.Вставить({q(f["name"])}, {expression(f,"СтрокаТаблицы")});']
            lines += ['      Строки.Добавить(СтрокаВыгрузки);','    КонецЦикла;',f'    Запись.Вставить({q(t["name"])}, Строки);']
        lines += ['    Результат.Добавить(Запись);','  КонецЦикла;','  Возврат Результат;','КонецФункции','']
    docs={e['name'] for kind,e in definitions if kind=='document'}
    lines += ['Процедура БП3ОснованияЗаписи(Вид, Запись, Индекс, Выбранные, Очередь, Результат)']
    for kind,e in definitions:
        if kind!='document':continue
        refs=[f for f in e.get('fields',[]) if f.get('type','').startswith('reference:') and f['type'].split(':',1)[1] in docs]
        if not refs:continue
        lines += [f'  Если Вид = {q(e["name"])} Тогда']
        for f in refs:lines += [f'    БП3ДобавитьОснование({q(f["type"].split(":",1)[1])}, Запись.Получить({q(f["name"])}), Индекс, Выбранные, Очередь, Результат);']
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
