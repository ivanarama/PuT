"""Post partial supply, receipts and a closure and verify the dates offered to a customer."""
import argparse
from decimal import Decimal
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--onebase", required=True)
    parser.add_argument("--postgres", action="store_true", help="Use a disposable PostgreSQL database from DATABASE_URL")
    args = parser.parse_args()
    if args.postgres and not os.environ.get("DATABASE_URL"):
        parser.error("--postgres requires DATABASE_URL")
    executable = str(Path(args.onebase).resolve())
    with tempfile.TemporaryDirectory(prefix="put-order-promises-") as tmp:
        project = Path(tmp)
        for kind in ("catalogs", "config", "constants", "documents", "enums", "forms", "inforegs",
                     "journals", "pages", "printforms", "processors", "registers", "reports", "roles",
                     "scheduled", "src", "subsystems", "widgets"):
            shutil.copytree(ROOT / kind, project / kind)
        (project / "processors/срокипоставоктест.yaml").write_text("name: СрокиПоставокТест\n", encoding="utf8")
        shutil.copyfile(ROOT / "tests/fixtures/order_promises.os", project / "src/срокипоставоктест.proc.os")
        target = [] if args.postgres else ["--sqlite", str(project / "order-promises.db")]

        def cli(*command):
            return subprocess.check_output(
                [executable, "--no-gui", *command, "--project", str(project), *target],
                encoding="utf8", timeout=120,
            )

        cli("migrate")
        cli("procrun", "--proc", "ЗаполнитьТестовуюБазу")
        cli("procrun", "--proc", "СрокиПоставокТест")
        keys, = json.loads(cli("query", "--json", 'ВЫБРАТЬ З.Ссылка КАК ЗаказИД, '
                               'З.Склад.Ссылка КАК СкладИД, З.Организация.Ссылка КАК ОргИД '
                               'ИЗ Документ.ЗаказПокупателя КАК З ГДЕ З.Комментарий = "order-promise-test"'))["rows"]
        # as-of day, incoming units still open, units received under the order, earliest full shipment
        expected = [
            (1, 10, 0, 14),  # last necessary lot is due on the 14th
            (2, 7, 3, 12),   # delivery of line 2 advances the promise to the 12th
            (3, 6, 3, None),  # cancellation leaves one unit without a confirmed date
            (4, 7, 3, 18),   # a replacement purchase covers the shortage
            (5, 6, 4, 18),   # receipt without a line number cannot be counted twice
            (11, 6, 4, None),  # the undelivered commitment of the 10th needs reconfirmation
            (21, 6, 4, 21),  # physical stock now covers all ten reserved units
        ]
        for day, in_transit, received, promise in expected:
            params = {"НаДату": f"2031-07-{day:02d}", "ЗаказПокупателя": keys["заказид"],
                      "Склад": keys["складид"], "Организация": keys["оргид"]}
            report = json.loads(cli("report", "explain", "АнализЗаказовПокупателей", "--sample", "10",
                                    "--json", "--params", json.dumps(params, ensure_ascii=False)))
            assert not report.get("error"), report["error"]
            row, = report["rows"]
            quantities = tuple(Decimal(str(row[key])) for key in ("резервостаток", "впути", "поступило"))
            assert quantities == (10, in_transit, received), row
            actual = (row["возможнаядатаотгрузки"] or "")[:10]
            assert actual == (f"2031-07-{promise:02d}" if promise else ""), (day, actual, row)
            print(params["НаДату"], in_transit, received, actual or "unconfirmed")


if __name__ == "__main__":
    main()
