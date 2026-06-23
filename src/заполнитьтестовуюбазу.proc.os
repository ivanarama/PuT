// Наполняет тестовую базу «мебельного абсурда» с проведением, в один проход.
//
// Параметр «Очистить» (bool, по умолчанию true; снять флажок — пропустить очистку):
//   при очистке удаляются все документы (движения уходят), затем база
//   наполняется заново. Так не нужно чистить руки.
//
// Идемпотентно: справочники — по наименованию; документы создаются, только
// если очистка прошла ИЛИ поступлений ещё нет (без дублей).
//
// Документы датируются «по этажам» (поступления раньше реализаций) — чтобы
// перепроведение / восстановление последовательности шло в верном порядке.
//
// П.13: одна процедура на файл — всё инлайн.

Процедура Выполнить()

  // ============ СПРАВОЧНИКИ ============

  ЕдШт     = Справочники.ЕдиницаИзмерения.НайтиПоНаименованию("шт");
  Ставка20 = Справочники.СтавкаНДС.НайтиПоНаименованию("20%");
  ТипРозн  = Справочники.ТипЦен.НайтиПоНаименованию("Розничная");

  Если ЗначениеЗаполнено(Справочники.Организация.НайтиПоНаименованию("ООО «Табуретка-Люкс»")) = Ложь Тогда
    Зап = Справочники.Организация.Создать();
    Зап.Наименование       = "ООО «Табуретка-Люкс»";
    Зап.ПолноеНаименование = "Общество с ограниченной ответственностью «Табуретка-Люкс»";
    Зап.ИНН                = "7701234567";
    Зап.КПП                = "770101001";
    Зап.ОГРН               = "1157746000000";
    Зап.ЮридическийАдрес   = "г. Москва, ул. Ножкина, д. 4, под столом";
    Зап.Руководитель       = "Табуреткин Эдуард Стулович";
    Зап.ГлавныйБухгалтер   = "Полкина Авдотья Ящиковна";
    Зап.Записать();
  КонецЕсли;
  НашаОрг = Справочники.Организация.НайтиПоНаименованию("ООО «Табуретка-Люкс»");

  Если ЗначениеЗаполнено(Справочники.Склад.НайтиПоНаименованию("Главный склад «Где-то там»")) = Ложь Тогда
    Зап = Справочники.Склад.Создать();
    Зап.Наименование = "Главный склад «Где-то там»";
    Зап.Записать();
  КонецЕсли;
  СкладГлавный = Справочники.Склад.НайтиПоНаименованию("Главный склад «Где-то там»");

  Если ЗначениеЗаполнено(Справочники.Склад.НайтиПоНаименованию("Склад уценёнки «Почти как новое»")) = Ложь Тогда
    Зап = Справочники.Склад.Создать();
    Зап.Наименование = "Склад уценёнки «Почти как новое»";
    Зап.Записать();
  КонецЕсли;
  СкладУценка = Справочники.Склад.НайтиПоНаименованию("Склад уценёнки «Почти как новое»");

  Если ЗначениеЗаполнено(Справочники.Касса.НайтиПоНаименованию("Касса (жестянка от печенья)")) = Ложь Тогда
    Зап = Справочники.Касса.Создать();
    Зап.Наименование = "Касса (жестянка от печенья)";
    Зап.Вид          = "Касса";
    Зап.Записать();
  КонецЕсли;
  КассаНал = Справочники.Касса.НайтиПоНаименованию("Касса (жестянка от печенья)");

  Если ЗначениеЗаполнено(Справочники.Касса.НайтиПоНаименованию("Счёт в банке «Подушка»")) = Ложь Тогда
    Зап = Справочники.Касса.Создать();
    Зап.Наименование = "Счёт в банке «Подушка»";
    Зап.Вид          = "БанковскийСчёт";
    Зап.НомерСчёта   = "40702810900000001234";
    Зап.Банк         = "АО «Подушка-Банк»";
    Зап.БИК          = "044525999";
    Зап.Записать();
  КонецЕсли;
  СчётБанк = Справочники.Касса.НайтиПоНаименованию("Счёт в банке «Подушка»");

  // --- Поставщики ---

  Если ЗначениеЗаполнено(Справочники.Контрагент.НайтиПоНаименованию("ООО «Дерево и Гвозди»")) = Ложь Тогда
    Зап = Справочники.Контрагент.Создать();
    Зап.Наименование       = "ООО «Дерево и Гвозди»";
    Зап.ПолноеНаименование = "ООО «Дерево и Гвозди»";
    Зап.Вид                = "Поставщик";
    Зап.ИНН                = "5025001122";
    Зап.Записать();
  КонецЕсли;
  ПоставщикДерево = Справочники.Контрагент.НайтиПоНаименованию("ООО «Дерево и Гвозди»");

  Если ЗначениеЗаполнено(Справочники.Контрагент.НайтиПоНаименованию("ООО «Фанера-Палас»")) = Ложь Тогда
    Зап = Справочники.Контрагент.Создать();
    Зап.Наименование       = "ООО «Фанера-Палас»";
    Зап.ПолноеНаименование = "ООО «Фанера-Палас»";
    Зап.Вид                = "Поставщик";
    Зап.ИНН                = "7805004455";
    Зап.Записать();
  КонецЕсли;
  ПоставщикФанера = Справочники.Контрагент.НайтиПоНаименованию("ООО «Фанера-Палас»");

  Если ЗначениеЗаполнено(Справочники.Контрагент.НайтиПоНаименованию("ООО «Гвоздь в стене»")) = Ложь Тогда
    Зап = Справочники.Контрагент.Создать();
    Зап.Наименование       = "ООО «Гвоздь в стене»";
    Зап.ПолноеНаименование = "ООО «Гвоздь в стене»";
    Зап.Вид                = "Поставщик";
    Зап.ИНН                = "7713007788";
    Зап.Записать();
  КонецЕсли;
  ПоставщикГвоздь = Справочники.Контрагент.НайтиПоНаименованию("ООО «Гвоздь в стене»");

  Если ЗначениеЗаполнено(Справочники.Контрагент.НайтиПоНаименованию("ООО «Клей и Шуруп»")) = Ложь Тогда
    Зап = Справочники.Контрагент.Создать();
    Зап.Наименование       = "ООО «Клей и Шуруп»";
    Зап.ПолноеНаименование = "ООО «Клей и Шуруп»";
    Зап.Вид                = "Поставщик";
    Зап.ИНН                = "7724009900";
    Зап.Записать();
  КонецЕсли;
  ПоставщикКлей = Справочники.Контрагент.НайтиПоНаименованию("ООО «Клей и Шуруп»");

  Если ЗначениеЗаполнено(Справочники.Контрагент.НайтиПоНаименованию("ЗАО «Мебель без ручек»")) = Ложь Тогда
    Зап = Справочники.Контрагент.Создать();
    Зап.Наименование       = "ЗАО «Мебель без ручек»";
    Зап.ПолноеНаименование = "Закрытое акционерное общество «Мебель без ручек»";
    Зап.Вид                = "Поставщик";
    Зап.ИНН                = "7735001123";
    Зап.Записать();
  КонецЕсли;
  ПоставщикБезРучек = Справочники.Контрагент.НайтиПоНаименованию("ЗАО «Мебель без ручек»");

  // --- Покупатели ---

  Если ЗначениеЗаполнено(Справочники.Контрагент.НайтиПоНаименованию("Кафе «Три Стула»")) = Ложь Тогда
    Зап = Справочники.Контрагент.Создать();
    Зап.Наименование       = "Кафе «Три Стула»";
    Зап.ПолноеНаименование = "ООО «Кафе Три Стула»";
    Зап.Вид                = "Покупатель";
    Зап.ИНН                = "7702987654";
    Зап.ТипЦенПродажи      = ТипРозн;
    Зап.Записать();
  КонецЕсли;
  ПокупательКафе = Справочники.Контрагент.НайтиПоНаименованию("Кафе «Три Стула»");

  Если ЗначениеЗаполнено(Справочники.Контрагент.НайтиПоНаименованию("ООО «Сядь-Полежи»")) = Ложь Тогда
    Зап = Справочники.Контрагент.Создать();
    Зап.Наименование       = "ООО «Сядь-Полежи»";
    Зап.ПолноеНаименование = "ООО «Сядь-Полежи»";
    Зап.Вид                = "Покупатель";
    Зап.ИНН                = "7703456789";
    Зап.ТипЦенПродажи      = ТипРозн;
    Зап.Записать();
  КонецЕсли;
  ПокупательСядь = Справочники.Контрагент.НайтиПоНаименованию("ООО «Сядь-Полежи»");

  Если ЗначениеЗаполнено(Справочники.Контрагент.НайтиПоНаименованию("Гостиница «Три подушки»")) = Ложь Тогда
    Зап = Справочники.Контрагент.Создать();
    Зап.Наименование       = "Гостиница «Три подушки»";
    Зап.ПолноеНаименование = "ООО «Гостиничный комплекс Три подушки»";
    Зап.Вид                = "Покупатель";
    Зап.ИНН                = "7710555666";
    Зап.ТипЦенПродажи      = ТипРозн;
    Зап.Записать();
  КонецЕсли;
  ПокупательГостиница = Справочники.Контрагент.НайтиПоНаименованию("Гостиница «Три подушки»");

  Если ЗначениеЗаполнено(Справочники.Контрагент.НайтиПоНаименованию("Ресторан «Стол на двоих»")) = Ложь Тогда
    Зап = Справочники.Контрагент.Создать();
    Зап.Наименование       = "Ресторан «Стол на двоих»";
    Зап.ПолноеНаименование = "ООО «Ресторан Стол на двоих»";
    Зап.Вид                = "Покупатель";
    Зап.ИНН                = "7706777888";
    Зап.ТипЦенПродажи      = ТипРозн;
    Зап.Записать();
  КонецЕсли;
  ПокупательРесторан = Справочники.Контрагент.НайтиПоНаименованию("Ресторан «Стол на двоих»");

  Если ЗначениеЗаполнено(Справочники.Контрагент.НайтиПоНаименованию("ООО «Ремонт-Уют»")) = Ложь Тогда
    Зап = Справочники.Контрагент.Создать();
    Зап.Наименование       = "ООО «Ремонт-Уют»";
    Зап.ПолноеНаименование = "ООО «Ремонт-Уют»";
    Зап.Вид                = "Покупатель";
    Зап.ИНН                = "7707999000";
    Зап.ТипЦенПродажи      = ТипРозн;
    Зап.Записать();
  КонецЕсли;
  ПокупательРемонт = Справочники.Контрагент.НайтиПоНаименованию("ООО «Ремонт-Уют»");

  Если ЗначениеЗаполнено(Справочники.Контрагент.НайтиПоНаименованию("Детсад «Маленький стульчик»")) = Ложь Тогда
    Зап = Справочники.Контрагент.Создать();
    Зап.Наименование       = "Детсад «Маленький стульчик»";
    Зап.ПолноеНаименование = "МДОБУ «Детский сад Маленький стульчик»";
    Зап.Вид                = "Покупатель";
    Зап.ИНН                = "7708111222";
    Зап.ТипЦенПродажи      = ТипРозн;
    Зап.Записать();
  КонецЕсли;
  ПокупательДетсад = Справочники.Контрагент.НайтиПоНаименованию("Детсад «Маленький стульчик»");

  Если ЗначениеЗаполнено(Справочники.Контрагент.НайтиПоНаименованию("ИП Табуреткин В.В.")) = Ложь Тогда
    Зап = Справочники.Контрагент.Создать();
    Зап.Наименование       = "ИП Табуреткин В.В.";
    Зап.ПолноеНаименование = "Индивидуальный предприниматель Табуреткин Виктор Викторович";
    Зап.Вид                = "Поставщик";
    Зап.ОГРНИП             = "315774600000000";
    Зап.Записать();
  КонецЕсли;

  Если ЗначениеЗаполнено(Справочники.Контрагент.НайтиПоНаименованию("Табуреткин Эдуард Стулович")) = Ложь Тогда
    Зап = Справочники.Контрагент.Создать();
    Зап.Наименование       = "Табуреткин Эдуард Стулович";
    Зап.ПолноеНаименование = "Табуреткин Эдуард Стулович";
    Зап.Вид                = "Прочее";
    Зап.Записать();
  КонецЕсли;
  Учредитель = Справочники.Контрагент.НайтиПоНаименованию("Табуреткин Эдуард Стулович");

  // --- Номенклатура ---

  // Демо-картинки номенклатуры. Сгенерировано scripts/gen_demo_images.go
  // (перерисовать: go run scripts/gen_demo_images.go). Base64 иконок мебели 300×300.
  ФотоТабурет   = "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";
  ФотоКресло     = "iVBORw0KGgoAAAANSUhEUgAAASwAAAEsCAYAAAB5fY51AAAHK0lEQVR4nOzbrW4dwcGA4eRTLuAjQS0IqApzFUUBvYXywIDCgsKCwPDeQkFQryLQKghwUYjvIFWkWrUs2+dvd2fePc9DbR2Ndmbf3TNjv7m7vfn5CiDg/0YPAOBYggVkCBaQIVhAhmABGYIFZAgWkCFYQIZgARmCBWQIFpAhWECGYAEZggVkCBaQIVhAhmABGYIFZAgWkCFYQIZgARmCBWQIFpAhWECGYAEZggVkCBaQIVhAhmABGYIFZAgWkCFYQIZgARmCBWQIFpAhWECGYAEZggVkCBaQIVhAhmABGYIFZAgWkCFYQIZgARmCBWQIFpAhWECGYAEZggVkCBaQIVhAhmABGYIFZAgWkCFYQIZgARmCBWQIFpAhWECGYAEZggVkCBaQIVhAhmABGW9GD4DTfP74YfQQdufTl6+jh8CRXt/d3vwcPQieJk7jiNicBGtCQjUP4ZqLYE1EqOYlXHOw6T4JsZqb+ZmDYE3AzdBgnsYTrMHcBC3mayzBGsjibzJv4/g7rLj3796OHkLOt+8/Rg+BMzklHOTcp7RALe/cgDk53J43rAihWs/9tfXmNT97WAOc+nYlVts49Trby9qeYE1OrLbles9NsCbm5hnDdZ+XYE3KTTOW6z8nwQIyBGtjx2zUerrP4Zh5sPG+LcECMgQLyBAsIEOwJmP/ai7mYy6CBWQIFpAhWECGYAEZggVkCBaQIVhAhmABGYIFZAgWkCFYQIZgARmCBWQIFpAhWECGYAEZggVkCBaQIVhAhmABGYIFZAgWkCFYQIZgARmCBWQIFpAhWECGYAEZggVkCBaQIVhAhmABGYIFZAgWkCFYQIZgARmCBWQIFpAhWECGYAEZggVkCBaQIVhAhmABGYIFZAgWkCFYQIZgARmCtbFPX76++PNv339sNhYOOzQfh+aTZQkWkCFYQIZgARmCNSH7WHMwD/MRrAFs1O6DedyeYE3K030s139OgjXIMU9nN80Yx1x3b1djCNbkRGtbrvfcBGugY5/SbqJtHHudvV2N8/ru9ubn6EFcu88fPxz9u+/fvV11LNfolAeCWI0lWJM4JVoPCdjpzn1jFavxBGsi50aL9YnVHATrTP/825+e/dkf/vz3iz5buOZxaajWXCfXSLBO8NLie84li1K4xrkkVFuvk2siWI88FYkl9onu900u/Swnhstbak6WXCcP+Tr6P29GD2B2S21qz/Y5LGfJOfn1WR5Kz/N3WECGYL3A2wwjWHfPEywgQ7CADMF6htdyRrL+niZYQIZgARmCBWQIFpAhWECGYAEZggVkCBaQIVhAhmABGYIFZAgWkCFYQIZgARmCBWQIFpAhWECGYAEZggVkCBaQIVhAhmABGYIFZAgWkCFYQIZgARmCBWQIFpAhWECGYAEZggVkCBaQIVhAhmABGYIFZAgWkCFYz/j2/cfoIXDFrL+nCRaQIVhAhmC9wGs5I1h3zxMsIEOwDvC0Y0vW28vejB5Awf0iev/u7eihsFNCdRzBOsHDRSVeXEqkTidYZ3pusQkZjwnTcuxhLczi5CHrYVmCtQKLlFfWwSp8JVyJjfrrJVTrEayVPV68ArY/ArWd13e3Nz9HD2KvPn/8cPB3Pn35uslYWIY5HcseFpAhWECGYAEZgrUSex37dMycHTP3nEewgAzBAjIEC8gQLCBDsIAMwVqBE8J9c1I4jmABGYIFZAgWkCFYQIZgARmCtTAnhNfBSeEYggVkCBaQIVhAhmABGYIFZ7Lxvj3BWpATQliXYAEZggVkCBaQIVhAhmAtxIb7dXJSuC3BAjIEC8gQLCBDsIAMwQIyBGsBTgivm5PC7QgWkCFYQIZgARmCBWQIFpAhWBdyQsgrJ4WbESwgQ7CADMFiFf//29//ZvQY2J83owfAeQpBmH2Md7c3/x49Bk7z+u725ufoQZSdu+k++83MYU8FzyHMugRrAS8t0r/+41/CdEX+8sffvfjWJlaX8ZXwSC+9ER1apFyPXw+ol9bDS+vIV9TDvGH916Vf0Z5apN6urtca60HQrjBYa+8d/VqoQsW9LdbDNYVs18Gysc212mvEdhUsgYKn7SVg+WCJFJymHK9ksEQKllGLVypYQgXrqIQr87+EYgXrqdxfiWBVLiaUFe6z6YNVuIiwF7Pfb9MHq/LdGvZg9vtt+mC9ClxE2IPCfZYI1qvIxYSqyv2V+rOGe7N/z4aKSqjuJYP1kHjBaWqReigfrIfEC55WjtRDuwrWYwLGtdpLoB7bdbCeImLszV7j9JSrC9ZzhIzZXVOYniNYRxI01iZIhwnWQgSNQwTpcoI1iMD1CdD2BCtK8C4nOD2CxSp+BVUQWJpgARmZf34GECwgQ7CADMECMgQLyBAsIEOwgAzBAjIEC8gQLCBDsIAMwQIyBAvIECwgQ7CADMECMgQLyBAsIEOwgAzBAjIEC8gQLCDjPwEAAP//DhkBjqszGC8AAAAASUVORK5CYII=";
  ФотоСтол         = "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";
  ФотоДиван       = "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";
  ФотоПолка       = "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";
  ФотоПуф           = "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";
  ФотоШкаф         = "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";
  ФотоКомод       = "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";
  ФотоТумбочка = "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";
  ФотоКровать   = "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";
  ФотоСтеллаж   = "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";
  ФотоБанкетка = "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";
  ФотоНабор       = "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";


  Если ЗначениеЗаполнено(Справочники.Номенклатура.НайтиПоНаименованию("Табурет «Шаткий-2000»")) = Ложь Тогда
    Зап = Справочники.Номенклатура.Создать();
    Зап.Наименование     = "Табурет «Шаткий-2000»";
    Зап.Артикул          = "TAB-2000";
    Зап.ЕдиницаИзмерения = ЕдШт;
    Зап.СтавкаНДС        = Ставка20;
    Зап.ОсновноеИзображение = СохранитьКартинку(ФотоТабурет);
    Зап.Записать();
  КонецЕсли;
  НомТабурет = Справочники.Номенклатура.НайтиПоНаименованию("Табурет «Шаткий-2000»");

  Если ЗначениеЗаполнено(Справочники.Номенклатура.НайтиПоНаименованию("Кресло «Я тут главный»")) = Ложь Тогда
    Зап = Справочники.Номенклатура.Создать();
    Зап.Наименование     = "Кресло «Я тут главный»";
    Зап.Артикул          = "KRS-BOSS";
    Зап.ЕдиницаИзмерения = ЕдШт;
    Зап.СтавкаНДС        = Ставка20;
    Зап.ОсновноеИзображение = СохранитьКартинку(ФотоКресло);
    Зап.Записать();
  КонецЕсли;
  НомКресло = Справочники.Номенклатура.НайтиПоНаименованию("Кресло «Я тут главный»");

  Если ЗначениеЗаполнено(Справочники.Номенклатура.НайтиПоНаименованию("Стол «Внезапно Зашатался»")) = Ложь Тогда
    Зап = Справочники.Номенклатура.Создать();
    Зап.Наименование     = "Стол «Внезапно Зашатался»";
    Зап.Артикул          = "STL-WTF";
    Зап.ЕдиницаИзмерения = ЕдШт;
    Зап.СтавкаНДС        = Ставка20;
    Зап.ОсновноеИзображение = СохранитьКартинку(ФотоСтол);
    Зап.Записать();
  КонецЕсли;
  НомСтол = Справочники.Номенклатура.НайтиПоНаименованию("Стол «Внезапно Зашатался»");

  Если ЗначениеЗаполнено(Справочники.Номенклатура.НайтиПоНаименованию("Диван «Проваленный, но мягкий»")) = Ложь Тогда
    Зап = Справочники.Номенклатура.Создать();
    Зап.Наименование     = "Диван «Проваленный, но мягкий»";
    Зап.Артикул          = "DIV-SOFT";
    Зап.ЕдиницаИзмерения = ЕдШт;
    Зап.СтавкаНДС        = Ставка20;
    Зап.ОсновноеИзображение = СохранитьКартинку(ФотоДиван);
    Зап.Записать();
  КонецЕсли;
  НомДиван = Справочники.Номенклатура.НайтиПоНаименованию("Диван «Проваленный, но мягкий»");

  Если ЗначениеЗаполнено(Справочники.Номенклатура.НайтиПоНаименованию("Полка «Пизанская»")) = Ложь Тогда
    Зап = Справочники.Номенклатура.Создать();
    Зап.Наименование     = "Полка «Пизанская»";
    Зап.Артикул          = "PLK-PIZA";
    Зап.ЕдиницаИзмерения = ЕдШт;
    Зап.СтавкаНДС        = Ставка20;
    Зап.ОсновноеИзображение = СохранитьКартинку(ФотоПолка);
    Зап.Записать();
  КонецЕсли;
  НомПолка = Справочники.Номенклатура.НайтиПоНаименованию("Полка «Пизанская»");

  Если ЗначениеЗаполнено(Справочники.Номенклатура.НайтиПоНаименованию("Пуф «Просто куб»")) = Ложь Тогда
    Зап = Справочники.Номенклатура.Создать();
    Зап.Наименование     = "Пуф «Просто куб»";
    Зап.Артикул          = "PUF-CUBE";
    Зап.ЕдиницаИзмерения = ЕдШт;
    Зап.СтавкаНДС        = Ставка20;
    Зап.ОсновноеИзображение = СохранитьКартинку(ФотоПуф);
    Зап.Записать();
  КонецЕсли;
  НомПуф = Справочники.Номенклатура.НайтиПоНаименованию("Пуф «Просто куб»");

  Если ЗначениеЗаполнено(Справочники.Номенклатура.НайтиПоНаименованию("Шкаф «Секрет дедушки»")) = Ложь Тогда
    Зап = Справочники.Номенклатура.Создать();
    Зап.Наименование     = "Шкаф «Секрет дедушки»";
    Зап.Артикул          = "SHK-SECR";
    Зап.ЕдиницаИзмерения = ЕдШт;
    Зап.СтавкаНДС        = Ставка20;
    Зап.ОсновноеИзображение = СохранитьКартинку(ФотоШкаф);
    Зап.Записать();
  КонецЕсли;
  НомШкаф = Справочники.Номенклатура.НайтиПоНаименованию("Шкаф «Секрет дедушки»");

  Если ЗначениеЗаполнено(Справочники.Номенклатура.НайтиПоНаименованию("Комод «Спрятанное наследство»")) = Ложь Тогда
    Зап = Справочники.Номенклатура.Создать();
    Зап.Наименование     = "Комод «Спрятанное наследство»";
    Зап.Артикул          = "KMD-HEST";
    Зап.ЕдиницаИзмерения = ЕдШт;
    Зап.СтавкаНДС        = Ставка20;
    Зап.ОсновноеИзображение = СохранитьКартинку(ФотоКомод);
    Зап.Записать();
  КонецЕсли;
  НомКомод = Справочники.Номенклатура.НайтиПоНаименованию("Комод «Спрятанное наследство»");

  Если ЗначениеЗаполнено(Справочники.Номенклатура.НайтиПоНаименованию("Тумбочка «Ночная жизнь»")) = Ложь Тогда
    Зап = Справочники.Номенклатура.Создать();
    Зап.Наименование     = "Тумбочка «Ночная жизнь»";
    Зап.Артикул          = "TMB-NITE";
    Зап.ЕдиницаИзмерения = ЕдШт;
    Зап.СтавкаНДС        = Ставка20;
    Зап.ОсновноеИзображение = СохранитьКартинку(ФотоТумбочка);
    Зап.Записать();
  КонецЕсли;
  НомТумбочка = Справочники.Номенклатура.НайтиПоНаименованию("Тумбочка «Ночная жизнь»");

  Если ЗначениеЗаполнено(Справочники.Номенклатура.НайтиПоНаименованию("Кровать «Сон нации»")) = Ложь Тогда
    Зап = Справочники.Номенклатура.Создать();
    Зап.Наименование     = "Кровать «Сон нации»";
    Зап.Артикул          = "KRV-SLEP";
    Зап.ЕдиницаИзмерения = ЕдШт;
    Зап.СтавкаНДС        = Ставка20;
    Зап.ОсновноеИзображение = СохранитьКартинку(ФотоКровать);
    Зап.Записать();
  КонецЕсли;
  НомКровать = Справочники.Номенклатура.НайтиПоНаименованию("Кровать «Сон нации»");

  Если ЗначениеЗаполнено(Справочники.Номенклатура.НайтиПоНаименованию("Стеллаж «Книжная лихорадка»")) = Ложь Тогда
    Зап = Справочники.Номенклатура.Создать();
    Зап.Наименование     = "Стеллаж «Книжная лихорадка»";
    Зап.Артикул          = "STL-BOOK";
    Зап.ЕдиницаИзмерения = ЕдШт;
    Зап.СтавкаНДС        = Ставка20;
    Зап.ОсновноеИзображение = СохранитьКартинку(ФотоСтеллаж);
    Зап.Записать();
  КонецЕсли;
  НомСтеллаж = Справочники.Номенклатура.НайтиПоНаименованию("Стеллаж «Книжная лихорадка»");

  Если ЗначениеЗаполнено(Справочники.Номенклатура.НайтиПоНаименованию("Банкетка «Скамейка подсудимых»")) = Ложь Тогда
    Зап = Справочники.Номенклатура.Создать();
    Зап.Наименование     = "Банкетка «Скамейка подсудимых»";
    Зап.Артикул          = "BNK-GILT";
    Зап.ЕдиницаИзмерения = ЕдШт;
    Зап.СтавкаНДС        = Ставка20;
    Зап.ОсновноеИзображение = СохранитьКартинку(ФотоБанкетка);
    Зап.Записать();
  КонецЕсли;
  НомБанкетка = Справочники.Номенклатура.НайтиПоНаименованию("Банкетка «Скамейка подсудимых»");

  ТипОпт = Справочники.ТипЦен.НайтиПоНаименованию("Оптовая");

  // --- Набор для сборки ---
  Если ЗначениеЗаполнено(Справочники.Номенклатура.НайтиПоНаименованию("Набор «Столовый»")) = Ложь Тогда
    Зап = Справочники.Номенклатура.Создать();
    Зап.Наименование     = "Набор «Столовый»";
    Зап.Артикул          = "NAB-TBL";
    Зап.ЕдиницаИзмерения = ЕдШт;
    Зап.СтавкаНДС        = Ставка20;
    Зап.ОсновноеИзображение = СохранитьКартинку(ФотоНабор);
    Зап.Записать();
  КонецЕсли;
  НомНабор = Справочники.Номенклатура.НайтиПоНаименованию("Набор «Столовый»");

  // --- Минимальные остатки: проставляем и для УЖЕ существующих позиций ---
  // Минимум, заданный в блоках Создать() выше, применяется только к новой
  // номенклатуре. На базе, где позиции уже есть, эти блоки пропускаются —
  // поэтому здесь обновляем через ПолучитьОбъект()/Записать() безусловно.
  ПрожМин = Новый Массив;
  ПрожМин.Добавить("Кресло «Я тут главный»");        ПрожМин.Добавить(40);
  ПрожМин.Добавить("Стол «Внезапно Зашатался»");     ПрожМин.Добавить(8);
  ПрожМин.Добавить("Диван «Проваленный, но мягкий»"); ПрожМин.Добавить(20);
  ПрожМин.Добавить("Полка «Пизанская»");             ПрожМин.Добавить(10);
  ПрожМин.Добавить("Шкаф «Секрет дедушки»");         ПрожМин.Добавить(10);
  ПрожМин.Добавить("Комод «Спрятанное наследство»"); ПрожМин.Добавить(10);
  ПрожМин.Добавить("Кровать «Сон нации»");           ПрожМин.Добавить(5);
  Инд = 0;
  Пока Инд < ПрожМин.Количество() Цикл
    СсМин = Справочники.Номенклатура.НайтиПоНаименованию(ПрожМин[Инд]);
    Если ЗначениеЗаполнено(СсМин) Тогда
      ОбъМин = СсМин.ПолучитьОбъект();
      ОбъМин.МинимальныйОстаток = ПрожМин[Инд + 1];
      ОбъМин.Записать();
    КонецЕсли;
    Инд = Инд + 2;
  КонецЦикла;

  // --- Основные изображения: проставляем и для УЖЕ существующих позиций ---
  // Картинка, заданная в блоках Создать() выше, применяется только к новой
  // номенклатуре. На базе, где позиции уже есть (повторное заполнение), эти
  // блоки пропускаются — поэтому здесь обновляем через ПолучитьОбъект()/Записать().
  // В отличие от МинимальныйОстаток, гард обязателен: СохранитьКартинку каждый
  // раз создаёт НОВЫЙ бинарник в _blobs, и безусловная перезапись плодила бы
  // дубли на каждом запуске. Ставим только если картинки ещё нет.
  ПарыКартинок = Новый Массив;
  ПарыКартинок.Добавить("Табурет «Шаткий-2000»");           ПарыКартинок.Добавить(ФотоТабурет);
  ПарыКартинок.Добавить("Кресло «Я тут главный»");           ПарыКартинок.Добавить(ФотоКресло);
  ПарыКартинок.Добавить("Стол «Внезапно Зашатался»");         ПарыКартинок.Добавить(ФотоСтол);
  ПарыКартинок.Добавить("Диван «Проваленный, но мягкий»");   ПарыКартинок.Добавить(ФотоДиван);
  ПарыКартинок.Добавить("Полка «Пизанская»");                 ПарыКартинок.Добавить(ФотоПолка);
  ПарыКартинок.Добавить("Пуф «Просто куб»");                  ПарыКартинок.Добавить(ФотоПуф);
  ПарыКартинок.Добавить("Шкаф «Секрет дедушки»");             ПарыКартинок.Добавить(ФотоШкаф);
  ПарыКартинок.Добавить("Комод «Спрятанное наследство»");     ПарыКартинок.Добавить(ФотоКомод);
  ПарыКартинок.Добавить("Тумбочка «Ночная жизнь»");           ПарыКартинок.Добавить(ФотоТумбочка);
  ПарыКартинок.Добавить("Кровать «Сон нации»");               ПарыКартинок.Добавить(ФотоКровать);
  ПарыКартинок.Добавить("Стеллаж «Книжная лихорадка»");       ПарыКартинок.Добавить(ФотоСтеллаж);
  ПарыКартинок.Добавить("Банкетка «Скамейка подсудимых»");    ПарыКартинок.Добавить(ФотоБанкетка);
  ПарыКартинок.Добавить("Набор «Столовый»");                  ПарыКартинок.Добавить(ФотоНабор);
  Инд = 0;
  Пока Инд < ПарыКартинок.Количество() Цикл
    СсКарт = Справочники.Номенклатура.НайтиПоНаименованию(ПарыКартинок[Инд]);
    Если ЗначениеЗаполнено(СсКарт) И НЕ ЗначениеЗаполнено(ЗначениеРеквизитаОбъекта(СсКарт, "ОсновноеИзображение")) Тогда
      ОбъКарт = СсКарт.ПолучитьОбъект();
      ОбъКарт.ОсновноеИзображение = СохранитьКартинку(ПарыКартинок[Инд + 1]);
      ОбъКарт.Записать();
    КонецЕсли;
    Инд = Инд + 2;
  КонецЦикла;

  Если ЗначениеЗаполнено(Справочники.НастройкиПользователя.НайтиПоНаименованию("Общие")) = Ложь Тогда
    Зап = Справочники.НастройкиПользователя.Создать();
    Зап.Наименование  = "Общие";
    Зап.Склад         = СкладГлавный;
    Зап.Организация   = НашаОрг;
    Зап.ТипЦенПродажи = ТипРозн;
    Зап.Записать();
  КонецЕсли;

  // --- Настройки пользователей по ролям (для виджета «Пользователи») ---
  // Наименование = логин. Создаются идемпотентно, по примеру ролей конфигурации.
  Если ЗначениеЗаполнено(Справочники.НастройкиПользователя.НайтиПоНаименованию("Менеджер")) = Ложь Тогда
    Зап = Справочники.НастройкиПользователя.Создать();
    Зап.Наименование  = "Менеджер";
    Зап.Склад         = СкладГлавный;
    Зап.Организация   = НашаОрг;
    Зап.ТипЦенПродажи = ТипОпт;
    Зап.Записать();
  КонецЕсли;

  Если ЗначениеЗаполнено(Справочники.НастройкиПользователя.НайтиПоНаименованию("Кладовщик")) = Ложь Тогда
    Зап = Справочники.НастройкиПользователя.Создать();
    Зап.Наименование  = "Кладовщик";
    Зап.Склад         = СкладГлавный;
    Зап.Организация   = НашаОрг;
    Зап.ТипЦенПродажи = ТипРозн;
    Зап.Записать();
  КонецЕсли;

  Если ЗначениеЗаполнено(Справочники.НастройкиПользователя.НайтиПоНаименованию("Кассир")) = Ложь Тогда
    Зап = Справочники.НастройкиПользователя.Создать();
    Зап.Наименование  = "Кассир";
    Зап.Склад         = СкладГлавный;
    Зап.Организация   = НашаОрг;
    Зап.ТипЦенПродажи = ТипРозн;
    Зап.Записать();
  КонецЕсли;

  Если ЗначениеЗаполнено(Справочники.НастройкиПользователя.НайтиПоНаименованию("Снабженец")) = Ложь Тогда
    Зап = Справочники.НастройкиПользователя.Создать();
    Зап.Наименование  = "Снабженец";
    Зап.Склад         = СкладУценка;
    Зап.Организация   = НашаОрг;
    Зап.ТипЦенПродажи = ТипОпт;
    Зап.Записать();
  КонецЕсли;

  Сообщить("Справочники готовы.");

  // ============ ОЧИСТКА ДОКУМЕНТОВ (по умолчанию включена) ============

  Очищаем = (Параметры.Очистить <> Ложь);
  Если Очищаем Тогда
    Удал = 0;
    Попытка
      // Порядок удаления: сначала документы-основания (листья), потом документы-родители
      // ВозвратОтПокупателя → РеализацияТоваров → Счёт/ЗаказПокупателя
      // ВозвратПоставщику → ПоступлениеТоваров → ЗаказПоставщику
      ЗД = Новый Запрос; ЗД.Текст = "ВЫБРАТЬ Номер ИЗ Документ.ВозвратОтПокупателя";
      Для Каждого Стр Из ЗД.Выполнить() Цикл
        Об = Документы.ВозвратОтПокупателя.НайтиПоНомеру(Стр.Номер);
        Если ЗначениеЗаполнено(Об) Тогда
          Документы.ВозвратОтПокупателя.Удалить(Об);
          Удал = Удал + 1;
        КонецЕсли;
      КонецЦикла;
      ЗД = Новый Запрос; ЗД.Текст = "ВЫБРАТЬ Номер ИЗ Документ.ВозвратПоставщику";
      Для Каждого Стр Из ЗД.Выполнить() Цикл
        Об = Документы.ВозвратПоставщику.НайтиПоНомеру(Стр.Номер);
        Если ЗначениеЗаполнено(Об) Тогда
          Документы.ВозвратПоставщику.Удалить(Об);
          Удал = Удал + 1;
        КонецЕсли;
      КонецЦикла;
      ЗД = Новый Запрос; ЗД.Текст = "ВЫБРАТЬ Номер ИЗ Документ.ПриходныйКассовыйОрдер";
      Для Каждого Стр Из ЗД.Выполнить() Цикл
        Об = Документы.ПриходныйКассовыйОрдер.НайтиПоНомеру(Стр.Номер);
        Если ЗначениеЗаполнено(Об) Тогда
          Документы.ПриходныйКассовыйОрдер.Удалить(Об);
          Удал = Удал + 1;
        КонецЕсли;
      КонецЦикла;
      ЗД = Новый Запрос; ЗД.Текст = "ВЫБРАТЬ Номер ИЗ Документ.РасходныйКассовыйОрдер";
      Для Каждого Стр Из ЗД.Выполнить() Цикл
        Об = Документы.РасходныйКассовыйОрдер.НайтиПоНомеру(Стр.Номер);
        Если ЗначениеЗаполнено(Об) Тогда
          Документы.РасходныйКассовыйОрдер.Удалить(Об);
          Удал = Удал + 1;
        КонецЕсли;
      КонецЦикла;
      ЗД = Новый Запрос; ЗД.Текст = "ВЫБРАТЬ Номер ИЗ Документ.ПоступлениеНаРасчётныйСчёт";
      Для Каждого Стр Из ЗД.Выполнить() Цикл
        Об = Документы.ПоступлениеНаРасчётныйСчёт.НайтиПоНомеру(Стр.Номер);
        Если ЗначениеЗаполнено(Об) Тогда
          Документы.ПоступлениеНаРасчётныйСчёт.Удалить(Об);
          Удал = Удал + 1;
        КонецЕсли;
      КонецЦикла;
      ЗД = Новый Запрос; ЗД.Текст = "ВЫБРАТЬ Номер ИЗ Документ.СписаниеСРасчётногоСчёта";
      Для Каждого Стр Из ЗД.Выполнить() Цикл
        Об = Документы.СписаниеСРасчётногоСчёта.НайтиПоНомеру(Стр.Номер);
        Если ЗначениеЗаполнено(Об) Тогда
          Документы.СписаниеСРасчётногоСчёта.Удалить(Об);
          Удал = Удал + 1;
        КонецЕсли;
      КонецЦикла;
      ЗД = Новый Запрос; ЗД.Текст = "ВЫБРАТЬ Номер ИЗ Документ.РеализацияТоваров";
      Для Каждого Стр Из ЗД.Выполнить() Цикл
        Об = Документы.РеализацияТоваров.НайтиПоНомеру(Стр.Номер);
        Если ЗначениеЗаполнено(Об) Тогда
          Документы.РеализацияТоваров.Удалить(Об);
          Удал = Удал + 1;
        КонецЕсли;
      КонецЦикла;
      ЗД = Новый Запрос; ЗД.Текст = "ВЫБРАТЬ Номер ИЗ Документ.ПоступлениеТоваров";
      Для Каждого Стр Из ЗД.Выполнить() Цикл
        Об = Документы.ПоступлениеТоваров.НайтиПоНомеру(Стр.Номер);
        Если ЗначениеЗаполнено(Об) Тогда
          Документы.ПоступлениеТоваров.Удалить(Об);
          Удал = Удал + 1;
        КонецЕсли;
      КонецЦикла;
      ЗД = Новый Запрос; ЗД.Текст = "ВЫБРАТЬ Номер ИЗ Документ.ЗаказПокупателя";
      Для Каждого Стр Из ЗД.Выполнить() Цикл
        Об = Документы.ЗаказПокупателя.НайтиПоНомеру(Стр.Номер);
        Если ЗначениеЗаполнено(Об) Тогда
          Документы.ЗаказПокупателя.Удалить(Об);
          Удал = Удал + 1;
        КонецЕсли;
      КонецЦикла;
      ЗД = Новый Запрос; ЗД.Текст = "ВЫБРАТЬ Номер ИЗ Документ.ЗаказПоставщику";
      Для Каждого Стр Из ЗД.Выполнить() Цикл
        Об = Документы.ЗаказПоставщику.НайтиПоНомеру(Стр.Номер);
        Если ЗначениеЗаполнено(Об) Тогда
          Документы.ЗаказПоставщику.Удалить(Об);
          Удал = Удал + 1;
        КонецЕсли;
      КонецЦикла;
      ЗД = Новый Запрос; ЗД.Текст = "ВЫБРАТЬ Номер ИЗ Документ.Счёт";
      Для Каждого Стр Из ЗД.Выполнить() Цикл
        Об = Документы.Счёт.НайтиПоНомеру(Стр.Номер);
        Если ЗначениеЗаполнено(Об) Тогда
          Документы.Счёт.Удалить(Об);
          Удал = Удал + 1;
        КонецЕсли;
      КонецЦикла;
      ЗД = Новый Запрос; ЗД.Текст = "ВЫБРАТЬ Номер ИЗ Документ.ПеремещениеТоваров";
      Для Каждого Стр Из ЗД.Выполнить() Цикл
        Об = Документы.ПеремещениеТоваров.НайтиПоНомеру(Стр.Номер);
        Если ЗначениеЗаполнено(Об) Тогда
          Документы.ПеремещениеТоваров.Удалить(Об);
          Удал = Удал + 1;
        КонецЕсли;
      КонецЦикла;
      ЗД = Новый Запрос; ЗД.Текст = "ВЫБРАТЬ Номер ИЗ Документ.СписаниеТоваров";
      Для Каждого Стр Из ЗД.Выполнить() Цикл
        Об = Документы.СписаниеТоваров.НайтиПоНомеру(Стр.Номер);
        Если ЗначениеЗаполнено(Об) Тогда
          Документы.СписаниеТоваров.Удалить(Об);
          Удал = Удал + 1;
        КонецЕсли;
      КонецЦикла;
      ЗД = Новый Запрос; ЗД.Текст = "ВЫБРАТЬ Номер ИЗ Документ.ОприходованиеТоваров";
      Для Каждого Стр Из ЗД.Выполнить() Цикл
        Об = Документы.ОприходованиеТоваров.НайтиПоНомеру(Стр.Номер);
        Если ЗначениеЗаполнено(Об) Тогда
          Документы.ОприходованиеТоваров.Удалить(Об);
          Удал = Удал + 1;
        КонецЕсли;
      КонецЦикла;
      ЗД = Новый Запрос; ЗД.Текст = "ВЫБРАТЬ Номер ИЗ Документ.СборкаТоваров";
      Для Каждого Стр Из ЗД.Выполнить() Цикл
        Об = Документы.СборкаТоваров.НайтиПоНомеру(Стр.Номер);
        Если ЗначениеЗаполнено(Об) Тогда
          Документы.СборкаТоваров.Удалить(Об);
          Удал = Удал + 1;
        КонецЕсли;
      КонецЦикла;
      ЗД = Новый Запрос; ЗД.Текст = "ВЫБРАТЬ Номер ИЗ Документ.РазборкаТоваров";
      Для Каждого Стр Из ЗД.Выполнить() Цикл
        Об = Документы.РазборкаТоваров.НайтиПоНомеру(Стр.Номер);
        Если ЗначениеЗаполнено(Об) Тогда
          Документы.РазборкаТоваров.Удалить(Об);
          Удал = Удал + 1;
        КонецЕсли;
      КонецЦикла;
      ЗД = Новый Запрос; ЗД.Текст = "ВЫБРАТЬ Номер ИЗ Документ.УстановкаЦен";
      Для Каждого Стр Из ЗД.Выполнить() Цикл
        Об = Документы.УстановкаЦен.НайтиПоНомеру(Стр.Номер);
        Если ЗначениеЗаполнено(Об) Тогда
          Документы.УстановкаЦен.Удалить(Об);
          Удал = Удал + 1;
        КонецЕсли;
      КонецЦикла;
      Сообщить("Очищено документов: " + Строка(Удал));
    Исключение
      Сообщить("Очистка не выполнена: " + ОписаниеОшибки());
    КонецПопытки;
  КонецЕсли;

  // Создаём ТОЛЬКО если поступлений нет — это исключает накопление дублей
  ЗПест = Новый Запрос; ЗПест.Текст = "ВЫБРАТЬ Номер ИЗ Документ.ПоступлениеТоваров";
  ЕстьПост = Ложь;
  Для Каждого Д Из ЗПест.Выполнить() Цикл ЕстьПост = Истина; Прервать; КонецЦикла;
  Создавать = (ЕстьПост = Ложь);

  // ============ СОЗДАНИЕ И ПРОВЕДЕНИЕ (один проход) ============

  Если Создавать Тогда
    Сегодня = ТекущаяДата();

    // Установить константу НашаОрганизация — нужна для подбора и форм по умолчанию
    Константы.НашаОрганизация = НашаОрг;

    // 6 месячных слотов: поступления → продажи → деньги разнесены по месяцам
    // для полноценных виджетов «Поступления по месяцам» (3+ столбца),
    // «Приход и расход денег» (6 точек), «Товары к заказу» (5 позиций).
    ДатаМ1 = ДобавитьМесяц(Сегодня, -5);  // взнос, установка цен
    ДатаМ2 = ДобавитьМесяц(Сегодня, -4);  // заказы поставщикам, Пост1, деньги
    ДатаМ3 = ДобавитьМесяц(Сегодня, -3);  // Пост2, Пост3, Реал1, деньги
    ДатаМ4 = ДобавитьМесяц(Сегодня, -2);  // Пост4, оприходования, Реал2, Реал3, деньги
    ДатаМ5 = ДобавитьМесяц(Сегодня, -1);  // перемещения, сборки, Реал4, Реал5, деньги
    ДатаМ6 = Сегодня;                      // счета, заказы, Реал6, возвраты, списания, пятые деньги

    // ---- ВЗНОС УЧРЕДИТЕЛЯ (месяц 1) ----

    ПКОуст = Документы.ПриходныйКассовыйОрдер.Создать();
    ПКОуст.Номер = "ПКО-00000";
    ПКОуст.Дата = ДатаМ1; ПКОуст.Организация = НашаОрг; ПКОуст.Касса = КассаНал;
    ПКОуст.Контрагент = Учредитель; ПКОуст.Основание = "Взнос учредителя в уставный капитал";
    ПКОуст.Сумма = 500000;
    ПКОуст.Записать(); ПКОуст.Провести();

    Сообщить("Взнос учредителя (500 000) проведён.");

    // ---- УСТАНОВКА ЦЕН (месяц 1) ----

    УЦ = Документы.УстановкаЦен.Создать();
    УЦ.Номер = "УЦ-00001";
    УЦ.Дата = ДатаМ1; УЦ.Организация = НашаОрг; УЦ.ТипЦен = ТипОпт;
    Стр = УЦ.Цены.Добавить(); Стр.Номенклатура = НомТабурет;  Стр.Цена = 700;
    Стр = УЦ.Цены.Добавить(); Стр.Номенклатура = НомКресло;   Стр.Цена = 4200;
    Стр = УЦ.Цены.Добавить(); Стр.Номенклатура = НомСтол;     Стр.Цена = 3500;
    Стр = УЦ.Цены.Добавить(); Стр.Номенклатура = НомДиван;    Стр.Цена = 11000;
    Стр = УЦ.Цены.Добавить(); Стр.Номенклатура = НомПолка;    Стр.Цена = 950;
    Стр = УЦ.Цены.Добавить(); Стр.Номенклатура = НомПуф;      Стр.Цена = 580;
    Стр = УЦ.Цены.Добавить(); Стр.Номенклатура = НомШкаф;     Стр.Цена = 17000;
    Стр = УЦ.Цены.Добавить(); Стр.Номенклатура = НомКомод;    Стр.Цена = 7000;
    Стр = УЦ.Цены.Добавить(); Стр.Номенклатура = НомТумбочка; Стр.Цена = 2100;
    Стр = УЦ.Цены.Добавить(); Стр.Номенклатура = НомКровать;  Стр.Цена = 20000;
    Стр = УЦ.Цены.Добавить(); Стр.Номенклатура = НомСтеллаж;  Стр.Цена = 5000;
    Стр = УЦ.Цены.Добавить(); Стр.Номенклатура = НомБанкетка; Стр.Цена = 850;
    Стр = УЦ.Цены.Добавить(); Стр.Номенклатура = НомНабор;    Стр.Цена = 4900;
    УЦ.Записать(); УЦ.Провести();

    // Розничная — расчётный тип цен, вычисляется автоматически от Оптовой.
    // Явная установка через УстановкаЦен запрещена (ПриЗаписи проверяет ВидРасчета).

    Сообщить("Установка оптовых цен (13 позиций) проведена. Розничные — расчётный тип, вычисляются автоматически.");

    // ---- ЗАКАЗЫ ПОСТАВЩИКАМ (месяц 2) ----

    ЗакПост1 = Документы.ЗаказПоставщику.Создать();
    ЗакПост1.Номер = "ЗПС-00001";
    ЗакПост1.Дата = ДатаМ2; ЗакПост1.Организация = НашаОрг; ЗакПост1.Поставщик = ПоставщикДерево;
    ЗакПост1.Склад = СкладГлавный; ЗакПост1.СпособУчетаНДС = "ВТомЧисле";
    ЗакПост1.Комментарий = "Табуреты, кресла и столы — заказ на квартал";
    Стр = ЗакПост1.Товары.Добавить(); Стр.Номенклатура = НомТабурет; Стр.Количество = 100; Стр.Цена = 500;
    Стр = ЗакПост1.Товары.Добавить(); Стр.Номенклатура = НомКресло;  Стр.Количество = 40;  Стр.Цена = 3000;
    Стр = ЗакПост1.Товары.Добавить(); Стр.Номенклатура = НомСтол;    Стр.Количество = 30;  Стр.Цена = 2500;
    ЗакПост1.Записать(); ЗакПост1.Провести();

    ЗакПост2 = Документы.ЗаказПоставщику.Создать();
    ЗакПост2.Номер = "ЗПС-00002";
    ЗакПост2.Дата = ДатаМ2; ЗакПост2.Организация = НашаОрг; ЗакПост2.Поставщик = ПоставщикФанера;
    ЗакПост2.Склад = СкладГлавный; ЗакПост2.СпособУчетаНДС = "ВТомЧисле";
    ЗакПост2.Комментарий = "Диваны, полки и пуфы — мягкая часть ассортимента";
    Стр = ЗакПост2.Товары.Добавить(); Стр.Номенклатура = НомДиван; Стр.Количество = 20; Стр.Цена = 8000;
    Стр = ЗакПост2.Товары.Добавить(); Стр.Номенклатура = НомПолка; Стр.Количество = 60; Стр.Цена = 700;
    Стр = ЗакПост2.Товары.Добавить(); Стр.Номенклатура = НомПуф;   Стр.Количество = 50; Стр.Цена = 400;
    ЗакПост2.Записать(); ЗакПост2.Провести();

    Сообщить("Заказы поставщикам (2 шт.) проведены.");

    // ---- ПОСТУПЛЕНИЯ (разнесены по 3 месяцам для виджета) ----

    // Поступление 1 (месяц 2): Дерево и Гвозди — табуреты, кресла, столы
    Пост1 = Документы.ПоступлениеТоваров.Создать();
    Пост1.Номер = "ПОС-00001";
    Пост1.Дата = ДатаМ2; Пост1.Организация = НашаОрг; Пост1.Поставщик = ПоставщикДерево;
    Пост1.Склад = СкладГлавный; Пост1.СпособУчетаНДС = "ВТомЧисле";
    Стр = Пост1.Товары.Добавить(); Стр.Номенклатура = НомТабурет; Стр.Количество = 100; Стр.Цена = 500;
    Стр = Пост1.Товары.Добавить(); Стр.Номенклатура = НомКресло;  Стр.Количество = 40;  Стр.Цена = 3000;
    Стр = Пост1.Товары.Добавить(); Стр.Номенклатура = НомСтол;    Стр.Количество = 30;  Стр.Цена = 2500;
    Пост1.Записать(); Пост1.Провести();

    // Поступление 2 (месяц 3): Фанера-Палас — диваны, полки, пуфы
    Пост2 = Документы.ПоступлениеТоваров.Создать();
    Пост2.Номер = "ПОС-00002";
    Пост2.Дата = ДатаМ3; Пост2.Организация = НашаОрг; Пост2.Поставщик = ПоставщикФанера;
    Пост2.Склад = СкладГлавный; Пост2.СпособУчетаНДС = "ВТомЧисле";
    Стр = Пост2.Товары.Добавить(); Стр.Номенклатура = НомДиван; Стр.Количество = 20; Стр.Цена = 8000;
    Стр = Пост2.Товары.Добавить(); Стр.Номенклатура = НомПолка; Стр.Количество = 60; Стр.Цена = 700;
    Стр = Пост2.Товары.Добавить(); Стр.Номенклатура = НомПуф;   Стр.Количество = 50; Стр.Цена = 400;
    Пост2.Записать(); Пост2.Провести();

    // Поступление 3 (месяц 3): Гвоздь в стене — стеллажи, комоды
    Пост3 = Документы.ПоступлениеТоваров.Создать();
    Пост3.Номер = "ПОС-00003";
    Пост3.Дата = ДатаМ3; Пост3.Организация = НашаОрг; Пост3.Поставщик = ПоставщикГвоздь;
    Пост3.Склад = СкладГлавный; Пост3.СпособУчетаНДС = "ВТомЧисле";
    Стр = Пост3.Товары.Добавить(); Стр.Номенклатура = НомСтеллаж; Стр.Количество = 25; Стр.Цена = 3500;
    Стр = Пост3.Товары.Добавить(); Стр.Номенклатура = НомКомод;   Стр.Количество = 15; Стр.Цена = 5000;
    Пост3.Записать(); Пост3.Провести();

    // Поступление 4 (месяц 4): Мебель без ручек — шкафы, тумбочки, кровати
    Пост4 = Документы.ПоступлениеТоваров.Создать();
    Пост4.Номер = "ПОС-00004";
    Пост4.Дата = ДатаМ4; Пост4.Организация = НашаОрг; Пост4.Поставщик = ПоставщикБезРучек;
    Пост4.Склад = СкладГлавный; Пост4.СпособУчетаНДС = "ВТомЧисле";
    Стр = Пост4.Товары.Добавить(); Стр.Номенклатура = НомШкаф;     Стр.Количество = 10; Стр.Цена = 12000;
    Стр = Пост4.Товары.Добавить(); Стр.Номенклатура = НомТумбочка; Стр.Количество = 35; Стр.Цена = 1500;
    Стр = Пост4.Товары.Добавить(); Стр.Номенклатура = НомКровать;  Стр.Количество = 8;  Стр.Цена = 15000;
    Пост4.Записать(); Пост4.Провести();

    Сообщить("Поступления (4 шт., 3 месяца) проведены.");

    // ---- ОПРИХОДОВАНИЯ (месяц 4) ----

    Опр1 = Документы.ОприходованиеТоваров.Создать();
    Опр1.Номер = "ОПР-00001";
    Опр1.Дата = ДатаМ4; Опр1.Организация = НашаОрг; Опр1.Склад = СкладУценка;
    Опр1.Причина = "Обнаружено при инвентаризации под столом";
    Стр = Опр1.Товары.Добавить(); Стр.Номенклатура = НомТабурет;  Стр.Количество = 7; Стр.Цена = 450;
    Стр = Опр1.Товары.Добавить(); Стр.Номенклатура = НомБанкетка; Стр.Количество = 5; Стр.Цена = 600;
    Опр1.Записать(); Опр1.Провести();

    Опр2 = Документы.ОприходованиеТоваров.Создать();
    Опр2.Номер = "ОПР-00002";
    Опр2.Дата = ДатаМ4; Опр2.Организация = НашаОрг; Опр2.Склад = СкладУценка;
    Опр2.Причина = "Курьер принес «не туда», но товар хороший";
    Стр = Опр2.Товары.Добавить(); Стр.Номенклатура = НомПолка; Стр.Количество = 3; Стр.Цена = 650;
    Опр2.Записать(); Опр2.Провести();

    Сообщить("Оприходования (2 шт.) проведены.");

    // ---- РЕАЛИЗАЦИИ (разнесены по 4 месяцам) ----

    // Реализация 1 (месяц 3): Кафе — табуреты и столы (после Пост1)
    Реал1 = Документы.РеализацияТоваров.Создать();
    Реал1.Номер = "РЕА-00001";
    Реал1.Дата = ДатаМ3; Реал1.Организация = НашаОрг; Реал1.Покупатель = ПокупательКафе;
    Реал1.Склад = СкладГлавный; Реал1.ТипЦенПродажи = ТипРозн; Реал1.СпособУчетаНДС = "ВТомЧисле";
    Стр = Реал1.Товары.Добавить(); Стр.Номенклатура = НомТабурет; Стр.Количество = 10; Стр.Цена = 900;
    Стр = Реал1.Товары.Добавить(); Стр.Номенклатура = НомСтол;    Стр.Количество = 3;  Стр.Цена = 4500;
    Реал1.Записать(); Реал1.Провести();

    // Реализация 2 (месяц 4): Сядь-Полежи — диваны и полки (после Пост2)
    Реал2 = Документы.РеализацияТоваров.Создать();
    Реал2.Номер = "РЕА-00002";
    Реал2.Дата = ДатаМ4; Реал2.Организация = НашаОрг; Реал2.Покупатель = ПокупательСядь;
    Реал2.Склад = СкладГлавный; Реал2.ТипЦенПродажи = ТипРозн; Реал2.СпособУчетаНДС = "ВТомЧисле";
    Стр = Реал2.Товары.Добавить(); Стр.Номенклатура = НомДиван; Стр.Количество = 5;  Стр.Цена = 14000;
    Стр = Реал2.Товары.Добавить(); Стр.Номенклатура = НомПолка; Стр.Количество = 20; Стр.Цена = 800;
    Реал2.Записать(); Реал2.Провести();

    // Реализация 3 (месяц 4): Ресторан — кресла, столы, стеллажи (после Пост1+Пост3)
    Реал3 = Документы.РеализацияТоваров.Создать();
    Реал3.Номер = "РЕА-00003";
    Реал3.Дата = ДатаМ4; Реал3.Организация = НашаОрг; Реал3.Покупатель = ПокупательРесторан;
    Реал3.Склад = СкладГлавный; Реал3.ТипЦенПродажи = ТипРозн; Реал3.СпособУчетаНДС = "ВТомЧисле";
    Стр = Реал3.Товары.Добавить(); Стр.Номенклатура = НомКресло;   Стр.Количество = 15; Стр.Цена = 7000;
    Стр = Реал3.Товары.Добавить(); Стр.Номенклатура = НомСтол;     Стр.Количество = 10; Стр.Цена = 4500;
    Стр = Реал3.Товары.Добавить(); Стр.Номенклатура = НомСтеллаж;  Стр.Количество = 5;  Стр.Цена = 6500;
    Реал3.Записать(); Реал3.Провести();

    // ---- ПЕРЕМЕЩЕНИЯ (месяц 5) ----

    Пер1 = Документы.ПеремещениеТоваров.Создать();
    Пер1.Номер = "ПРМ-00001";
    Пер1.Дата = ДатаМ5; Пер1.Организация = НашаОрг;
    Пер1.СкладОтправитель = СкладГлавный; Пер1.СкладПолучатель = СкладУценка;
    Стр = Пер1.Товары.Добавить(); Стр.Номенклатура = НомПолка;    Стр.Количество = 10;
    Стр = Пер1.Товары.Добавить(); Стр.Номенклатура = НомТабурет;  Стр.Количество = 15;
    Пер1.Записать(); Пер1.Провести();

    Пер2 = Документы.ПеремещениеТоваров.Создать();
    Пер2.Номер = "ПРМ-00002";
    Пер2.Дата = ДатаМ5; Пер2.Организация = НашаОрг;
    Пер2.СкладОтправитель = СкладГлавный; Пер2.СкладПолучатель = СкладУценка;
    Стр = Пер2.Товары.Добавить(); Стр.Номенклатура = НомПуф; Стр.Количество = 8;
    Пер2.Записать(); Пер2.Провести();

    Сообщить("Перемещения (2 шт.) проведены.");

    // ---- СБОРКА (месяц 5) ----

    Сбр = Документы.СборкаТоваров.Создать();
    Сбр.Номер = "СБР-00001";
    Сбр.Дата = ДатаМ5; Сбр.Организация = НашаОрг; Сбр.Склад = СкладГлавный;
    Сбр.Комментарий = "Комплект: 2 табурета + стол — готовый набор";
    Стр = Сбр.Расход.Добавить(); Стр.Номенклатура = НомТабурет; Стр.Количество = 2; Стр.Себестоимость = 500;
    Стр = Сбр.Расход.Добавить(); Стр.Номенклатура = НомСтол;    Стр.Количество = 1; Стр.Себестоимость = 2500;
    Стр = Сбр.Приход.Добавить(); Стр.Номенклатура = НомНабор;   Стр.Количество = 1; Стр.Себестоимость = 3500;
    Сбр.Записать(); Сбр.Провести();

    Сообщить("Сборки (1 шт.) проведены.");

    // Реализация 4 (месяц 5): Детсад — табуреты, пуфы
    Реал4 = Документы.РеализацияТоваров.Создать();
    Реал4.Номер = "РЕА-00004";
    Реал4.Дата = ДатаМ5; Реал4.Организация = НашаОрг; Реал4.Покупатель = ПокупательДетсад;
    Реал4.Склад = СкладГлавный; Реал4.ТипЦенПродажи = ТипРозн; Реал4.СпособУчетаНДС = "ВТомЧисле";
    Стр = Реал4.Товары.Добавить(); Стр.Номенклатура = НомТабурет; Стр.Количество = 25; Стр.Цена = 900;
    Стр = Реал4.Товары.Добавить(); Стр.Номенклатура = НомПуф;     Стр.Количество = 15; Стр.Цена = 750;
    Реал4.Записать(); Реал4.Провести();

    // Реализация 5 (месяц 5): Гостиница — кровати, тумбочки, шкафы (после Пост4)
    Реал5 = Документы.РеализацияТоваров.Создать();
    Реал5.Номер = "РЕА-00005";
    Реал5.Дата = ДатаМ5; Реал5.Организация = НашаОрг; Реал5.Покупатель = ПокупательГостиница;
    Реал5.Склад = СкладГлавный; Реал5.ТипЦенПродажи = ТипРозн; Реал5.СпособУчетаНДС = "ВТомЧисле";
    Стр = Реал5.Товары.Добавить(); Стр.Номенклатура = НомКровать;  Стр.Количество = 4; Стр.Цена = 35000;
    Стр = Реал5.Товары.Добавить(); Стр.Номенклатура = НомТумбочка; Стр.Количество = 6; Стр.Цена = 2800;
    Стр = Реал5.Товары.Добавить(); Стр.Номенклатура = НомШкаф;     Стр.Количество = 4; Стр.Цена = 22000;
    Реал5.Записать(); Реал5.Провести();

    Сообщить("Реализации (5 шт., 3 месяца) проведены.");

    // ---- СЧЕТА (месяц 6) ----

    Сч1 = Документы.Счёт.Создать();
    Сч1.Номер = "СЧ-00001";
    Сч1.Дата = ДатаМ6; Сч1.Организация = НашаОрг; Сч1.Покупатель = ПокупательКафе;
    Сч1.Склад = СкладГлавный; Сч1.ТипЦенПродажи = ТипРозн; Сч1.СпособУчетаНДС = "ВТомЧисле";
    Сч1.СрокОплаты = ДобавитьМесяц(ДатаМ6, 1);
    Сч1.Комментарий = "Счёт на стулья и столы для зала";
    Стр = Сч1.Товары.Добавить(); Стр.Номенклатура = НомТабурет; Стр.Количество = 10;
    Стр = Сч1.Товары.Добавить(); Стр.Номенклатура = НомСтол;    Стр.Количество = 3;
    Сч1.Записать();

    Сч2 = Документы.Счёт.Создать();
    Сч2.Номер = "СЧ-00002";
    Сч2.Дата = ДатаМ6; Сч2.Организация = НашаОрг; Сч2.Покупатель = ПокупательСядь;
    Сч2.Склад = СкладГлавный; Сч2.ТипЦенПродажи = ТипРозн; Сч2.СпособУчетаНДС = "ВТомЧисле";
    Сч2.СрокОплаты = ДобавитьМесяц(ДатаМ6, 1);
    Сч2.Комментарий = "Диваны и полки — в любой позе";
    Стр = Сч2.Товары.Добавить(); Стр.Номенклатура = НомДиван; Стр.Количество = 2;
    Стр = Сч2.Товары.Добавить(); Стр.Номенклатура = НомПолка; Стр.Количество = 12;
    Сч2.Записать();

    Сч3 = Документы.Счёт.Создать();
    Сч3.Номер = "СЧ-00003";
    Сч3.Дата = ДатаМ6; Сч3.Организация = НашаОрг; Сч3.Покупатель = ПокупательГостиница;
    Сч3.Склад = СкладГлавный; Сч3.ТипЦенПродажи = ТипРозн; Сч3.СпособУчетаНДС = "ВТомЧисле";
    Сч3.СрокОплаты = ДобавитьМесяц(ДатаМ6, 1);
    Сч3.Комментарий = "Комплектация номеров — кровати, тумбы, шкаф";
    Стр = Сч3.Товары.Добавить(); Стр.Номенклатура = НомКровать;  Стр.Количество = 2;
    Стр = Сч3.Товары.Добавить(); Стр.Номенклатура = НомТумбочка; Стр.Количество = 4;
    Стр = Сч3.Товары.Добавить(); Стр.Номенклатура = НомШкаф;     Стр.Количество = 1;
    Сч3.Записать();

    Сч4 = Документы.Счёт.Создать();
    Сч4.Номер = "СЧ-00004";
    Сч4.Дата = ДатаМ6; Сч4.Организация = НашаОрг; Сч4.Покупатель = ПокупательРемонт;
    Сч4.Склад = СкладГлавный; Сч4.ТипЦенПродажи = ТипРозн; Сч4.СпособУчетаНДС = "ВТомЧисле";
    Сч4.СрокОплаты = ДобавитьМесяц(ДатаМ6, 1);
    Сч4.Комментарий = "Комоды, шкафы и стеллаж для новостройки";
    Стр = Сч4.Товары.Добавить(); Стр.Номенклатура = НомКомод;    Стр.Количество = 3;
    Стр = Сч4.Товары.Добавить(); Стр.Номенклатура = НомШкаф;     Стр.Количество = 2;
    Стр = Сч4.Товары.Добавить(); Стр.Номенклатура = НомСтеллаж;  Стр.Количество = 1;
    Сч4.Записать();

    Сообщить("Счета (4 шт.) созданы.");

    // ---- ЗАКАЗЫ ПОКУПАТЕЛЕЙ (месяц 6) ----

    ЗакПок1 = Документы.ЗаказПокупателя.Создать();
    ЗакПок1.Номер = "ЗПК-00001";
    ЗакПок1.Дата = ДатаМ6; ЗакПок1.Организация = НашаОрг; ЗакПок1.Покупатель = ПокупательКафе;
    ЗакПок1.Склад = СкладГлавный; ЗакПок1.ТипЦенПродажи = ТипРозн; ЗакПок1.СпособУчетаНДС = "ВТомЧисле";
    ЗакПок1.Основание = Сч1.Ссылка;
    ЗакПок1.Комментарий = "Заказ по счёту на стулья и столы";
    Стр = ЗакПок1.Товары.Добавить(); Стр.Номенклатура = НомТабурет; Стр.Количество = 10; Стр.Цена = 900;
    Стр = ЗакПок1.Товары.Добавить(); Стр.Номенклатура = НомСтол;    Стр.Количество = 3;  Стр.Цена = 4500;
    ЗакПок1.Записать(); ЗакПок1.Провести();

    ЗакПок2 = Документы.ЗаказПокупателя.Создать();
    ЗакПок2.Номер = "ЗПК-00002";
    ЗакПок2.Дата = ДатаМ6; ЗакПок2.Организация = НашаОрг; ЗакПок2.Покупатель = ПокупательГостиница;
    ЗакПок2.Склад = СкладГлавный; ЗакПок2.ТипЦенПродажи = ТипРозн; ЗакПок2.СпособУчетаНДС = "ВТомЧисле";
    ЗакПок2.Основание = Сч3.Ссылка;
    ЗакПок2.Комментарий = "Комплектация номеров — кровати, тумбы, шкаф";
    Стр = ЗакПок2.Товары.Добавить(); Стр.Номенклатура = НомКровать;  Стр.Количество = 2; Стр.Цена = 35000;
    Стр = ЗакПок2.Товары.Добавить(); Стр.Номенклатура = НомТумбочка; Стр.Количество = 4; Стр.Цена = 2800;
    Стр = ЗакПок2.Товары.Добавить(); Стр.Номенклатура = НомШкаф;     Стр.Количество = 1; Стр.Цена = 22000;
    ЗакПок2.Записать(); ЗакПок2.Провести();

    // Заказ-дефицит для АРМ Закупок: крупный резерв сверх остатка и товаров в пути
    // (контроль КонтролироватьОстаткиПриРезерве выключен — резервируем «в долг»).
    ЗакПок3 = Документы.ЗаказПокупателя.Создать();
    ЗакПок3.Номер = "ЗПК-00003";
    ЗакПок3.Дата = ДатаМ6; ЗакПок3.Организация = НашаОрг; ЗакПок3.Покупатель = ПокупательГостиница;
    ЗакПок3.Склад = СкладГлавный; ЗакПок3.ТипЦенПродажи = ТипРозн; ЗакПок3.СпособУчетаНДС = "ВТомЧисле";
    ЗакПок3.Комментарий = "Большой банкетный зал — столов нужно сильно больше, чем есть";
    Стр = ЗакПок3.Товары.Добавить(); Стр.Номенклатура = НомСтол; Стр.Количество = 50; Стр.Цена = 4500;
    ЗакПок3.Записать(); ЗакПок3.Провести();

    Сообщить("Заказы покупателей (3 шт.) проведены.");

    // Реализация 6 (месяц 6): Ремонт-Уют — комоды, шкафы, стеллажи
    Реал6 = Документы.РеализацияТоваров.Создать();
    Реал6.Номер = "РЕА-00006";
    Реал6.Дата = ДатаМ6; Реал6.Организация = НашаОрг; Реал6.Покупатель = ПокупательРемонт;
    Реал6.Склад = СкладГлавный; Реал6.ТипЦенПродажи = ТипРозн; Реал6.СпособУчетаНДС = "ВТомЧисле";
    Стр = Реал6.Товары.Добавить(); Стр.Номенклатура = НомКомод;    Стр.Количество = 6;  Стр.Цена = 5800;
    Стр = Реал6.Товары.Добавить(); Стр.Номенклатура = НомШкаф;     Стр.Количество = 3;  Стр.Цена = 22000;
    Стр = Реал6.Товары.Добавить(); Стр.Номенклатура = НомСтеллаж;  Стр.Количество = 3;  Стр.Цена = 6500;
    Реал6.Записать(); Реал6.Провести();

    Сообщить("Реализация 6 проведена.");

    // ---- ВОЗВРАТЫ (месяц 6) ----

    // Возврат от покупателя: Кафе возвращает 3 табурета — слишком шаткие
    ВозвПок1 = Документы.ВозвратОтПокупателя.Создать();
    ВозвПок1.Номер = "ВОЗ-00001";
    ВозвПок1.Дата = ДатаМ6; ВозвПок1.Организация = НашаОрг; ВозвПок1.Покупатель = ПокупательКафе;
    ВозвПок1.Склад = СкладГлавный; ВозвПок1.Основание = Реал1.Ссылка; ВозвПок1.СпособУчетаНДС = "ВТомЧисле";
    Стр = ВозвПок1.Товары.Добавить(); Стр.Номенклатура = НомТабурет; Стр.Количество = 3; Стр.Цена = 900;
    ВозвПок1.Записать(); ВозвПок1.Провести();

    // Возврат поставщику: Дерево — 5 бракованных табуретов (три ножки вместо четырёх)
    ВозвПост1 = Документы.ВозвратПоставщику.Создать();
    ВозвПост1.Номер = "ВПС-00001";
    ВозвПост1.Дата = ДатаМ6; ВозвПост1.Организация = НашаОрг; ВозвПост1.Поставщик = ПоставщикДерево;
    ВозвПост1.Склад = СкладГлавный; ВозвПост1.Основание = Документы.ПоступлениеТоваров.НайтиПоНомеру("ПОС-00001"); ВозвПост1.СпособУчетаНДС = "ВТомЧисле";
    Стр = ВозвПост1.Товары.Добавить(); Стр.Номенклатура = НомТабурет; Стр.Количество = 5; Стр.Цена = 500;
    ВозвПост1.Записать(); ВозвПост1.Провести();

    Сообщить("Возвраты (2 шт.) проведены.");

    // ---- ДЕНЕЖНЫЕ ДОКУМЕНТЫ (разнесены по 5 месяцам) ----

    // Месяц 2: оплата поставщикам
    РКО1 = Документы.РасходныйКассовыйОрдер.Создать();
    РКО1.Номер = "РКО-00001";
    РКО1.Дата = ДатаМ2; РКО1.Организация = НашаОрг; РКО1.Касса = КассаНал;
    РКО1.Контрагент = ПоставщикДерево; РКО1.Основание = "Гвозди сами себя не оплатят"; РКО1.Сумма = 50000;
    РКО1.Записать(); РКО1.Провести();

    БнкР1 = Документы.СписаниеСРасчётногоСчёта.Создать();
    БнкР1.Номер = "БР-00001";
    БнкР1.Дата = ДатаМ2; БнкР1.Организация = НашаОрг; БнкР1.БанковскийСчёт = СчётБанк;
    БнкР1.Контрагент = ПоставщикФанера; БнкР1.НазначениеПлатежа = "За фанеру (палас отдельно)"; БнкР1.Сумма = 80000;
    БнкР1.Записать(); БнкР1.Провести();

    // Месяц 3: оплата от Кафе, мелкий расход
    ПКО1 = Документы.ПриходныйКассовыйОрдер.Создать();
    ПКО1.Номер = "ПКО-00001";
    ПКО1.Дата = ДатаМ3; ПКО1.Организация = НашаОрг; ПКО1.Касса = КассаНал;
    ПКО1.Контрагент = ПокупательКафе; ПКО1.Основание = "Оплата за стулья (пока на них сидят)"; ПКО1.Сумма = 21000;
    ПКО1.Записать(); ПКО1.Провести();

    РКО2 = Документы.РасходныйКассовыйОрдер.Создать();
    РКО2.Номер = "РКО-00002";
    РКО2.Дата = ДатаМ3; РКО2.Организация = НашаОрг; РКО2.Касса = КассаНал;
    РКО2.Контрагент = ПоставщикКлей; РКО2.Основание = "На оперативные нужды (клей кончился)"; РКО2.Сумма = 15000;
    РКО2.Записать(); РКО2.Провести();

    // Месяц 4: поступление от Сядь-Полежи, оплата БезРучек
    БнкП1 = Документы.ПоступлениеНаРасчётныйСчёт.Создать();
    БнкП1.Номер = "БП-00001";
    БнкП1.Дата = ДатаМ4; БнкП1.Организация = НашаОрг; БнкП1.БанковскийСчёт = СчётБанк;
    БнкП1.Контрагент = ПокупательСядь; БнкП1.НазначениеПлатежа = "За диваны и полки по счёту"; БнкП1.Сумма = 60000;
    БнкП1.Записать(); БнкП1.Провести();

    БнкР2 = Документы.СписаниеСРасчётногоСчёта.Создать();
    БнкР2.Номер = "БР-00002";
    БнкР2.Дата = ДатаМ4; БнкР2.Организация = НашаОрг; БнкР2.БанковскийСчёт = СчётБанк;
    БнкР2.Контрагент = ПоставщикБезРучек; БнкР2.НазначениеПлатежа = "За шкафы и тумбочки (ручки обещали докрутить)"; БнкР2.Сумма = 120000;
    БнкР2.Записать(); БнкР2.Провести();

    // Месяц 5: Детсад, Гостиница, мелкий расход
    ПКО2 = Документы.ПриходныйКассовыйОрдер.Создать();
    ПКО2.Номер = "ПКО-00002";
    ПКО2.Дата = ДатаМ5; ПКО2.Организация = НашаОрг; ПКО2.Касса = КассаНал;
    ПКО2.Контрагент = ПокупательДетсад; ПКО2.Основание = "Спонсорский взнос на пуфики"; ПКО2.Сумма = 30000;
    ПКО2.Записать(); ПКО2.Провести();

    БнкП2 = Документы.ПоступлениеНаРасчётныйСчёт.Создать();
    БнкП2.Номер = "БП-00002";
    БнкП2.Дата = ДатаМ5; БнкП2.Организация = НашаОрг; БнкП2.БанковскийСчёт = СчётБанк;
    БнкП2.Контрагент = ПокупательГостиница; БнкП2.НазначениеПлатежа = "За кровати, тумбочки и шкаф"; БнкП2.Сумма = 150000;
    БнкП2.Записать(); БнкП2.Провести();

    РКО3 = Документы.РасходныйКассовыйОрдер.Создать();
    РКО3.Номер = "РКО-00003";
    РКО3.Дата = ДатаМ5; РКО3.Организация = НашаОрг; РКО3.Касса = КассаНал;
    РКО3.Контрагент = ПоставщикКлей; РКО3.Основание = "На оперативные нужды (ещё клей)"; РКО3.Сумма = 10000;
    РКО3.Записать(); РКО3.Провести();

    // Месяц 6: Ресторан, оплата Гвоздю
    ПКО3 = Документы.ПриходныйКассовыйОрдер.Создать();
    ПКО3.Номер = "ПКО-00003";
    ПКО3.Дата = ДатаМ6; ПКО3.Организация = НашаОрг; ПКО3.Касса = КассаНал;
    ПКО3.Контрагент = ПокупательРесторан; ПКО3.Основание = "Оплата за кресла и столы"; ПКО3.Сумма = 50000;
    ПКО3.Записать(); ПКО3.Провести();

    БнкР3 = Документы.СписаниеСРасчётногоСчёта.Создать();
    БнкР3.Номер = "БР-00003";
    БнкР3.Дата = ДатаМ6; БнкР3.Организация = НашаОрг; БнкР3.БанковскийСчёт = СчётБанк;
    БнкР3.Контрагент = ПоставщикГвоздь; БнкР3.НазначениеПлатежа = "За стеллажи и комоды"; БнкР3.Сумма = 100000;
    БнкР3.Записать(); БнкР3.Провести();

    Сообщить("Денежные документы (10 шт., 5 месяцев) проведены.");

    // ---- СПИСАНИЯ (месяц 6) ----

    Спис1 = Документы.СписаниеТоваров.Создать();
    Спис1.Номер = "СПС-00001";
    Спис1.Дата = ДатаМ6; Спис1.Организация = НашаОрг; Спис1.Склад = СкладГлавный;
    Спис1.Причина = "Кот точил когти, товар утратил товарный вид";
    Стр = Спис1.Товары.Добавить(); Стр.Номенклатура = НомПуф; Стр.Количество = 5; Стр.Цена = 400;
    Спис1.Записать(); Спис1.Провести();

    Спис2 = Документы.СписаниеТоваров.Создать();
    Спис2.Номер = "СПС-00002";
    Спис2.Дата = ДатаМ6; Спис2.Организация = НашаОрг; Спис2.Склад = СкладГлавный;
    Спис2.Причина = "Разбиты при разгрузке (водитель перепутал стул с пнём)";
    Стр = Спис2.Товары.Добавить(); Стр.Номенклатура = НомТумбочка; Стр.Количество = 2; Стр.Цена = 1500;
    Спис2.Записать(); Спис2.Провести();

    Сообщить("Списания (2 шт.) проведены.");

    // ---- РАЗБОРКА (месяц 6) ----

    Рзб = Документы.РазборкаТоваров.Создать();
    Рзб.Номер = "РЗБ-00001";
    Рзб.Дата = ДатаМ6; Рзб.Организация = НашаОрг; Рзб.Склад = СкладГлавный;
    Рзб.Комментарий = "Диван распотрошён на запчасти — пуфики и полки нужнее";
    Стр = Рзб.Расход.Добавить(); Стр.Номенклатура = НомДиван;  Стр.Количество = 1; Стр.Себестоимость = 8000;
    Стр = Рзб.Приход.Добавить(); Стр.Номенклатура = НомПуф;    Стр.Количество = 3; Стр.Себестоимость = 2000;
    Стр = Рзб.Приход.Добавить(); Стр.Номенклатура = НомПолка;  Стр.Количество = 2; Стр.Себестоимость = 1000;
    Рзб.Записать(); Рзб.Провести();

    Сообщить("Разборки (1 шт.) проведены.");

    Сообщить("Все документы созданы и проведены.");
  Иначе
    Сообщить("Документы уже есть, очистка выключена — создание пропущено.");
  КонецЕсли;

  // ============ ИТОГОВАЯ СВОДКА ============

  ЗК = Новый Запрос; ЗК.Текст = "ВЫБРАТЬ Наименование ИЗ Контрагент";
  КолК = 0; Для Каждого Д Из ЗК.Выполнить() Цикл КолК = КолК + 1; КонецЦикла;

  ЗН = Новый Запрос; ЗН.Текст = "ВЫБРАТЬ Наименование ИЗ Номенклатура";
  КолН = 0; Для Каждого Д Из ЗН.Выполнить() Цикл КолН = КолН + 1; КонецЦикла;

  ЗП = Новый Запрос; ЗП.Текст = "ВЫБРАТЬ Номер ИЗ Документ.ПоступлениеТоваров";
  КолП = 0; Для Каждого Д Из ЗП.Выполнить() Цикл КолП = КолП + 1; КонецЦикла;

  ЗРеал = Новый Запрос; ЗРеал.Текст = "ВЫБРАТЬ Номер ИЗ Документ.РеализацияТоваров";
  КолР = 0; Для Каждого Д Из ЗРеал.Выполнить() Цикл КолР = КолР + 1; КонецЦикла;

  ЗСч = Новый Запрос; ЗСч.Текст = "ВЫБРАТЬ Номер ИЗ Документ.Счёт";
  КолСч = 0; Для Каждого Д Из ЗСч.Выполнить() Цикл КолСч = КолСч + 1; КонецЦикла;

  ЗВПок = Новый Запрос; ЗВПок.Текст = "ВЫБРАТЬ Номер ИЗ Документ.ВозвратОтПокупателя";
  КолВПок = 0; Для Каждого Д Из ЗВПок.Выполнить() Цикл КолВПок = КолВПок + 1; КонецЦикла;

  ЗВПост = Новый Запрос; ЗВПост.Текст = "ВЫБРАТЬ Номер ИЗ Документ.ВозвратПоставщику";
  КолВПост = 0; Для Каждого Д Из ЗВПост.Выполнить() Цикл КолВПост = КолВПост + 1; КонецЦикла;

  ЗЗакПок = Новый Запрос; ЗЗакПок.Текст = "ВЫБРАТЬ Номер ИЗ Документ.ЗаказПокупателя";
  КолЗакПок = 0; Для Каждого Д Из ЗЗакПок.Выполнить() Цикл КолЗакПок = КолЗакПок + 1; КонецЦикла;

  ЗЗакПост = Новый Запрос; ЗЗакПост.Текст = "ВЫБРАТЬ Номер ИЗ Документ.ЗаказПоставщику";
  КолЗакПост = 0; Для Каждого Д Из ЗЗакПост.Выполнить() Цикл КолЗакПост = КолЗакПост + 1; КонецЦикла;

  ЗСбр = Новый Запрос; ЗСбр.Текст = "ВЫБРАТЬ Номер ИЗ Документ.СборкаТоваров";
  КолСбр = 0; Для Каждого Д Из ЗСбр.Выполнить() Цикл КолСбр = КолСбр + 1; КонецЦикла;

  ЗРзб = Новый Запрос; ЗРзб.Текст = "ВЫБРАТЬ Номер ИЗ Документ.РазборкаТоваров";
  КолРзб = 0; Для Каждого Д Из ЗРзб.Выполнить() Цикл КолРзб = КолРзб + 1; КонецЦикла;

  ЗУЦ = Новый Запрос; ЗУЦ.Текст = "ВЫБРАТЬ Номер ИЗ Документ.УстановкаЦен";
  КолУЦ = 0; Для Каждого Д Из ЗУЦ.Выполнить() Цикл КолУЦ = КолУЦ + 1; КонецЦикла;

  ЗОст = Новый Запрос;
  ЗОст.Текст = "ВЫБРАТЬ Номенклатура ИЗ РегистрНакопления.ОстаткиТоваров.Остатки() ГДЕ КоличествоОстаток > 0";
  КолОст = 0; Для Каждого Д Из ЗОст.Выполнить() Цикл КолОст = КолОст + 1; КонецЦикла;

  Сообщить("Сводка: контрагентов " + Строка(КолК) + ", номенклатуры " + Строка(КолН)
    + ", заказов поставщикам " + Строка(КолЗакПост) + ", поступлений " + Строка(КолП)
    + ", заказов покупателей " + Строка(КолЗакПок) + ", реализаций " + Строка(КолР)
    + ", возвратов от покупателей " + Строка(КолВПок)
    + ", возвратов поставщикам " + Строка(КолВПост)
    + ", счетов " + Строка(КолСч)
    + ", сборок " + Строка(КолСбр) + ", разборок " + Строка(КолРзб)
    + ", установок цен " + Строка(КолУЦ)
    + ", строк остатков " + Строка(КолОст) + ".");
КонецПроцедуры
