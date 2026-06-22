#!/usr/bin/env python3
# Одноразовая сшивка демо-картинок в src/заполнитьтестовуюбазу.proc.os:
#  1) вставляет блок Base64-переменных (из scripts/demo_images/_imgvars.os.txt)
#     после строки "// --- Номенклатура ---";
#  2) перед каждым Зап.Записать() внутри блока создания Номенклатуры добавляет
#     Зап.ОсновноеИзображение = СохранитьКартинку(Фото<...>); (сопоставление по Артикулу).
# Идемпотентен: повторный запуск не дублирует (пропускает уже размеченные блоки).

import re, sys, io

OS = "src/заполнитьтестовуюбазу.proc.os"
VARS = "scripts/demo_images/_imgvars.os.txt"

ART_TO_VAR = {
    "TAB-2000": "ФотоТабурет",
    "KRS-BOSS": "ФотоКресло",
    "STL-WTF":  "ФотоСтол",
    "DIV-SOFT": "ФотоДиван",
    "PLK-PIZA": "ФотоПолка",
    "PUF-CUBE": "ФотоПуф",
    "SHK-SECR": "ФотоШкаф",
    "KMD-HEST": "ФотоКомод",
    "TMB-NITE": "ФотоТумбочка",
    "KRV-SLEP": "ФотоКровать",
    "STL-BOOK": "ФотоСтеллаж",
    "BNK-GILT": "ФотоБанкетка",
    "NAB-TBL":  "ФотоНабор",
}

with io.open(VARS, encoding="utf-8") as f:
    vars_block = f.read().rstrip("\n")

with io.open(OS, encoding="utf-8") as f:
    lines = f.readlines()

out = []
inserted_vars = False
nom_block = False      # внутри блока "Зап = Справочники.Номенклатура.Создать();"
cur_art = None
img_count = 0

i = 0
while i < len(lines):
    line = lines[i]
    stripped = line.rstrip("\n")

    # 1) блок переменных — один раз после маркера Номенклатура
    if not inserted_vars and "// --- Номенклатура ---" in stripped:
        out.append(line)
        out.append("\n")
        out.append(vars_block + "\n")
        out.append("\n")
        inserted_vars = True
        i += 1
        continue

    # отслеживание блоков создания Номенклатуры
    if "Зап = Справочники.Номенклатура.Создать()" in stripped:
        nom_block = True
        cur_art = None
    elif nom_block and re.match(r"\s*КонецЕсли;", stripped):
        nom_block = False
        cur_art = None

    # запоминаем артикул внутри блока
    if nom_block:
        m = re.search(r'Зап\.Артикул\s*=\s*"([^"]+)"', stripped)
        if m:
            cur_art = m.group(1)

    # вставка картинки перед Записать() — с защитой от повтора
    if nom_block and re.match(r"\s*Зап\.Записать\(\);", stripped) and cur_art in ART_TO_VAR:
        if "ОсновноеИзображение" not in "".join(lines[i-1:i]):  # не дублировать
            indent = re.match(r"(\s*)", stripped).group(1)
            var = ART_TO_VAR[cur_art]
            out.append(f'{indent}Зап.ОсновноеИзображение = СохранитьКартинку({var});\n')
            img_count += 1

    out.append(line)
    i += 1

if not inserted_vars:
    sys.exit("ERROR: маркер '// --- Номенклатура ---' не найден — блок переменных не вставлен")
if img_count != 13:
    sys.exit(f"ERROR: ожидалось 13 вставок картинок, сделано {img_count}")

with io.open(OS, "w", encoding="utf-8", newline="\n") as f:
    f.writelines(out)

print(f"OK: vars block inserted={inserted_vars}, image lines inserted={img_count}")
