# -*- coding: utf-8 -*-
"""
fetch_data.py - Thu thập dữ liệu Power 6/55 từ 4 nguồn:
  1. GitHub vietvudanh/vietlott-data  -> lịch sử đầy đủ từng kỳ (JSONL)
  2. xosovietlott.org                 -> tần suất all-time
  3. atrungroi.com                    -> tần suất 100 kỳ, cặp số, jackpot
  4. kqxs.day                         -> tần suất, số gan, số Power (qua API)
Dữ liệu thô lưu vào data/raw/ dưới dạng JSON chuẩn hóa.
"""
import json
import os
import re
import sys
import urllib.request
import urllib.error

RAW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "raw")
RAW_DIR = os.path.normpath(RAW_DIR)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}


def http_get(url, timeout=60):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def save_json(name, data):
    path = os.path.join(RAW_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"  [OK] {name} ({len(data)} records)")
    return path


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s).strip()


# ---------------------------------------------------------------- source 1
def fetch_github():
    """Lịch sử đầy đủ từng kỳ quay từ repo vietvudanh/vietlott-data."""
    print("[1/4] GitHub vietlott-data ...")
    url = "https://raw.githubusercontent.com/vietvudanh/vietlott-data/main/data/power655.jsonl"
    text = http_get(url)
    records = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        nums = rec["result"]
        records.append({
            "date": rec["date"],
            "id": rec["id"],
            "numbers": nums[:6],
            "power": nums[6] if len(nums) > 6 else None,
        })
    return save_json("source_github.json", records)


