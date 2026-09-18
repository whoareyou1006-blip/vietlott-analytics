# -*- coding: utf-8 -*-
"""
analyze_miss.py - Phân tích kỳ 01397: vì sao dự đoán trượt?
So sánh hồ sơ (profile) số trúng thực tế vs số được dự đoán.
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from predict import Predictor

DB = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "vietlott.db"))

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# --- kỳ 01397 ---
draw = conn.execute("SELECT * FROM draws WHERE draw_code='01397'").fetchone()
actual = [draw["n1"], draw["n2"], draw["n3"], draw["n4"], draw["n5"], draw["n6"]]
power = draw["power"]
print(f"Kỳ 01397 ({draw['date']}): {actual} + Power {power}")
print()

# --- tín hiệu của từng số trúng ---
p = Predictor(DB)
sig = p.signals()  # dữ liệu đến trước kỳ 01397 (vì 01397 đã trong DB, signals dùng toàn bộ... cần as_of)
# dùng as_of_id=1397 để chỉ dùng dữ liệu trước kỳ đó
sig = p.signals(as_of_id=1397)
raw = sig["raw"]

print("=== Hồ sơ 6 số trúng thực tế (tín hiệu TRƯỚC kỳ 01397) ===")
print(f"{'Số':>4} {'FreqAll':>8} {'RankAll':>8} {'Freq30':>7} {'Freq90':>7} {'Gan(ngày)':>10} {'PowerFreq':>9}")
freq_all_sorted = sorted(raw["freq_all"].items(), key=lambda x: -x[1])
rank_all = {n: i + 1 for i, (n, _) in enumerate(freq_all_sorted)}
for n in actual + [power]:
    print(f"{n:>4} {raw['freq_all'].get(n,0):>8} {rank_all.get(n,0):>8} "
          f"{raw['freq_30'].get(n,0):>7} {raw['freq_90'].get(n,0):>7} "
          f"{raw['gan'].get(n,0):>10} {raw['power_freq'].get(n,0):>9}")

print()
print("=== Hồ sơ 12 số được dự đoán (2 dãy) ===")
pred = p.predict(as_of_id=1397)
for s in pred["sets"]:
    print(f"[{s['label']}] {s['numbers']} + Power {s['power']}")
    for n in s["numbers"]:
        print(f"  {n:>4}: FreqAll={raw['freq_all'].get(n,0):>4} (rank {rank_all.get(n,0):>2}) "
              f"Freq30={raw['freq_30'].get(n,0):>2} Gan={raw['gan'].get(n,0):>3} ngày")

print()
print("=== Phân tích cấu trúc ===")
def profile(nums):
    odd = sum(1 for n in nums if n % 2)
    even = 6 - odd
    s = sum(nums)
    decades = {}
    for n in nums:
        d = (n - 1) // 10
        decades[d] = decades.get(d, 0) + 1
    return f"lẻ/chẵn={odd}:{even}, tổng={s}, phân bố chục={dict(sorted(decades.items()))}"

print("Thực tế :", profile(actual))
for s in pred["sets"]:
    print(f"{s['label'][:12]:12s}:", profile(s["numbers"]))

# --- phân bố tổng của toàn bộ lịch sử ---
print()
print("=== Phân bố tổng 6 số (toàn lịch sử) ===")
sums = []
for r in conn.execute("SELECT n1,n2,n3,n4,n5,n6 FROM draws"):
    sums.append(sum(r))
import statistics
print(f"Trung bình: {statistics.mean(sums):.0f}, trung vị: {statistics.median(sums):.0f}, "
      f"khoảng 90%: {sorted(sums)[int(0.05*len(sums))]}–{sorted(sums)[int(0.95*len(sums))]}")
print(f"Tổng kỳ 01397: {sum(actual)}")

# --- phân bố lẻ/chẵn ---
print()
print("=== Phân bố lẻ/chẵn (toàn lịch sử) ===")
oe = {}
for r in conn.execute("SELECT n1,n2,n3,n4,n5,n6 FROM draws"):
    odd = sum(1 for n in r if n % 2)
    oe[odd] = oe.get(odd, 0) + 1
for k in sorted(oe):
    print(f"  {k} lẻ / {6-k} chẵn: {oe[k]} kỳ ({100*oe[k]/1397:.1f}%)")

# --- tần suất theo thứ hạng: số trúng thường ở hạng nào? ---
print()
print("=== Thứ hạng FreqAll của các số trúng (toàn lịch sử, 500 kỳ gần) ===")
import collections
rank_buckets = collections.Counter()
for r in conn.execute("SELECT n1,n2,n3,n4,n5,n6 FROM draws ORDER BY id DESC LIMIT 500"):
    for n in r:
        rk = rank_all.get(n, 55)
        if rk <= 10: rank_buckets["top10"] += 1
        elif rk <= 20: rank_buckets["11-20"] += 1
        elif rk <= 30: rank_buckets["21-30"] += 1
        elif rk <= 40: rank_buckets["31-40"] += 1
        else: rank_buckets["41-55"] += 1
total = sum(rank_buckets.values())
for k in ["top10", "11-20", "21-30", "31-40", "41-55"]:
    print(f"  {k:>6}: {rank_buckets[k]:>4} số trúng ({100*rank_buckets[k]/total:.1f}%)")

conn.close()