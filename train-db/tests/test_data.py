"""data/trains.sqlite と app/index.html の整合性テスト。  python3 -m unittest discover -s tests"""
import json, os, re, sqlite3, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "trains.sqlite")
TIME = re.compile(r"^\d{2}:\d{2}$")

class TrainDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = sqlite3.connect(DB)
        cls.db.row_factory = sqlite3.Row
        cls.rows = [dict(r) for r in cls.db.execute("SELECT * FROM trains")]

    def test_not_empty_and_all_combinations_present(self):
        for day in ("weekday", "holiday"):
            for d in ("O>S", "S>O", "H>O"):
                for g in ("山手線", "その他"):
                    n = sum(1 for r in self.rows if (r["day_type"], r["direction"], r["group_name"]) == (day, d, g))
                    self.assertGreater(n, 80, (day, d, g))

    def test_time_format_and_order(self):
        for r in self.rows:
            if r["direction"] == "H>O":        # 渋谷→大崎
                self.assertRegex(r["shibuya_time"], TIME, r["id"])
                self.assertIsNone(r["shinjuku_time"], r["id"])
                if r["osaki_passing"]:
                    self.assertIsNone(r["osaki_time"], r["id"])
                else:
                    self.assertRegex(r["osaki_time"], TIME, r["id"])
                    ride = r["osaki_min"] - r["shibuya_min"]
                    self.assertTrue(3 <= ride <= 15, (r["id"], ride))
                continue
            self.assertRegex(r["shinjuku_time"], TIME, r["id"])
            if r["osaki_passing"]:
                self.assertIsNone(r["osaki_time"], r["id"])
                continue
            self.assertRegex(r["osaki_time"], TIME, r["id"])
            ride = (r["shinjuku_min"] - r["osaki_min"]) if r["direction"] == "O>S" else (r["osaki_min"] - r["shinjuku_min"])
            self.assertTrue(8 <= ride <= 25, (r["id"], ride))

    def test_no_duplicate_trains(self):
        keys = [(r["day_type"], r["direction"], r["train_number"], r["osaki_time"], r["shinjuku_time"], r["shibuya_time"]) for r in self.rows]
        self.assertEqual(len(keys), len(set(keys)))

    def test_yamanote_daytime_headway(self):
        for day in ("weekday", "holiday"):
            for d in ("O>S", "S>O", "H>O"):
                ks = sorted(r["sort_min"] for r in self.rows
                            if (r["day_type"], r["direction"], r["group_name"]) == (day, d, "山手線"))
                day_ks = [k for k in ks if 600 <= k <= 900]
                gaps = [b - a for a, b in zip(day_ks, day_ks[1:])]
                self.assertLessEqual(max(gaps), 6, (day, d, max(gaps)))
                self.assertGreaterEqual(len(day_ks), 55)  # 5時間 / 約5分

    def test_yamanote_is_only_in_yamanote_group(self):
        for r in self.rows:
            self.assertEqual(r["group_name"] == "山手線", r["line"] == "山手線", r["id"])

    def test_known_trains(self):
        # 山手線の始発(平日・大崎発 外回り)と最終が存在する
        yo = sorted(r["sort_min"] for r in self.rows if (r["day_type"], r["direction"], r["group_name"]) == ("weekday", "O>S", "山手線"))
        self.assertLess(yo[0], 5 * 60)
        self.assertGreater(yo[-1], 24 * 60)

    def test_shibuya_to_osaki_matches_shinjuku_to_osaki(self):
        # 渋谷始発がないので、新宿→大崎の全列車が渋谷→大崎にも現れる(列車番号が一致)
        for day in ("weekday", "holiday"):
            s_o = {r["train_number"] for r in self.rows if (r["day_type"], r["direction"]) == (day, "S>O")}
            h_o = {r["train_number"] for r in self.rows if (r["day_type"], r["direction"]) == (day, "H>O")}
            self.assertEqual(s_o, h_o, day)

    def test_sort_min_is_departure_of_the_first_station(self):
        # 一覧の基準時刻: 大崎→新宿=大崎発、新宿→大崎=新宿発、渋谷→大崎=渋谷発
        for r in self.rows:
            if r["direction"] == "S>O":
                self.assertEqual(r["sort_min"], r["shinjuku_min"], r["id"])
            elif r["direction"] == "H>O":
                self.assertEqual(r["sort_min"], r["shibuya_min"], r["id"])
            elif not r["osaki_passing"]:
                self.assertEqual(r["sort_min"], r["osaki_min"], r["id"])

    def test_rinkai_train_leaving_shinjuku_at_1706(self):
        # 公式: 平日 新宿17:06発 快速 新木場行(1620F) 渋谷17:10 大崎17:21発
        q = {(r["direction"], r["train_number"]): r for r in self.rows if r["day_type"] == "weekday"}
        s = q[("S>O", "1620F")]
        self.assertEqual((s["shinjuku_dep"], s["shibuya_dep"], s["osaki_dep"], s["sort_min"]), ("17:06", "17:10", "17:21", 17 * 60 + 6))
        self.assertEqual(q[("H>O", "1620F")]["sort_min"], 17 * 60 + 10)

    def test_html_embeds_same_number_of_trains(self):
        html = open(os.path.join(ROOT, "app", "index.html"), encoding="utf-8").read()
        m = re.search(r"const DATA = (\{.*?\});\nconst T =", html, re.S)
        self.assertIsNotNone(m)
        self.assertEqual(len(json.loads(m.group(1))["t"]), len(self.rows))

    def test_html_is_self_contained(self):
        html = open(os.path.join(ROOT, "app", "index.html"), encoding="utf-8").read()
        self.assertNotRegex(html, r'(src|href)="https?://')

if __name__ == "__main__":
    unittest.main()
