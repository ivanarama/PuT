"""Exercise ABC cutoffs, returns, date/organization filters and equal product names."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import uuid

PROJECT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--onebase", required=True)
    args = parser.parse_args()
    binary = str(Path(args.onebase).resolve())
    with tempfile.TemporaryDirectory(prefix="put-abc-") as folder:
        db = Path(folder) / "abc.db"
        common = ["--project", str(PROJECT), "--sqlite", str(db)]
        subprocess.run([binary, "--no-gui", "migrate", *common], check=True, stdout=subprocess.DEVNULL)
        org, other = str(uuid.uuid4()), str(uuid.uuid4())
        products = [str(uuid.UUID(int=i)) for i in range(1, 7)]
        with closing(sqlite3.connect(db)) as conn:
            for key in (org, other):
                conn.execute("INSERT INTO организация (id,наименование) VALUES (?,?)", (key, key))
            for key, name in zip(products, ["Одинаковый", "Одинаковый", "Третий", "Возврат", "Ноль", "Равный"]):
                conn.execute("INSERT INTO номенклатура (id,наименование) VALUES (?,?)", (key, name))

            def movement(product, revenue, cost=0, direction="Приход", owner=org, day="2026-07-01"):
                conn.execute(
                    "INSERT INTO рег_валоваяприбыль (id, recorder, recorder_type, line_number, period, "
                    "вид_движения, организация_id, номенклатура_id, выручка, себестоимость, суммасндс, себестоимостьсндс) "
                    "VALUES (?,?,?,1,?,?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), str(uuid.uuid4()), "РеализацияТоваров", day+" 18:30:00",
                     direction, owner, products[product], str(revenue), str(cost), str(2*revenue), str(2*cost)),
                )
            movement(0, 100, 10)
            movement(0, 12, 2, "Расход")  # net profit 80 after a partial return
            movement(1, 15)
            movement(2, 5)
            movement(3, 5, direction="Расход")
            movement(4, 8, 8)
            movement(0, 200, owner=other)
            movement(5, 80, day="2026-07-02")
            movement(2, 3, direction="Расход", day="2026-07-03")
            conn.commit()

        def report(**changes):
            params = {"ДатаНачала":"2026-07-01", "ДатаОкончания":"2026-07-01",
                      "Организация": org, "СУчетомНДС":False, **changes}
            out = subprocess.check_output([binary, "--no-gui", "report", "explain", "ABCАнализПродаж",
                                          *common, "--sample", "100", "--json", "--params",
                                          json.dumps(params, ensure_ascii=False)], encoding="utf-8")
            result = json.loads(out)
            assert not result.get("error"), result.get("error")
            return result.get("rows", [])

        rows = report()
        assert [r["валоваяприбыль"] for r in rows] == [80, 15, 5, 0, -5], rows
        assert [r["номенклатура"] for r in rows[:2]] == ["Одинаковый"] * 2
        assert [r["классabc"] for r in rows] == list("ABCCC")
        assert [r["накопленнаядоляпроцент"] for r in rows] == [80, 95, 100, 100, 100]
        assert [r["классabc"] for r in report(ПорогА=80.1, ПорогБ=99)] == list("AABCC")
        assert [r["валоваяприбыль"] for r in report(СУчетомНДС=True)] == [160, 30, 10, 0, -10]
        assert report(Организация=other)[0]["доляпроцент"] == 100
        tied = report(ДатаОкончания="2026-07-02")
        assert [r["номенклатура"] for r in tied[:2]] == ["Одинаковый", "Равный"]
        invalid = report(ПорогА=95, ПорогБ=90)
        assert len(invalid) == 1 and "границ" in invalid[0]["классabc"]
        losses = report(ДатаНачала="2026-07-03", ДатаОкончания="2026-07-03")
        assert losses[0]["классabc"] == "C" and losses[0]["накопленнаядоляпроцент"] == 0
        assert not report(ДатаНачала="2030-01-01", ДатаОкончания="2030-02-01")
        print("ABC: returns, A/B/C at 80/95 and custom thresholds, ties, empty period, VAT and organization verified")


if __name__ == "__main__":
    main()
