"""取得済みキャッシュ -> 大崎〜新宿を走る列車レコード(JSON)。"""
import json, os, re, collections
WORK = os.environ.get("JR_WORK", "/tmp")
from jrparse import fetch, parse_train

OSAKI, SHINJUKU, SHINAGAWA = "0319", "0866", "0788"
# 大崎-新宿間(渋谷経由)の途中駅
SIDE = {"1654", "1256", "0808", "0290", "1552", "0695"}  # 代々木 原宿 渋谷 恵比寿 目黒 五反田
SIDE_NAMES = ["五反田", "目黒", "恵比寿", "渋谷", "原宿", "代々木"]

def hm(s):
    h, m = map(int, s.split(":"))
    return h * 60 + m + (1440 if h < 4 else 0)

def line_of(label):
    for k in ("山手線", "湘南新宿ライン", "埼京線", "りんかい線", "成田エクスプレス", "相鉄線直通"):
        if label.startswith(k):
            return k
    return label

def classify(stops):
    codes = [s["code"] for s in stops]
    if SHINJUKU not in codes:
        return None
    j = codes.index(SHINJUKU)
    if OSAKI in codes:
        i = codes.index(OSAKI)
        lo, hi = sorted((i, j))
        if all(c in SIDE for c in codes[lo + 1:hi]):
            return ("O>S" if i < j else "S>O"), i, j, False
        # 山手線のように1周する列車: 2回目の大崎を見る
        idx = [k for k, c in enumerate(codes) if c == OSAKI]
        for i in idx:
            lo, hi = sorted((i, j))
            if all(c in SIDE for c in codes[lo + 1:hi]):
                return ("O>S" if i < j else "S>O"), i, j, False
        return None
    # 大崎を通過 (成田エクスプレス・踊り子など)。新宿の隣が渋谷で、その先に
    # 大崎〜渋谷間以外の駅がある(= 恵比寿等で打ち切りではなく南へ抜ける)列車
    SHIBUYA = "0808"
    if SHIBUYA in codes:
        k = codes.index(SHIBUYA)
        if k == j + 1 and any(c not in SIDE for c in codes[k + 1:]):
            return "S>O", None, j, True
        if k == j - 1 and any(c not in SIDE for c in codes[:k]):
            return "O>S", None, j, True
    return None

SIDE_S = {"0290", "1552", "0695"}          # 恵比寿 目黒 五反田 (渋谷-大崎間)
NORTH_OF_SHIBUYA = {"0866", "1654", "1256"}  # 新宿 代々木 原宿

def classify_h(stops):
    """渋谷→大崎。(渋谷の行index, 大崎の行index|None, 大崎通過か) を返す。"""
    timed = [(n, s) for n, s in enumerate(stops) if s["arr"] or s["dep"]]
    codes = [s["code"] for _, s in timed]
    if "0808" not in codes:
        return None
    k = codes.index("0808")
    if not timed[k][1]["dep"]:
        return None
    after = codes[k + 1:]
    if OSAKI in after:
        a = after.index(OSAKI)
        if all(c in SIDE_S for c in after[:a]):
            return timed[k][0], timed[k + 1 + a][0], False
        return None
    if OSAKI in codes:                      # 大崎が渋谷より前 = 北行
        return None
    south = (any(c in NORTH_OF_SHIBUYA for c in codes[:k]) or
             (k == 0 and after and after[0] not in NORTH_OF_SHIBUYA))
    if south and any(c not in SIDE_S for c in after):
        return timed[k][0], None, True
    return None

def sort_key(r):
    if r["direction"] == "H>O":
        return hm(r["shibuya_time"])
    if r["direction"] == "O>S" and not r["osaki_passing"]:
        return hm(r["osaki_time"])
    if r["direction"] == "O>S":
        return hm(r["shinjuku_time"])
    return hm(r["shinjuku_time"])

def main():
    lists = json.load(open(os.path.join(WORK, "jr_lists.json")))
    refs = collections.defaultdict(lambda: dict(days=set(), pages=set()))
    for o in lists:
        refs[o["url"]]["days"].add(o["day"])
        refs[o["url"]]["pages"].add((o["station"], o["page"]))
    recs = {}
    for url, r in sorted(refs.items()):
        for ci, c in enumerate(parse_train(fetch(url))):
            st = c["stops"]
            if not st:
                continue
            cands = []
            res = classify(st)
            if res:
                d, i, j, passing = res
                sj = st[j]
                so = st[i] if i is not None else None
                if d == "O>S":
                    o_t = so and so["dep"]
                    s_t = sj["arr"] or sj["dep"]
                    ok = not (so and not o_t)      # 大崎止まり -> 新宿へ行かない
                else:
                    s_t = sj["dep"]
                    o_t = so and (so["arr"] or so["dep"])
                    ok = bool(s_t)                 # 新宿着のみ
                if ok and (passing or o_t):
                    cands.append(dict(direction=d, osaki_time=o_t, osaki_passing=passing,
                                      shinjuku_time=s_t, shibuya_time=None))
            resh = classify_h(st)
            if resh:
                k, i, passing = resh
                o_t = None if i is None else (st[i]["arr"] or st[i]["dep"])
                if passing or o_t:
                    cands.append(dict(direction="H>O", osaki_time=o_t, osaki_passing=passing,
                                      shinjuku_time=None, shibuya_time=st[k]["dep"]))
            if not cands:
                continue
            pages = sorted(f"{a}:{b}" for a, b in r["pages"])
            line = None
            for a, b in sorted(r["pages"]):
                line = line_of(b)
                if line == "山手線":
                    break
            names = {s["station"] for s in st}
            if c.get("name", "").startswith("成田エクスプレス"):
                line = "成田エクスプレス"
            elif c["type"] == "特急":
                line = "特急"
            elif line != "山手線":
                if "羽沢横浜国大" in names:
                    line = "相鉄線直通"
                elif names & {"新木場", "東京テレポート", "天王洲アイル"}:
                    line = "りんかい線直通"
            for cand in cands:
                for day in sorted(r["days"]):
                    rid = f"{url.split('/train/')[1][:-5].replace('/', '_')}_{ci}_{day[0]}_{cand['direction'][0]}"
                    recs[rid] = dict(
                        id=rid, day=day, line=line,
                        group="山手線" if line == "山手線" else "その他",
                        train_type=c["type"], train_name=c.get("name", ""), train_number=c["number"],
                        origin=st[0]["station"], destination=st[-1]["station"],
                        note=c["note"], source=url, listed_in=pages, **cand,
                    )
    seen = {}
    for rid, r in sorted(recs.items()):
        k = (r["day"], r["direction"], r["train_number"], r["osaki_time"], r["shinjuku_time"], r["shibuya_time"])
        if k in seen:
            seen[k]["listed_in"] = sorted(set(seen[k]["listed_in"]) | set(r["listed_in"]))
            seen[k].setdefault("alt_sources", []).append(r["source"])
        else:
            seen[k] = r
    recs = {r["id"]: r for r in seen.values()}
    out = sorted(recs.values(), key=lambda r: (r["day"], r["direction"], r["group"], sort_key(r)))
    json.dump(out, open(os.path.join(WORK, "jr_records.json"), "w"), ensure_ascii=False, indent=0)
    c = collections.Counter((r["day"], r["direction"], r["group"], r["line"]) for r in out)
    for k, v in sorted(c.items()):
        print(k, v)
    print("total", len(out))

main()
