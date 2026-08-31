#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор технической автодокументации конфигурации OneBase (DOCS.md).
Сканирует структуру метаданных (YAML) и формирует полный каталог объектов,
полей, связей (based_on), регистров и логики проведения.
"""

import os
import glob
import yaml
import sys

def get_str(val, lang="ru"):
    if isinstance(val, dict):
        return val.get(lang, val.get("ru", val.get("en", str(val))))
    return str(val) if val is not None else ""

def generate_docs(repo_root, output_file):
    lines = []
    
    # 1. App Info
    app_yaml_path = os.path.join(repo_root, "config", "app.yaml")
    app_info = {}
    if os.path.exists(app_yaml_path):
        with open(app_yaml_path, "r", encoding="utf-8") as f:
            app_info = yaml.safe_load(f) or {}

    app_name = app_info.get("name", "OneBase Application")
    app_title = get_str(app_info.get("title", app_name))
    app_version = app_info.get("version", "1.0.0")

    lines.append(f"# {app_title} ({app_name}) — Автодокументация")
    lines.append("")
    lines.append(f"> Автоматически сгенерированная документация структуры метаданных конфигурации.")
    lines.append(f"> Версия конфигурации: **v{app_version}** | Платформа: **OneBase**")
    lines.append("")
    lines.append("## Содержание")
    lines.append("- [Подсистемы](#подсистемы)")
    lines.append("- [Справочники](#справочники)")
    lines.append("- [Документы](#документы)")
    lines.append("- [Регистры накопления](#регистры-накопления)")
    lines.append("- [Регистры сведений](#регистры-сведений)")
    lines.append("- [АРМы и Обработки](#армы-и-обработки)")
    lines.append("- [Отчёты](#отчёты)")
    lines.append("- [Перечисления и Константы](#перечисления-и-константы)")
    lines.append("- [Роли и безопасность](#роли-и-безопасность)")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 2. Subsystems
    subsys_files = sorted(glob.glob(os.path.join(repo_root, "subsystems", "*.yaml")))
    lines.append("## Подсистемы")
    lines.append("")
    lines.append("| Подсистема | Заголовок | Описание / Объекты |")
    lines.append("|---|---|---|")
    for sf in subsys_files:
        with open(sf, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        s_name = data.get("name", os.path.splitext(os.path.basename(sf))[0])
        s_title = get_str(data.get("title", s_name))
        s_items = data.get("items", [])
        items_str = ", ".join(s_items) if s_items else "—"
        lines.append(f"| **{s_name}** | {s_title} | {items_str} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 3. Catalogs
    cat_files = sorted(glob.glob(os.path.join(repo_root, "catalogs", "*.yaml")))
    lines.append("## Справочники")
    lines.append("")
    for cf in cat_files:
        with open(cf, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        c_name = data.get("name", os.path.splitext(os.path.basename(cf))[0])
        c_title = get_str(data.get("title", c_name))
        hier = " (иерархический)" if data.get("hierarchical") else ""
        lines.append(f"### Справочник `{c_name}` ({c_title}){hier}")
        fields = data.get("fields", [])
        if fields:
            lines.append("| Реквизит | Тип | Заголовок |")
            lines.append("|---|---|---|")
            for fld in fields:
                fname = fld.get("name", "")
                ftype = fld.get("type", "string")
                ftitle = get_str(fld.get("title", fname))
                lines.append(f"| `{fname}` | `{ftype}` | {ftitle} |")
            lines.append("")
        else:
            lines.append("*Стандартные реквизиты (Код, Наименование)*\n")
    lines.append("---")
    lines.append("")

    # 4. Documents
    doc_files = sorted(glob.glob(os.path.join(repo_root, "documents", "*.yaml")))
    lines.append("## Документы")
    lines.append("")
    for df in doc_files:
        with open(df, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        d_name = data.get("name", os.path.splitext(os.path.basename(df))[0])
        d_title = get_str(data.get("title", d_name))
        posting = "Да (порождает движения)" if data.get("posting") else "Нет (непроводимый)"
        based_on = data.get("based_on", [])
        based_str = ", ".join([f"`{b}`" for b in based_on]) if based_on else "—"

        lines.append(f"### Документ `{d_name}` — {d_title}")
        lines.append(f"- **Проведение:** {posting}")
        lines.append(f"- **Ввод на основании:** {based_str}")
        lines.append("")

        # Header fields
        fields = data.get("fields", [])
        if fields:
            lines.append("#### Реквизиты шапки")
            lines.append("| Реквизит | Тип | Заголовок |")
            lines.append("|---|---|---|")
            for fld in fields:
                fname = fld.get("name", "")
                ftype = fld.get("type", "string")
                ftitle = get_str(fld.get("title", fname))
                lines.append(f"| `{fname}` | `{ftype}` | {ftitle} |")
            lines.append("")

        # Table parts
        tparts = data.get("tableparts", [])
        for tp in tparts:
            tp_name = tp.get("name", "")
            tp_title = get_str(tp.get("title", tp_name))
            lines.append(f"#### Табличная часть `{tp_name}` ({tp_title})")
            tp_fields = tp.get("fields", [])
            lines.append("| Поле | Тип | Заголовок |")
            lines.append("|---|---|---|")
            for fld in tp_fields:
                fname = fld.get("name", "")
                ftype = fld.get("type", "string")
                ftitle = get_str(fld.get("title", fname))
                lines.append(f"| `{fname}` | `{ftype}` | {ftitle} |")
            lines.append("")
        lines.append("")
    lines.append("---")
    lines.append("")

    # 5. Accumulation Registers
    reg_files = sorted(glob.glob(os.path.join(repo_root, "registers", "*.yaml")))
    lines.append("## Регистры накопления")
    lines.append("")
    for rf in reg_files:
        with open(rf, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        r_name = data.get("name", os.path.splitext(os.path.basename(rf))[0])
        r_title = get_str(data.get("title", r_name))
        r_type = "Остатки и обороты" if data.get("type") == "turnovers" else "Остаточный (баланс)"

        lines.append(f"### Регистр накопления `{r_name}` ({r_title})")
        lines.append(f"- **Вид регистра:** {r_type}")
        lines.append("")

        dims = data.get("dimensions", [])
        if dims:
            lines.append("#### Измерения")
            lines.append("| Измерение | Тип | Заголовок |")
            lines.append("|---|---|---|")
            for d in dims:
                dname = d.get("name", "")
                dtype = d.get("type", "string")
                dtitle = get_str(d.get("title", dname))
                lines.append(f"| `{dname}` | `{dtype}` | {dtitle} |")
            lines.append("")

        res = data.get("resources", [])
        if res:
            lines.append("#### Ресурсы")
            lines.append("| Ресурс | Тип | Заголовок |")
            lines.append("|---|---|---|")
            for r in res:
                rname = r.get("name", "")
                rtype = r.get("type", "number")
                rtitle = get_str(r.get("title", rname))
                lines.append(f"| `{rname}` | `{rtype}` | {rtitle} |")
            lines.append("")

        attrs = data.get("attributes", [])
        if attrs:
            lines.append("#### Реквизиты")
            lines.append("| Реквизит | Тип | Заголовок |")
            lines.append("|---|---|---|")
            for a in attrs:
                aname = a.get("name", "")
                atype = a.get("type", "string")
                atitle = get_str(a.get("title", aname))
                lines.append(f"| `{aname}` | `{atype}` | {atitle} |")
            lines.append("")
    lines.append("---")
    lines.append("")

    # 6. Information Registers
    inforeg_files = sorted(glob.glob(os.path.join(repo_root, "inforegs", "*.yaml")))
    lines.append("## Регистры сведений")
    lines.append("")
    for irf in inforeg_files:
        with open(irf, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        ir_name = data.get("name", os.path.splitext(os.path.basename(irf))[0])
        ir_title = get_str(data.get("title", ir_name))
        periodic = data.get("periodicity", "Непериодический")

        lines.append(f"### Регистр сведений `{ir_name}` ({ir_title})")
        lines.append(f"- **Периодичность:** {periodic}")
        lines.append("")

        dims = data.get("dimensions", [])
        if dims:
            lines.append("#### Измерения")
            lines.append("| Измерение | Тип |")
            lines.append("|---|---|")
            for d in dims:
                lines.append(f"| `{d.get('name')}` | `{d.get('type')}` |")
            lines.append("")

        res = data.get("resources", [])
        if res:
            lines.append("#### Ресурсы")
            lines.append("| Ресурс | Тип |")
            lines.append("|---|---|")
            for r in res:
                lines.append(f"| `{r.get('name')}` | `{r.get('type')}` |")
            lines.append("")
    lines.append("---")
    lines.append("")

    # 7. Processors & ARMs
    proc_files = sorted(glob.glob(os.path.join(repo_root, "processors", "*.yaml")))
    lines.append("## АРМы и Обработки")
    lines.append("")
    for pf in proc_files:
        with open(pf, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        p_name = data.get("name", os.path.splitext(os.path.basename(pf))[0])
        p_title = get_str(data.get("title", p_name))

        lines.append(f"### `{p_name}` — {p_title}")
        params = data.get("params", [])
        if params:
            lines.append("Параметры:")
            for p in params:
                lines.append(f"- `{p.get('name')}` ({get_str(p.get('label', ''))}): `{p.get('type')}`")
        tparts = data.get("table_parts", [])
        if tparts:
            lines.append("Табличные части:")
            for tp in tparts:
                lines.append(f"- **{tp.get('name')}** ({get_str(tp.get('title', ''))})")
        lines.append("")
    lines.append("---")
    lines.append("")

    # 8. Reports
    rep_files = sorted(glob.glob(os.path.join(repo_root, "reports", "*.yaml")))
    lines.append("## Отчёты")
    lines.append("")
    lines.append("| Отчёт | Название | Подсистема |")
    lines.append("|---|---|---|")
    for rf in rep_files:
        with open(rf, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        r_name = data.get("name", os.path.splitext(os.path.basename(rf))[0])
        r_title = get_str(data.get("title", r_name))
        r_sub = data.get("subsystem", "—")
        lines.append(f"| `{r_name}` | {r_title} | {r_sub} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 9. Enums & Constants
    enum_files = sorted(glob.glob(os.path.join(repo_root, "enums", "*.yaml")))
    lines.append("## Перечисления и Константы")
    lines.append("")
    lines.append("### Перечисления")
    for ef in enum_files:
        with open(ef, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        e_name = data.get("name", os.path.splitext(os.path.basename(ef))[0])
        vals = [v.get("name", "") if isinstance(v, dict) else str(v) for v in data.get("values", [])]
        lines.append(f"- **`{e_name}`**: {', '.join(vals)}")
    lines.append("")

    const_files = sorted(glob.glob(os.path.join(repo_root, "constants", "*.yaml")))
    lines.append("### Константы")
    for cnf in const_files:
        with open(cnf, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        lines.append(f"- **`{data.get('name')}`** (`{data.get('type')}`): {get_str(data.get('title', ''))}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 10. Roles
    role_files = sorted(glob.glob(os.path.join(repo_root, "roles", "*.yaml")))
    lines.append("## Роли и безопасность")
    lines.append("")
    for rof in role_files:
        with open(rof, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        ro_name = data.get("name", os.path.splitext(os.path.basename(rof))[0])
        ro_title = get_str(data.get("title", ro_name))
        lines.append(f"- **`{ro_name}`** ({ro_title})")
    lines.append("")

    content = "\n".join(lines)
    with open(output_file, "w", encoding="utf-8") as out:
        out.write(content)
    print(f"Документация успешно сгенерирована в {output_file} ({len(lines)} строк).")

if __name__ == "__main__":
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    out_file = os.path.join(repo_root, "DOCS.md")
    generate_docs(repo_root, out_file)
