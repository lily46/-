"""一覧ページから列車URLを集め、各列車ページを取得してキャッシュする。"""
import json, concurrent.futures as cf, sys
from jrparse import fetch, parse_list, BASE

ED = "2611"
# (駅コード, ページ番号, 駅名, 路線・方面)  末尾 0=平日 / 1=土曜・休日
PAGES = [
    ("0319", "01", "大崎", "埼京線・川越線 大宮・川越方面(下り)"),
    ("0319", "02", "大崎", "湘南新宿ライン 高崎・宇都宮方面(北行)"),
    ("0319", "03", "大崎", "湘南新宿ライン 横浜・大船方面(南行)"),
    ("0319", "04", "大崎", "山手線 渋谷・新宿方面(外回り)"),
    ("0319", "05", "大崎", "山手線 品川・東京方面(内回り)"),
    ("0319", "06", "大崎", "りんかい線 新木場方面(上り)"),
    ("0319", "91", "大崎", "相鉄線直通 相鉄線方面(下り)"),
    ("0866", "02", "新宿", "埼京線・川越線 大崎方面(上り)"),
    ("0866", "08", "新宿", "湘南新宿ライン 高崎・宇都宮・東武日光方面(北行)"),
    ("0866", "09", "新宿", "湘南新宿ライン 横浜・大船方面(南行)"),
    ("0866", "10", "新宿", "山手線 池袋・上野方面(外回り)"),
    ("0866", "11", "新宿", "山手線 渋谷・品川方面(内回り)"),
    ("0866", "12", "新宿", "成田エクスプレス 成田空港方面"),
    ("0866", "91", "新宿", "相鉄線直通 相鉄線方面(下り)"),
]
DAYS = {"0": "weekday", "1": "holiday"}

def main():
    jobs = []
    for st, pg, name, label in PAGES:
        for d, dn in DAYS.items():
            url = f"{BASE}{ED}/timetable/tt{st}/{st}{pg}{d}.html"
            jobs.append((st, pg, name, label, dn, url))
    out = []
    def go(j):
        st, pg, name, label, dn, url = j
        items = parse_list(fetch(url), url)
        return j, items
    with cf.ThreadPoolExecutor(4) as ex:
        for j, items in ex.map(go, jobs):
            st, pg, name, label, dn, url = j
            print(name, label, dn, len(items), flush=True)
            for it in items:
                out.append(dict(station=name, page=label, day=dn, **it))
    json.dump(out, open("/tmp/jr_lists.json", "w"), ensure_ascii=False)
    urls = sorted({o["url"] for o in out})
    print("unique train pages:", len(urls))
    n = 0
    def tr(u):
        fetch(u); return u
    with cf.ThreadPoolExecutor(6) as ex:
        for u in ex.map(tr, urls):
            n += 1
            if n % 200 == 0: print("fetched", n, flush=True)
    print("done", n)

main()
