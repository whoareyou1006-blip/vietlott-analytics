# -*- coding: utf-8 -*-
"""
backtest_contrarian.py - Kiểm chứng bằng dữ liệu thật:

PHẦN 1: Chiến lược "tư duy ngược" có thắng được mô hình/ngẫu nhiên không?
  - contrarian : chọn 6 số ĐIỂM THẤP NHẤT của mô hình (làm ngược hoàn toàn)
  - cold       : chọn số GAN lâu nhất + tần suất thấp nhất (số lạnh)
  - anti_hot   : chọn số ít xuất hiện nhất trong 30 kỳ gần (ngược số nóng)
  - model      : chiến lược Cân bằng (baseline)
  - random     : ngẫu nhiên thuần

PHẦN 2: Kiểm tra giả thuyết "nhà cái né số đông người chọn"
  - Số 1-31 (ngày sinh, người chơi hay chọn) có xuất hiện ÍT hơn 32-55 không?
  - Số "nóng" có bị né ở kỳ sau không? (kiểm tra autocorrelation)
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from predict import Predictor, DECADES

DB = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "vietlott.db"))
p = Predictor(DB)
rng = random.Random(12345)

PROFILE = {"odd_even": [2, 3, 4], "sum_lo": 106, "sum_hi": 228,
           "min_decades": 4, "max_consecutive": 2}


def structure_ok(nums):
    odd = sum(1 for n in nums if n % 2)
    if odd not in PROFILE["odd_even"]:
        return False
    if not (PROFILE["sum_lo"] <= sum(nums) <= PROFILE["sum_hi"]):
        return False
    if len({(n - 1) // 10 for n in nums}) < PROFILE["min_decades"]:
        return False
    s = sorted(nums)
    run = 1
    for i in range(1, len(s)):
        run = run + 1 if s[i] == s[i - 1] + 1 else 1
        if run > PROFILE["max_consecutive"]:
            return False
    return True


def gen_from_scores(scores, prefer_high=True, pool_size=30, tries=3000):
    """Sinh 6 số thỏa cấu trúc, ưu tiên điểm cao (hoặc thấp nếu prefer_high=False)."""
    items = sorted(scores.items(), key=lambda x: -x[1])
    pool = [n for n, _ in (items[:pool_size] if prefer_high else items[-pool_size:])]
    mx = max(scores.values())
    best = None
    for _ in range(tries):
        cand = set()
        guard = 0
        while len(cand) < 6 and guard < 100:
            guard += 1
            w = []
            for n in pool:
                base = scores[n] if prefer_high else (mx - scores[n])
                w.append(max(base, 0.0) + rng.uniform(0, 0.02))
            tw = sum(w)
            r = rng.random() * tw
            acc = 0.0
            for n, wi in zip(pool, w):
                acc += wi
                if r <= acc:
                    cand.add(n)
                    break
        if len(cand) < 6 or not structure_ok(cand):
            continue
        sc = sum(scores[n] for n in cand)
        if best is None or sc > best[0]:
            best = (sc, sorted(cand))
    return best[1] if best else sorted(pool[:6])


# ============================================================ PHẦN 1
print("=" * 72)
print("PHẦN 1: BACKTEST 300 KỲ - TƯ DUY NGƯỢC vs MÔ HÌNH vs NGẪU NHIÊN")
print("=" * 72)

N = 300
ids = [r["id"] for r in p.conn.execute(
    "SELECT id FROM draws ORDER BY id DESC LIMIT ?", (N,)).fetchall()]
ids.reverse()

W_CB = {"decay": 0.30, "mean_rev": 0.25, "freq_30": 0.15,
        "gan": 0.15, "freq_all": 0.05, "pair_bonus": 0.10}

stats = {k: {"hits": [], "dist": {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}}
         for k in ["model", "contrarian", "cold", "anti_hot", "random"]}

for did in ids:
    actual = set(p.conn.execute(
        "SELECT n1,n2,n3,n4,n5,n6 FROM draws WHERE id=?", (did,)).fetchone())
    sig = p.signals(as_of_id=did)
    if sig is None:
        continue

    model_scores = p.score(sig, W_CB)

    # model: điểm cao nhất
    nums = gen_from_scores(model_scores, prefer_high=True)
    stats["model"]["hits"].append(len(set(nums) & actual))
    stats["model"]["dist"][len(set(nums) & actual)] += 1

    # contrarian: điểm THẤP nhất (làm ngược mô hình)
    nums = gen_from_scores(model_scores, prefer_high=False)
    stats["contrarian"]["hits"].append(len(set(nums) & actual))
    stats["contrarian"]["dist"][len(set(nums) & actual)] += 1

    # cold: gan cao + freq_all thấp
    cold_scores = {n: sig["gan"].get(n, 0) * 0.6 + (1 - sig["freq_all"].get(n, 0)) * 0.4
                   for n in range(1, 56)}
    nums = gen_from_scores(cold_scores, prefer_high=True)
    stats["cold"]["hits"].append(len(set(nums) & actual))
    stats["cold"]["dist"][len(set(nums) & actual)] += 1

    # anti_hot: freq_30 thấp nhất
    anti_scores = {n: 1 - sig["freq_30"].get(n, 0) for n in range(1, 56)}
    nums = gen_from_scores(anti_scores, prefer_high=True)
    stats["anti_hot"]["hits"].append(len(set(nums) & actual))
    stats["anti_hot"]["dist"][len(set(nums) & actual)] += 1

    # random
    rnd = set(rng.sample(range(1, 56), 6))
    stats["random"]["hits"].append(len(rnd & actual))
    stats["random"]["dist"][len(rnd & actual)] += 1

labels = {"model": "Mô hình Cân bằng", "contrarian": "NGƯỢC mô hình",
          "cold": "Số lạnh (gan+freq thấp)", "anti_hot": "Ngược số nóng (30 kỳ)",
          "random": "Ngẫu nhiên"}
print(f"\n{'Chiến lược':26s} {'TB số/kỳ':>10s} {'≥2 số':>8s}   Phân phối 0/1/2/3")
for k, v in stats.items():
    n = len(v["hits"])
    avg = sum(v["hits"]) / n
    pct2 = 100 * sum(1 for h in v["hits"] if h >= 2) / n
    dist = " ".join(str(v["dist"].get(h, 0)) for h in range(4))
    print(f"{labels[k]:26s} {avg:10.3f} {pct2:7.1f}%   {dist}")

# sai số chuẩn để biết khác biệt có ý nghĩa không
print("\n(Sai số chuẩn ~0.05 số/kỳ với N=300 -> chênh lệch <0.1 là NHIỄU, không ý nghĩa)")

# ============================================================ PHẦN 2
print("\n" + "=" * 72)
print("PHẦN 2: KIỂM TRA GIẢ THUYẾT 'NHÀ CÁI NÉ SỐ ĐÔNG NGƯỜI CHỌN'")
print("=" * 72)

rows = p.conn.execute("SELECT n1,n2,n3,n4,n5,n6 FROM draws ORDER BY id").fetchall()
all_nums = [tuple(r) for r in rows]
total_draws = len(all_nums)
total_slots = total_draws * 6

# --- 2a. Số 1-31 (ngày sinh) vs 32-55 ---
low = sum(1 for nums in all_nums for n in nums if n <= 31)
high = total_slots - low
exp_low = total_slots * 31 / 55
exp_high = total_slots * 24 / 55
print(f"\n[2a] Số 1-31 (ngày sinh, người chơi hay chọn) vs 32-55:")
print(f"  1-31 : thực tế {low:5d} lần | kỳ vọng {exp_low:7.1f} | lệch {low - exp_low:+.1f}")
print(f"  32-55: thực tế {high:5d} lần | kỳ vọng {exp_high:7.1f} | lệch {high - exp_high:+.1f}")
# kiểm định chi-square
chi2 = (low - exp_low) ** 2 / exp_low + (high - exp_high) ** 2 / exp_high
print(f"  Chi-square = {chi2:.3f} (ngưỡng 3.84 ở mức 5%) -> "
      f"{'CÓ lệch bất thường' if chi2 > 3.84 else 'KHÔNG lệch bất thường'}")

# --- 2b. Số nóng kỳ trước có bị né kỳ sau không? (autocorrelation) ---
# Với mỗi kỳ, đếm số nóng (xuất hiện kỳ trước) có xuất hiện lại kỳ này không
repeat = 0
total_prev = 0
for i in range(1, total_draws):
    prev = set(all_nums[i - 1])
    cur = set(all_nums[i])
    repeat += len(prev & cur)
    total_prev += 6
exp_repeat = total_prev * 6 / 55
print(f"\n[2b] Số vừa ra kỳ trước có xuất hiện lại kỳ sau?")
print(f"  Thực tế {repeat} lần | kỳ vọng {exp_repeat:.1f} | lệch {repeat - exp_repeat:+.1f}")
print(f"  -> {'Số nóng KHÔNG bị né' if abs(repeat - exp_repeat) < 2 * math.sqrt(exp_repeat) else 'Có dấu hiệu bất thường'}")

# --- 2c. Số gan lâu có xuất hiện nhiều hơn không? ---
# Chia số thành 2 nhóm theo gan tại mỗi kỳ, xem nhóm gan cao có về nhiều hơn
print(f"\n[2c] Số gan lâu có 'đến lượt' nhiều hơn không?")
# đơn giản: tương quan giữa gan và lần xuất hiện kế tiếp
gan_high_hits = 0
gan_high_total = 0
gan_low_hits = 0
gan_low_total = 0
for i in range(60, total_draws):
    # tính gan tại kỳ i
    last_seen = {}
    for j in range(i):
        for n in all_nums[j]:
            last_seen[n] = j
    gan = {n: i - last_seen.get(n, -999) for n in range(1, 56)}
    med = sorted(gan.values())[27]
    cur = set(all_nums[i])
    for n in range(1, 56):
        if gan[n] >= med:
            gan_high_total += 1
            if n in cur:
                gan_high_hits += 1
        else:
            gan_low_total += 1
            if n in cur:
                gan_low_hits += 1
print(f"  Nhóm gan CAO: {gan_high_hits}/{gan_high_total} = {100*gan_high_hits/gan_high_total:.2f}%")
print(f"  Nhóm gan THẤP: {gan_low_hits}/{gan_low_total} = {100*gan_low_hits/gan_low_total:.2f}%")
print(f"  Kỳ vọng ngẫu nhiên: {100*6/55:.2f}%")
print(f"  -> {'Số gan KHÔNG có lợi thế' if abs(gan_high_hits/gan_high_total - 6/55) < 0.01 else 'Có khác biệt'}")

p.conn.close()