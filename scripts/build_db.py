# -*- coding: utf-8 -*-
"""
build_db.py - Xây dựng database SQLite đồng nhất từ dữ liệu thô 4 nguồn.

Schema:
  draws              - toàn bộ kỳ quay (nguồn chính: GitHub, bổ sung jackpot từ kqxs.day)
  sources            - nhật ký thu thập từng nguồn
  frequency          - tần suất số theo từng nguồn & phạm vi
  pairs              - cặp số hay về cùng (atrungroi)
  jackpot_history    - lịch sử jackpot lớn nhất (atrungroi)
  meta               - thông tin tổng quan
"""
import json
import os
import re
import sqlite3
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.normpath(os.path.join(BASE, "..", "data", "raw"))
DB_PATH = os.path.normpath(os.path.join(BASE, "..", "data", "vietlott.db"))


def connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_schema(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS draws (
        id          INTEGER PRIMARY KEY,
        draw_code   TEXT UNIQUE NOT NULL,
        date        TEXT NOT NULL,
        n1 INTEGER, n2 INTEGER, n3 INTEGER, n4 INTEGER, n5 INTEGER, n6 INTEGER,
        power       INTEGER,
        jackpot1    INTEGER,
        jackpot2    INTEGER,
        source      TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_draws_date ON draws(date);

    CREATE TABLE IF NOT EXISTS sources (
        name        TEXT PRIMARY KEY,
        fetched_at  TEXT,
        draws_count INTEGER,
        notes       TEXT
    );

    CREATE TABLE IF NOT EXISTS frequency (
        source  TEXT NOT NULL,
        scope   TEXT NOT NULL,
        number  INTEGER NOT NULL,
        count   INTEGER NOT NULL,
        PRIMARY KEY (source, scope, number)
    );

    CREATE TABLE IF NOT EXISTS pairs (
        source  TEXT NOT NULL,
        pair    TEXT NOT NULL,
        count   INTEGER NOT NULL,
        PRIMARY KEY (source, pair)
    );

    CREATE TABLE IF NOT EXISTS jackpot_history (
        rank    INTEGER PRIMARY KEY,
        jackpot INTEGER,
        date    TEXT
    );

    CREATE TABLE IF NOT EXISTS meta (
        key   TEXT PRIMARY KEY,
        value TEXT
    );
    """)


def load_json(name):
    path = os.path.join(RAW, name)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def ingest_github(conn):
    """Nguồn chính: toàn bộ lịch sử kỳ quay."""
    data = load_json("source_github.json")
    if not data:
        print("  [SKIP] source_github.json không tồn tại")
        return 0
    rows = []
    for r in data:
        nums = r["numbers"]
        rows.append((
            int(r["id"]), r["id"], r["date"],
            nums[0], nums[1], nums[2], nums[3], nums[4], nums[5],
            r["power"], None, None, "github",
        ))
    conn.executemany("""
        INSERT OR REPLACE INTO draws
        (id, draw_code, date, n1, n2, n3, n4, n5, n6, power, jackpot1, jackpot2, source)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    conn.execute("INSERT OR REPLACE INTO sources VALUES (?,?,?,?)",
                 ("github", datetime.now().isoformat(timespec="seconds"), len(rows),
                  "Lịch sử đầy đủ từng kỳ quay (2017-08-01 → nay)"))
    print(f"  [OK] github: {len(rows)} kỳ quay")
    return len(rows)


def ingest_kqxsday(conn):
    """Bổ sung jackpot1/jackpot2 cho các kỳ từ kqxs.day."""
    data = load_json("source_kqxsday_draws.json")
    if not data:
        print("  [SKIP] source_kqxsday_draws.json không tồn tại")
        return 0
    n = 0
    for r in data.get("draws", []):
        code = re.sub(r"\D", "", r["drawCode"])
        code = code.zfill(5)
        j1 = int(r["jackpot1"]) if r.get("jackpot1") else None
        j2 = int(r["jackpot2"]) if r.get("jackpot2") else None
        cur = conn.execute("SELECT id FROM draws WHERE draw_code=?", (code,)).fetchone()
        if cur:
            conn.execute("UPDATE draws SET jackpot1=?, jackpot2=? WHERE draw_code=?",
                         (j1, j2, code))
            n += 1
        else:
            # kỳ chưa có trong DB (kỳ mới hơn GitHub) -> thêm mới
            nums = r["numbers"]
            conn.execute("""
                INSERT OR REPLACE INTO draws
                (id, draw_code, date, n1, n2, n3, n4, n5, n6, power, jackpot1, jackpot2, source)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (int(code), code, r["drawDate"],
                  nums[0], nums[1], nums[2], nums[3], nums[4], nums[5],
                  int(r["specialNum"]) if r.get("specialNum") else None,
                  j1, j2, "kqxsday"))
            n += 1
    conn.execute("INSERT OR REPLACE INTO sources VALUES (?,?,?,?)",
                 ("kqxsday", datetime.now().isoformat(timespec="seconds"), n,
                  "Kỳ quay + giá trị Jackpot (2020 → nay)"))
    print(f"  [OK] kqxsday: cập nhật jackpot cho {n} kỳ")
    return n


def ingest_frequency(conn):
    """Tần suất từ xosovietlott (all-time) và atrungroi (100 kỳ)."""
    x = load_json("source_xosovietlott.json")
    if x:
        for num, cnt in x["frequency"].items():
            conn.execute("INSERT OR REPLACE INTO frequency VALUES (?,?,?,?)",
                         ("xosovietlott", "all_time", int(num), int(cnt)))
        conn.execute("INSERT OR REPLACE INTO sources VALUES (?,?,?,?)",
                     ("xosovietlott", datetime.now().isoformat(timespec="seconds"),
                      x.get("draws"), "Tần suất all-time"))
        print(f"  [OK] xosovietlott: tần suất {len(x['frequency'])} số (all-time)")

    a = load_json("source_atrungroi.json")
    if a:
        for num, cnt in a.get("freq_100", {}).items():
            conn.execute("INSERT OR REPLACE INTO frequency VALUES (?,?,?,?)",
                         ("atrungroi", "100_draws", int(num), int(cnt)))
        for num, cnt in a.get("top_power", {}).items():
            conn.execute("INSERT OR REPLACE INTO frequency VALUES (?,?,?,?)",
                         ("atrungroi", "power_100", int(num), int(cnt)))
        for p in a.get("pairs", []):
            conn.execute("INSERT OR REPLACE INTO pairs VALUES (?,?,?)",
                         ("atrungroi", p["pair"], int(p["count"])))
        conn.execute("DELETE FROM jackpot_history")
        for j in a.get("jackpots", []):
            val = int(re.sub(r"\D", "", j["jackpot"])) if j["jackpot"] else None
            conn.execute("INSERT OR REPLACE INTO jackpot_history VALUES (?,?,?)",
                         (int(j["rank"]), val, j["date"]))
        conn.execute("INSERT OR REPLACE INTO sources VALUES (?,?,?,?)",
                     ("atrungroi", datetime.now().isoformat(timespec="seconds"),
                      None, "Tần suất 100 kỳ, cặp số, jackpot"))
        print(f"  [OK] atrungroi: tần suất 100 kỳ, {len(a.get('pairs', []))} cặp số, "
              f"{len(a.get('jackpots', []))} jackpot")

    k = load_json("source_kqxsday_freq.json")
    if k:
        for f in k.get("frequency", []):
            conn.execute("INSERT OR REPLACE INTO frequency VALUES (?,?,?,?)",
                         ("kqxsday", "all_time", int(f["number"]), int(f["count"])))
        print(f"  [OK] kqxsday: tần suất {len(k.get('frequency', []))} số (all-time)")


def compute_derived(conn):
    """Tính tần suất thực tế từ bảng draws (nguồn chuẩn nhất)."""
    conn.execute("DELETE FROM frequency WHERE source='derived'")
    rows = conn.execute("SELECT n1,n2,n3,n4,n5,n6,power FROM draws").fetchall()
    counts = {}
    power_counts = {}
    for r in rows:
        for n in r[:6]:
            if n:
                counts[n] = counts.get(n, 0) + 1
        if r[6]:
            power_counts[r[6]] = power_counts.get(r[6], 0) + 1
    for num in range(1, 56):
        conn.execute("INSERT OR REPLACE INTO frequency VALUES (?,?,?,?)",
                     ("derived", "all_time", num, counts.get(num, 0)))
        conn.execute("INSERT OR REPLACE INTO frequency VALUES (?,?,?,?)",
                     ("derived", "power", num, power_counts.get(num, 0)))

    # tần suất 30/60/90 kỳ gần nhất
    total = conn.execute("SELECT COUNT(*) FROM draws").fetchone()[0]
    for window, scope in ((30, "last_30"), (60, "last_60"), (90, "last_90")):
        wc = {}
        for r in conn.execute(
                "SELECT n1,n2,n3,n4,n5,n6 FROM draws ORDER BY id DESC LIMIT ?",
                (window,)).fetchall():
            for n in r:
                if n:
                    wc[n] = wc.get(n, 0) + 1
        for num in range(1, 56):
            conn.execute("INSERT OR REPLACE INTO frequency VALUES (?,?,?,?)",
                         ("derived", scope, num, wc.get(num, 0)))

    # số ngày chưa xuất hiện (gan) - tính từ kỳ mới nhất
    last_date = conn.execute("SELECT MAX(date) FROM draws").fetchone()[0]
    last_seen = {}
    for r in conn.execute("SELECT date, n1,n2,n3,n4,n5,n6 FROM draws ORDER BY date").fetchall():
        for n in r[1:]:
            if n:
                last_seen[n] = r[0]
    from datetime import date as _date
    ld = _date.fromisoformat(last_date)
    for num in range(1, 56):
        ls = last_seen.get(num)
        days = (ld - _date.fromisoformat(ls)).days if ls else None
        conn.execute("INSERT OR REPLACE INTO frequency VALUES (?,?,?,?)",
                     ("derived", "gan_days", num, days if days is not None else -1))

    conn.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", ("total_draws", str(total)))
    conn.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", ("first_date", conn.execute(
        "SELECT MIN(date) FROM draws").fetchone()[0]))
    conn.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", ("last_date", last_date))
    print(f"  [OK] derived: tần suất all-time/30/60/90, gan, power (tổng {total} kỳ)")


def main():
    conn = connect()
    init_schema(conn)
    print("Xây dựng database:", DB_PATH)
    ingest_github(conn)
    ingest_kqxsday(conn)
    ingest_frequency(conn)
    compute_derived(conn)
    conn.commit()
    # báo cáo
    total = conn.execute("SELECT COUNT(*) FROM draws").fetchone()[0]
    with_jp = conn.execute("SELECT COUNT(*) FROM draws WHERE jackpot1 IS NOT NULL").fetchone()[0]
    print(f"\nTổng kết: {total} kỳ quay trong DB, {with_jp} kỳ có giá trị Jackpot.")
    conn.close()


if __name__ == "__main__":
    main()