# ---------------------------------------------------------------- source 2
def fetch_xosovietlott():
    """Bảng tần suất all-time từ xosovietlott.org."""
    print("[2/4] xosovietlott.org ...")
    url = "https://xosovietlott.org/power-655/thong-ke/tan-suat/"
    html = http_get(url)
    tables = re.findall(r"<table.*?</table>", html, re.S)
    freq = {}
    for t in tables:
        rows = re.findall(r"<tr.*?</tr>", t, re.S)
        for r in rows:
            cells = [strip_tags(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
            if len(cells) == 2 and cells[0].isdigit() and cells[1].isdigit():
                freq[int(cells[0])] = int(cells[1])
    if not freq:
        raise RuntimeError("Không parse được bảng tần suất xosovietlott")
    # trích số kỳ từ meta description
    m = re.search(r"tr[êe]n\s+([\d.,]+)\s+k[ỳy]", html)
    draws = int(m.group(1).replace(".", "").replace(",", "")) if m else None
    return save_json("source_xosovietlott.json", {
        "draws": draws,
        "frequency": freq,
    })


# ---------------------------------------------------------------- source 3
def fetch_atrungroi():
    """Thống kê 100 kỳ, số Power, cặp số, jackpot từ atrungroi.com."""
    print("[3/4] atrungroi.com ...")
    url = "https://atrungroi.com/xo-so-power-6-55-vietlott/thong-ke-xo-so-power-6-55.html"
    html = http_get(url)
    tables = re.findall(r"<table.*?</table>", html, re.S)

    def parse_freq_table(t):
        out = {}
        rows = re.findall(r"<tr.*?</tr>", t, re.S)
        for r in rows:
            cells = [strip_tags(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
            # cells like ['01','15 lần','02','13 lần',...]
            for i in range(0, len(cells) - 1, 2):
                num = cells[i]
                cnt = cells[i + 1]
                if num.isdigit() and "lần" in cnt:
                    out[int(num)] = int(re.sub(r"\D", "", cnt))
        return out

    def parse_pair_table(t):
        out = []
        rows = re.findall(r"<tr.*?</tr>", t, re.S)
        for r in rows:
            cells = [strip_tags(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
            for i in range(0, len(cells) - 1, 2):
                pair = cells[i]
                cnt = cells[i + 1]
                if len(pair) == 4 and pair.isdigit() and "lần" in cnt:
                    out.append({"pair": pair, "count": int(re.sub(r"\D", "", cnt))})
        return out

    def parse_jackpot_table(t):
        out = []
        rows = re.findall(r"<tr.*?</tr>", t, re.S)
        for r in rows[1:]:
            cells = [strip_tags(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
            if len(cells) >= 3 and cells[0].isdigit():
                out.append({
                    "rank": int(cells[0]),
                    "jackpot": cells[1],
                    "date": cells[2],
                })
        return out

    data = {
        "freq_100": parse_freq_table(tables[0]) if len(tables) > 0 else {},
        "top_power": parse_freq_table(tables[1]) if len(tables) > 1 else {},
        "least_freq": parse_freq_table(tables[2]) if len(tables) > 2 else {},
        "pairs": parse_pair_table(tables[4]) if len(tables) > 4 else [],
        "jackpots": parse_jackpot_table(tables[7]) if len(tables) > 7 else [],
    }
    return save_json("source_atrungroi.json", data)


# ---------------------------------------------------------------- source 4
def fetch_kqxsday():
    """kqxs.day render dữ liệu qua JS - tìm API endpoint trong trang."""
    print("[4/4] kqxs.day ...")
    url = "https://kqxs.day/thong-ke-vietlott/power655/"
    html = http_get(url)
    # tìm các URL API / endpoint trong HTML & script
    candidates = set()
    for m in re.finditer(r"[\"']((?:https?://[^\"']*|/wp-json[^\"']*|/api[^\"']*|/vietlott[^\"']*))[\"']", html):
        candidates.add(m.group(1))
    for m in re.finditer(r"fetch\(\s*[\"']([^\"']+)[\"']", html):
        candidates.add(m.group(1))
    for m in re.finditer(r"axios\.(?:get|post)\(\s*[\"']([^\"']+)[\"']", html):
        candidates.add(m.group(1))
    # script srcs
    for m in re.finditer(r'<script[^>]*src="([^"]+)"', html):
        candidates.add(m.group(1))

    api_urls = [c for c in candidates if any(k in c for k in ("wp-json", "api", "vietlott", "thong-ke", "power655"))]
    print("  API candidates:", api_urls[:10])

    # thử các endpoint wp-json phổ biến
    base = "https://kqxs.day"
    tried = []
    for u in api_urls:
        full = u if u.startswith("http") else base + u
        tried.append(full)
        try:
            text = http_get(full, timeout=20)
            if text.strip().startswith(("{", "[")):
                data = json.loads(text)
                return save_json("source_kqxsday.json", data)
        except Exception:
            continue

    # fallback: parse trực tiếp bảng tần suất nếu có trong HTML tĩnh
    tables = re.findall(r"<table.*?</table>", html, re.S)
    freq = {}
    for t in tables:
        rows = re.findall(r"<tr.*?</tr>", t, re.S)
        for r in rows:
            cells = [strip_tags(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
            if len(cells) == 2 and cells[0].isdigit() and cells[1].isdigit():
                freq[int(cells[0])] = int(cells[1])
    if freq:
        return save_json("source_kqxsday.json", {"frequency": freq, "note": "parsed from static HTML"})

    print("  [WARN] kqxs.day: không lấy được dữ liệu, bỏ qua nguồn này")
    return None


# ---------------------------------------------------------------- source 4b
def fetch_kqxsday_draws():
    """Kỳ quay + giá trị Jackpot 1/2 từ API kqxs.day (bổ sung cho GitHub)."""
    print("[4b] kqxs.day draws API ...")
    url = ("https://kqxs.day/wp-json/xoso/v1/statistics/vietlott-draws"
           "?gameType=power655&from=2017-01-01&to=2026-12-31")
    text = http_get(url, timeout=90)
    data = json.loads(text)
    draws = data.get("draws", [])
    # chuẩn hóa drawCode -> 5 chữ số
    for d in draws:
        code = re.sub(r"\D", "", d.get("drawCode", ""))
        d["drawCode"] = code.zfill(5)
    path = os.path.join(RAW_DIR, "source_kqxsday_draws.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"  [OK] source_kqxsday_draws.json ({len(draws)} kỳ, có Jackpot 1/2)")
    return path


def main():
    os.makedirs(RAW_DIR, exist_ok=True)
    results = {}
    results["github"] = fetch_github()
    results["xosovietlott"] = fetch_xosovietlott()
    results["atrungroi"] = fetch_atrungroi()
    results["kqxsday"] = fetch_kqxsday()
    results["kqxsday_draws"] = fetch_kqxsday_draws()
    print("\nHoàn tất thu thập dữ liệu thô.")


if __name__ == "__main__":
    main()