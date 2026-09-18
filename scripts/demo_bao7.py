# -*- coding: utf-8 -*-
"""
demo_bao7.py - Mô phỏng: nếu chơi Bao 7 ở kỳ 01397, mô hình gợi ý số nào?
Chỉ dùng dữ liệu TRƯỚC kỳ 01397 (as_of_id=1397), rồi đối chiếu kết quả thực.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from predict import Predictor

DB = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "vietlott.db"))
p = Predictor(DB)

# --- kết quả thực kỳ 01397 ---
ACTUAL = [7, 24, 31, 43, 47, 54]
POWER_ACTUAL = 22

# --- tín hiệu trước kỳ 01397 ---
sig = p.signals(as_of_id=1397)

# --- gợi ý 7 số: kết hợp 2 chiến lược, chọn 7 số điểm cao + cấu trúc cân đối ---
weights_cb = {"decay": 0.30, "mean_rev": 0.25, "freq_30": 0.15, "gan": 0.15,
              "freq_all": 0.05, "pair_bonus": 0.10}
weights_ng = {"freq_30": 0.30, "gan": 0.30, "decay": 0.20, "mean_rev": 0.10,
              "freq_all": 0.05, "pair_bonus": 0.05}

def bao7_from(weights, seed_offset=0):
    """Chọn 7 số điểm cao nhất thỏa cấu trúc (lẻ/chẵn 3:4 hoặc 4:3, ≥5 chục, tổng 160-240)."""
    scores = p.score(sig, weights)
    pool = [n for n, _ in sorted(scores.items(), key=lambda x: -x[1])][:35]
    best = None
    rng = __import__("random").Random(42 + seed_offset)
    for _ in range(5000):
        cand = set()
        guard = 0
        while len(cand) < 7 and guard < 200:
            guard += 1
            w = [max(scores[n] + rng.uniform(0, 0.05), 0.0) for n in pool]
            tw = sum(w)
            r = rng.random() * tw
            acc = 0.0
            for n, wi in zip(pool, w):
                acc += wi
                if r <= acc:
                    cand.add(n)
                    break
        if len(cand) < 7:
            continue
        nums = sorted(cand)
        odd = sum(1 for n in nums if n % 2)
        decades = len({(n - 1) // 10 for n in nums})
        s = sum(nums)
        if odd not in (3, 4) or decades < 5 or not (160 <= s <= 240):
            continue
        sc = sum(scores[n] for n in nums)
        if best is None or sc > best[0]:
            best = (sc, nums)
    return best[1] if best else sorted(pool[:7])

def pick_power(exclude):
    cand = [(sig["power_freq"].get(n, 0.0), n) for n in range(1, 56) if n not in exclude]
    cand.sort(reverse=True)
    return __import__("random").Random(7).choice(cand[:12])[1]

def prize_report(bao_nums, power_num, label):
    """Tính giải thưởng nếu chơi Bao 7 với 7 số này ở kỳ 01397."""
    winners = set(ACTUAL)
    k = len(winners & set(bao_nums))
    power_hit = power_num == POWER_ACTUAL
    print(f"\n=== {label} ===")
    print(f"  7 số gợi ý: {' '.join(f'{n:02d}' for n in bao_nums)} + Power {power_num:02d}")
    print(f"  Số trùng với kết quả: {k}/6  ({sorted(winners & set(bao_nums)) or 'không có'})"
          f"  | Power: {'TRÚNG' if power_hit else 'trượt'}")
    # phân tích 7 tổ hợp
    combos = []
    for drop in bao_nums:
        combo = [n for n in bao_nums if n != drop]
        hit = len(set(combo) & winners)
        combos.append((drop, hit))
    from collections import Counter
    dist = Counter(h for _, h in combos)
    print(f"  Phân bố 7 tổ hợp: " + ", ".join(f"{h} số: {dist[h]} tổ hợp" for h in sorted(dist, reverse=True)))
    # giải thưởng
    prize = 0
    detail = []
    for drop, h in combos:
        if h == 6:
            prize += 28_989_675 * 10_000  # Jackpot 1 ~ giá trị cố định ước tính
            detail.append("Jackpot 1")
        elif h == 5:
            if power_hit:
                prize += 3_000_000_000  # Jackpot 2 (ước tính)
                detail.append("Jackpot 2")
            else:
                prize += 40_000_000
                detail.append("Giải Nhất")
        elif h == 4:
            prize += 500_000
            detail.append("Giải Nhì")
        elif h == 3:
            prize += 50_000
            detail.append("Giải Ba")
    if prize == 0:
        print(f"  💸 Kết quả: KHÔNG có giải (chi 70.000đ)")
    else:
        print(f"  🏆 Giải: {', '.join(detail)}")
        print(f"  💰 Tổng thưởng ước tính: {prize:,.0f}đ (chi 70.000đ)")
    return k

print("Kỳ 01397 (12/09/2026) kết quả thực: 07 24 31 43 47 54 + Power 22")
print("=" * 70)

# Gợi ý 1: theo chiến lược Cân bằng
bao1 = bao7_from(weights_cb, 0)
pw1 = pick_power(bao1)
k1 = prize_report(bao1, pw1, "Gợi ý Bao 7 #1 - Chiến lược Cân bằng")

# Gợi ý 2: theo chiến lược Nóng + Gan
bao2 = bao7_from(weights_ng, 1)
pw2 = pick_power(bao2)
k2 = prize_report(bao2, pw2, "Gợi ý Bao 7 #2 - Chiến lược Nóng + Gan")

# So sánh: 2 vé lẻ (12 số) đã mua
old_sets = [5, 8, 9, 22, 33, 41, 18, 29, 38, 39, 44, 45]
k_old = len(set(old_sets) & set(ACTUAL))
print(f"\n=== So sánh: 2 vé lẻ cũ (12 số) ===")
print(f"  12 số: {' '.join(f'{n:02d}' for n in old_sets)}")
print(f"  Số trùng: {k_old}/6 → không có giải (chi 20.000đ)")

# Xác suất có giải của Bao 7 vs 2 vé lẻ
def p_prize_bao7():
    """Xác suất có ít nhất 1 tổ hợp ≥3 số khi chọn 7 số (bao 7)."""
    # P(k trúng trong 7 số) theo hypergeometric
    total = 0.0
    for k in range(3, 8):
        pk = (math.comb(6, k) * math.comb(49, 7 - k)) / math.comb(55, 7)
        # với k trúng trong 7 số, xác suất có tổ hợp ≥3 số = 100% nếu k>=3
        total += pk
    return total

def p_prize_2tickets():
    """Xác suất ít nhất 1 trong 2 vé lẻ có ≥3 số trúng."""
    p3 = sum(math.comb(6, k) * math.comb(49, 6 - k) for k in range(3, 7)) / math.comb(55, 6)
    return 1 - (1 - p3) ** 2

p3_single = sum(math.comb(6, k) * math.comb(49, 6 - k) for k in range(3, 7)) / math.comb(55, 6)

print(f"\n=== Xác suất 'có giải' (≥3 số) ===")
print(f"  1 vé lẻ (10.000đ)      : {100 * p3_single:.2f}%")
print(f"  2 vé lẻ (20.000đ)      : {100 * p_prize_2tickets():.2f}%")
print(f"  Bao 7 (70.000đ)        : {100 * p_prize_bao7():.2f}%")
print(f"  7 vé lẻ khác số (70k)  : {100 * (1 - (1 - p3_single) ** 7):.2f}%")
print(f"\n  Lưu ý: Bao 7 = 7 tổ hợp từ 7 số bạn chọn. Xác suất Jackpot của Bao 7")
print(f"  bằng đúng 7 vé lẻ (7/C(55,6)), nhưng khi trúng thì NHÂN nhiều giải.")

p.conn.close()