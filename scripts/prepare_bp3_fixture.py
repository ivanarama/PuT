"""Add the two empty demo document types in an isolated runtime fixture."""
from pathlib import Path
import argparse,json,subprocess

p=argparse.ArgumentParser();p.add_argument('--onebase',required=True);p.add_argument('--project',type=Path,required=True);p.add_argument('--database',required=True);p.add_argument('--dump',type=Path,required=True);a=p.parse_args()
d=json.loads(a.dump.read_text(encoding='utf-8-sig'));cats=d['catalogs']
org=cats['Организация'][0]['uid'];stock=cats['Склад'][0]['uid'];nom=cats['Номенклатура'][0]['uid']
buyer=next(x['uid'] for x in cats['Контрагент'] if x['Вид']=='Покупатель')
code=f'''Процедура Выполнить()
  Организация = Справочники.Организация.НайтиПоИдентификатору("{org}");
  Склад = Справочники.Склад.НайтиПоИдентификатору("{stock}");
  Товар = Справочники.Номенклатура.НайтиПоИдентификатору("{nom}");
  Контрагент = Справочники.Контрагент.НайтиПоИдентификатору("{buyer}");
  Док = Документы.ПересчетТоваров.Создать();
  Док.Организация = Организация; Док.Склад = Склад; Док.Дата = Дата(2026,10,28,12,0,0);
  Стр = Док.Товары.Добавить(); Стр.Номенклатура = Товар; Стр.КоличествоУчёт = 10; Стр.КоличествоФакт = 9;
  Док.Записать();
  Док = Документы.КорректировкаДолга.Создать();
  Док.Организация = Организация; Док.Контрагент = Контрагент; Док.Дата = Дата(2026,10,28,12,0,0);
  Док.ВидОперации = "СписаниеЗадолженности"; Док.Сумма = 10;
  Док.Записать();
  Сообщить("BP3 fixture: inventory and debt adjustment created");
КонецПроцедуры
'''
meta=a.project/'processors/бп3_покрытие_теста.yaml';module=a.project/'src/бп3покрытиетеста.proc.os'
assert not meta.exists() and not module.exists()
try:
 meta.write_text('name: БП3ПокрытиеТеста\ntitle: BP3 runtime fixture\n',encoding='utf-8');module.write_text(code,encoding='utf-8')
 subprocess.run([a.onebase,'procrun','--project',str(a.project),'--sqlite',a.database,'--proc','БП3ПокрытиеТеста','--no-gui'],check=True)
finally:
 meta.unlink(missing_ok=True);module.unlink(missing_ok=True)
