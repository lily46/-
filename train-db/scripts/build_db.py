"""jr_records.json -> data/trains.sqlite, data/trains.csv, data/trains.json, app/index.html"""
import csv, datetime, json, os, sqlite3
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.environ.get("JR_WORK", "/tmp")
EDITION = "2611"
FETCHED = os.environ.get("JR_FETCHED", datetime.date.today().isoformat())
SOURCE = "https://timetables.jreast.co.jp/ (JR東日本 駅の時刻表)"

def minutes(t):
    if not t:
        return None
    h, m = map(int, t.split(":"))
    return h * 60 + m

def main():
    recs = json.load(open(os.path.join(WORK, "jr_records.json")))
    rows = []
    for r in recs:
        om, sm, hmn = minutes(r["osaki_time"]), minutes(r["shinjuku_time"]), minutes(r["shibuya_time"])
        rows.append(dict(
            id=r["id"], day_type=r["day"], direction=r["direction"], group_name=r["group"],
            line=r["line"], train_type=r["train_type"], train_name=r["train_name"],
            train_number=r["train_number"], origin=r["origin"], destination=r["destination"],
            osaki_time=r["osaki_time"], osaki_passing=int(r["osaki_passing"]),
            shinjuku_time=r["shinjuku_time"], shibuya_time=r["shibuya_time"],
            osaki_min=om, shinjuku_min=sm, shibuya_min=hmn,
            sort_min=hmn if r["direction"] == "H>O" else (om if om is not None else sm),
            note=r["note"], source_url=r["source"]))
    rows.sort(key=lambda x: (x["day_type"], x["direction"], x["group_name"], x["sort_min"], x["train_number"]))
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "app"), exist_ok=True)
    cols = list(rows[0])
    # SQLite
    dbp = os.path.join(ROOT, "data", "trains.sqlite")
    if os.path.exists(dbp):
        os.remove(dbp)
    db = sqlite3.connect(dbp)
    db.execute("""CREATE TABLE trains(
        id TEXT PRIMARY KEY, day_type TEXT NOT NULL CHECK(day_type IN ('weekday','holiday')),
        direction TEXT NOT NULL CHECK(direction IN ('O>S','S>O','H>O')),
        group_name TEXT NOT NULL, line TEXT, train_type TEXT, train_name TEXT, train_number TEXT,
        origin TEXT, destination TEXT,
        osaki_time TEXT, osaki_passing INTEGER NOT NULL, shinjuku_time TEXT, shibuya_time TEXT,
        osaki_min INTEGER, shinjuku_min INTEGER, shibuya_min INTEGER, sort_min INTEGER NOT NULL,
        note TEXT, source_url TEXT)""")
    db.executemany(f"INSERT INTO trains({','.join(cols)}) VALUES({','.join('?'*len(cols))})",
                   [tuple(r[c] for c in cols) for r in rows])
    db.execute("CREATE INDEX idx_lookup ON trains(day_type, direction, group_name, sort_min)")
    db.execute("CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT)")
    meta = {"edition": EDITION, "fetched": FETCHED, "source": SOURCE,
            "section": "大崎〜新宿・渋谷〜大崎 (山手線・埼京線・湘南新宿ライン・相鉄直通・特急)",
            "time_format": "HH:MM。24:00以降は翌日の0時台(24:03 = 0:03)。osaki_passing=1は大崎通過(osaki_timeはNULL)",
            "direction": "O>S = 大崎→新宿(osaki_time=大崎発, shinjuku_time=新宿着) / S>O = 新宿→大崎(shinjuku_time=新宿発, osaki_time=大崎着) / H>O = 渋谷→大崎(shibuya_time=渋谷発, osaki_time=大崎着, shinjuku_time=NULL)"}
    db.executemany("INSERT INTO meta VALUES(?,?)", meta.items())
    db.commit(); db.close()
    # CSV
    with open(os.path.join(ROOT, "data", "trains.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    # JSON + HTML
    payload = {"meta": meta, "trains": rows}
    json.dump(payload, open(os.path.join(ROOT, "data", "trains.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    slim = [[r["day_type"], r["direction"], r["group_name"], r["line"], r["train_type"], r["train_name"],
             r["train_number"], r["origin"], r["destination"], r["osaki_time"], r["osaki_passing"],
             r["shinjuku_time"], r["sort_min"], r["osaki_min"], r["shinjuku_min"],
             r["shibuya_time"], r["shibuya_min"]] for r in rows]
    tpl = open(os.path.join(ROOT, "scripts", "app_template.html"), encoding="utf-8").read()
    html = tpl.replace("/*DATA*/null", json.dumps({"meta": meta, "t": slim}, ensure_ascii=False, separators=(",", ":")))
    open(os.path.join(ROOT, "app", "index.html"), "w", encoding="utf-8").write(html)
    print("rows", len(rows))

main()
