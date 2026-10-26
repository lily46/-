"""JR東日本 時刻表サイト (timetables.jreast.co.jp) の取得・解析ユーティリティ。"""
import hashlib, os, re, sys, time, urllib.request, urllib.error
from urllib.parse import urljoin
from bs4 import BeautifulSoup

BASE = "https://timetables.jreast.co.jp/"
CACHE = os.environ.get("JR_CACHE", "/tmp/jr_cache")
os.makedirs(CACHE, exist_ok=True)
UA = "Mozilla/5.0 (offline-timetable-db; personal use)"


def fetch(url, retries=4):
    key = os.path.join(CACHE, hashlib.md5(url.encode()).hexdigest())
    if os.path.exists(key):
        return open(key, encoding="utf-8").read()
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            body = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
            open(key, "w", encoding="utf-8").write(body)
            return body
        except Exception as e:  # noqa
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"fetch failed {url}: {last}")


def parse_list(html, url):
    """駅の方面別時刻表ページ -> [{hour, minute, mark, dest_mark, url}]"""
    soup = BeautifulSoup(html, "lxml")
    out = []
    for tr in soup.select("tr[id^=time_]"):
        hour = int(tr["id"].split("_")[1])
        for d in tr.select("div.timetable_time"):
            a = d.find("a")
            m = d.select_one("span.minute")
            if not (a and m):
                continue
            out.append(dict(hour=hour, minute=int(m.text.strip()),
                            mark=d.get("data-train", ""), dest_mark=d.get("data-dest", ""),
                            url=urljoin(url, a["href"])))
    return out


TIME_RE = re.compile(r"(\d{1,2}):(\d\d)\s*(発|着)?")


def parse_train(html):
    """列車詳細ページ -> 列(列車)ごとのリスト。
    各列: {type, number, note, stops:[{station, code, arr, dep, passing}]}"""
    soup = BeautifulSoup(html, "lxml")
    tbl = soup.select_one("table#tbl_train")
    if tbl is None:
        return []
    rows = tbl.find_all("tr")
    cols = []  # header-derived columns
    stop_rows = []
    for tr in rows:
        cls = tr.get("class", [])
        th = tr.find("th")
        if "train" in cls:
            label = th.get_text(strip=True)
            cells = tr.find_all("td")
            vals = [re.sub(r"\s+", " ", c.get_text(" ", strip=True)) for c in cells]
            if label == "列車種別":
                cols = [dict(type=v, number="", note="", stops=[]) for v in vals]
            elif label == "列車番号":
                for c, v in zip(cols, vals):
                    c["number"] = v
            elif label == "運転日":
                for c, v in zip(cols, vals):
                    c["note"] = v
        elif "time" in cls and th is not None:
            stop_rows.append(tr)
    for tr in stop_rows:
        th = tr.find("th")
        a = th.find("a")
        name = th.get_text(strip=True)
        m = re.search(r"list(\d+)\.html", a["href"]) if a else None
        code = m.group(1) if m else None
        tds = tr.find_all("td", class_="time")
        for c, td in zip(cols, tds):
            txt = td.get_text(" ", strip=True)
            arr = dep = None
            for t in td.find_all("li"):
                s = t.get_text(" ", strip=True)
                mm = TIME_RE.search(s)
                if not mm:
                    continue
                hhmm = f"{int(mm.group(1)):02d}:{mm.group(2)}"
                if mm.group(3) == "着":
                    arr = hhmm
                else:  # 発 / 記号なし(通過時刻など) は発扱い
                    dep = hhmm
            passing = (arr is None and dep is None and
                       any(k in txt for k in ("レ", "通過", "↓", "||", "－", "ー")))
            if arr or dep or passing:
                c["stops"].append(dict(station=name, code=code, arr=arr, dep=dep,
                                       passing=passing, raw=txt))
    return cols


if __name__ == "__main__":
    u = sys.argv[1]
    h = fetch(u)
    import json
    print(json.dumps(parse_train(h) if "/train/" in u else parse_list(h, u)[:5],
                     ensure_ascii=False, indent=1)[:3000])
