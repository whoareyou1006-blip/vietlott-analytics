# -*- coding: utf-8 -*-
"""
predict.py - Engine phân tích & dự đoán Power 6/55 (phiên bản 2).

Bài học từ kỳ 01397 (trượt 0/6):
  - Phân tích 500 kỳ cho thấy thứ hạng tần suất của số trúng phân bố GẦN ĐỀU
    (top10: 20.8% vs ngẫu nhiên 18.2%) -> tín hiệu "số nóng" gần như vô dụng.
  - Mô hình v1 đặt trọng số 30% vào freq_all nên chọn toàn số nóng -> trượt.

Cải thiện v2:
  1. Giảm mạnh trọng số freq_all, tăng tần suất suy giảm theo thời gian (decay)
     và tín hiệu mean-reversion (số "đến lượt" - dưới kỳ vọng gần đây).
  2. Ràng buộc cấu trúc dựa trên thống kê lịch sử:
       - lẻ/chẵn 2:4, 3:3, 4:2 (chiếm 81.9% lịch sử)
       - tổng 6 số trong 106–228 (90% lịch sử), ưu tiên 140–200
       - phủ ít nhất 4 chục khác nhau
       - tối đa 2 số liên tiếp
  3. 2 dãy có hồ sơ cấu trúc KHÁC NHAU (đa dạng hóa).
  4. Backtest 300 kỳ + phân phối đầy đủ số trúng + xác suất thật (hypergeometric).
"""
import json
import math
import os
import random
import sqlite3
from datetime import date

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.normpath(os.path.join(BASE, "..", "data", "vietlott.db"))

DECADES = [(1, 10), (11, 20), (21, 30), (31, 40), (41, 50), (51, 55)]
SUM_LO, SUM_HI = 106, 228   # 90% lịch sử
SUM_TARGET_LO, SUM_TARGET_HI = 140, 200


def hypergeom_pmf(k, n=6, K=6, N=55):
    """Xác suất trúng đúng k số khi chọn n số từ N, có K số trúng."""
    return (math.comb(K, k) * math.comb(N - K, n - k)) / math.comb(N, n)


class Predictor:
    def __init__(self, db_path=DB, seed=42):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.rng = random.Random(seed)
        self._cache = {}

    # ------------------------------------------------------------- signals
    def _pairs(self):
        if "pairs" not in self._cache:
            rows = self.conn.execute("SELECT pair, count FROM pairs").fetchall()
            self._cache["pairs"] = {r["pair"]: r["count"] for r in rows}
        return self._cache["pairs"]

    def _normalize(self, values):
        if not values:
            return {}
        mx = max(values.values())
        mn = min(values.values())
        span = (mx - mn) or 1
        return {k: (v - mn) / span for k, v in values.items()}

    def signals(self, as_of_id=None):
        """Tín hiệu cho 55 số dựa trên dữ liệu TRƯỚC kỳ as_of_id."""
        if as_of_id is not None:
            rows = self.conn.execute(
                "SELECT n1,n2,n3,n4,n5,n6,power,date FROM draws WHERE id < ? ORDER BY id",
                (as_of_id,)).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT n1,n2,n3,n4,n5,n6,power,date FROM draws ORDER BY id").fetchall()

        all_nums = [tuple(r)[:6] for r in rows]
        powers = [r["power"] for r in rows if r["power"]]
        dates = [r["date"] for r in rows]
        total = len(all_nums)
        if total == 0:
            return None

        # --- tần suất all-time ---
        freq_all = {}
        for nums in all_nums:
            for n in nums:
                freq_all[n] = freq_all.get(n, 0) + 1

        # --- tần suất suy giảm theo thời gian (decay): kỳ gần nhất nặng nhất ---
        decay = {}
        for i, nums in enumerate(all_nums):
            w = math.exp(-(total - 1 - i) / 60.0)  # half-life ~42 kỳ
            for n in nums:
                decay[n] = decay.get(n, 0) + w

        # --- tần suất 30 & 90 kỳ ---
        freq_30, freq_90 = {}, {}
        for nums in all_nums[-30:]:
            for n in nums:
                freq_30[n] = freq_30.get(n, 0) + 1
        for nums in all_nums[-90:]:
            for n in nums:
                freq_90[n] = freq_90.get(n, 0) + 1

        # --- số gan (ngày chưa về) ---
        last_date = dates[-1] if dates else None
        last_seen = {}
        for d, nums in zip(dates, all_nums):
            for n in nums:
                last_seen[n] = d
        gan = {}
        if last_date:
            ld = date.fromisoformat(last_date)
            for n in range(1, 56):
                ls = last_seen.get(n)
                gan[n] = (ld - date.fromisoformat(ls)).days if ls else 999

        # --- mean-reversion: số dưới kỳ vọng trong 90 kỳ gần (đang "nợ") ---
        # kỳ vọng mỗi số trong 90 kỳ = 90 * 6 / 55 ≈ 9.8
        expected_90 = 90 * 6 / 55
        mean_rev = {}
        for n in range(1, 56):
            mean_rev[n] = expected_90 - freq_90.get(n, 0)  # dương = đang thiếu

        # --- tần suất số Power ---
        power_freq = {}
        for p in powers:
            power_freq[p] = power_freq.get(p, 0) + 1

        # --- cặp số hay đi cùng ---
        pairs = self._pairs()
        pair_bonus = {}
        for n in range(1, 56):
            b = 0
            for p, c in pairs.items():
                a, b2 = int(p[:2]), int(p[2:])
                if n in (a, b2):
                    b += c
            pair_bonus[n] = b

        return {
            "total_draws": total,
            "last_date": last_date,
            "freq_all": self._normalize(freq_all),
            "decay": self._normalize(decay),
            "freq_30": self._normalize(freq_30),
            "freq_90": self._normalize(freq_90),
            "gan": self._normalize(gan),
            "mean_rev": self._normalize(mean_rev),
            "power_freq": self._normalize(power_freq),
            "pair_bonus": self._normalize(pair_bonus),
            "raw": {
                "freq_all": freq_all, "decay": decay, "freq_30": freq_30,
                "freq_90": freq_90, "gan": gan, "mean_rev": mean_rev,
                "power_freq": power_freq, "pair_bonus": pair_bonus,
            },
        }

    # ------------------------------------------------------------- scoring
    def score(self, sig, weights):
        scores = {}
        for n in range(1, 56):
            s = 0.0
            for k, w in weights.items():
                s += w * sig[k].get(n, 0.0)
            scores[n] = s
        return scores

    def _pick_power(self, sig, exclude):
        cand = [(sig["power_freq"].get(n, 0.0), n) for n in range(1, 56) if n not in exclude]
        cand.sort(reverse=True)
        top = cand[:12]
        return self.rng.choice(top)[1]

    # ----------------------------------------------------- structural checks
    def _odd_even_ok(self, nums, target):
        odd = sum(1 for n in nums if n % 2)
        return odd in target

    def _sum_ok(self, nums, lo=SUM_LO, hi=SUM_HI):
        return lo <= sum(nums) <= hi

    def _decade_ok(self, nums, min_decades=4):
        covered = set()
        for n in nums:
            for i, (lo, hi) in enumerate(DECADES):
                if lo <= n <= hi:
                    covered.add(i)
        return len(covered) >= min_decades

    def _consecutive_ok(self, nums, max_run=2):
        s = sorted(nums)
        run = 1
        for i in range(1, len(s)):
            run = run + 1 if s[i] == s[i - 1] + 1 else 1
            if run > max_run:
                return False
        return True

    def _structure_ok(self, nums, profile):
        return (self._odd_even_ok(nums, profile["odd_even"])
                and self._sum_ok(nums, profile["sum_lo"], profile["sum_hi"])
                and self._decade_ok(nums, profile["min_decades"])
                and self._consecutive_ok(nums, profile["max_consecutive"]))

    # ------------------------------------------------------------- generate
    def generate(self, sig, weights, profile, n_sets=1, exclude=None, noise=0.0):
        """
        Sinh dãy số thỏa ràng buộc cấu trúc bằng Monte Carlo:
        lấy mẫu có trọng số từ pool 30 số điểm cao nhất, lọc theo cấu trúc,
        giữ bộ có tổng điểm cao nhất.
        """
        exclude = set(exclude or [])
        scores = self.score(sig, weights)
        pool = [n for n, _ in sorted(scores.items(), key=lambda x: -x[1])
                if n not in exclude][:30]
        results = []
        for _ in range(n_sets):
            best = None
            for _ in range(3000):
                cand = set()
                guard = 0
                while len(cand) < 6 and guard < 100:
                    guard += 1
                    w = [max(scores[n] + self.rng.uniform(0, noise), 0.0) for n in pool]
                    tw = sum(w)
                    if tw <= 0:
                        break
                    r = self.rng.random() * tw
                    acc = 0.0
                    for n, wi in zip(pool, w):
                        acc += wi
                        if r <= acc:
                            cand.add(n)
                            break
                if len(cand) < 6:
                    continue
                nums = sorted(cand)
                if not self._structure_ok(nums, profile):
                    continue
                sc = sum(scores[n] for n in nums)
                if best is None or sc > best[0]:
                    best = (sc, nums)
            if best is None:
                # fallback: chọn 6 số điểm cao nhất (không ràng buộc)
                nums = sorted(pool[:6])
            else:
                nums = best[1]
            power = self._pick_power(sig, nums)
            results.append({"numbers": nums, "power": power})
        return results

    # ------------------------------------------------------------- strategies
    def strategies(self):
        return {
            "can_bang": {
                "label": "Chiến lược Cân bằng",
                "desc": "Tần suất suy giảm + mean-reversion, cấu trúc 3 lẻ/3 chẵn, tổng quanh 170",
                "weights": {
                    "decay": 0.30, "mean_rev": 0.25, "freq_30": 0.15,
                    "gan": 0.15, "freq_all": 0.05, "pair_bonus": 0.10,
                },
                "profile": {"odd_even": [3], "sum_lo": 140, "sum_hi": 200,
                            "min_decades": 4, "max_consecutive": 2},
                "noise": 0.0,
            },
            "nong_gan": {
                "label": "Chiến lược Nóng + Gan",
                "desc": "Nhấn số đang nóng gần đây + số gan, cấu trúc 4 lẻ/2 chẵn, tổng cao",
                "weights": {
                    "freq_30": 0.30, "gan": 0.30, "decay": 0.20,
                    "mean_rev": 0.10, "freq_all": 0.05, "pair_bonus": 0.05,
                },
                "profile": {"odd_even": [4, 2], "sum_lo": 150, "sum_hi": 220,
                            "min_decades": 4, "max_consecutive": 2},
                "noise": 0.0,
            },
        }

    def predict(self, as_of_id=None):
        sig = self.signals(as_of_id)
        if sig is None:
            return None
        out = {"as_of": sig["last_date"], "total_draws": sig["total_draws"],
               "sets": [], "signals": {}}
        chosen_all = set()
        for key, st in self.strategies().items():
            sets = self.generate(sig, st["weights"], st["profile"], n_sets=1,
                                 exclude=chosen_all, noise=st["noise"])
            nums = sets[0]["numbers"]
            chosen_all.update(nums)
            out["sets"].append({
                "strategy": key,
                "label": st["label"],
                "desc": st["desc"],
                "numbers": nums,
                "power": sets[0]["power"],
                "structure": {
                    "odd_even": f"{sum(1 for n in nums if n % 2)}:{6 - sum(1 for n in nums if n % 2)}",
                    "sum": sum(nums),
                    "decades": len({(n - 1) // 10 for n in nums}),
                },
            })
        out["signals"] = {
            "freq_all": sig["raw"]["freq_all"],
            "freq_30": sig["raw"]["freq_30"],
            "freq_90": sig["raw"]["freq_90"],
            "gan": sig["raw"]["gan"],
            "power_freq": sig["raw"]["power_freq"],
            "mean_rev": sig["raw"]["mean_rev"],
        }
        return out

    # ------------------------------------------------------------- backtest
    def backtest(self, n_draws=300):
        """
        Walk-forward: dự đoán chỉ dùng dữ liệu trước kỳ đó.
        So sánh: 2 chiến lược + ngẫu nhiên thuần + ngẫu nhiên có cấu trúc.
        """
        ids = [r["id"] for r in self.conn.execute(
            "SELECT id FROM draws ORDER BY id DESC LIMIT ?", (n_draws,)).fetchall()]
        ids.reverse()
        stats = {k: {"hits": [], "avg": 0.0, "pct_2plus": 0.0, "dist": {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}}
                 for k in list(self.strategies()) + ["random", "random_struct"]}

        for did in ids:
            actual = self.conn.execute(
                "SELECT n1,n2,n3,n4,n5,n6 FROM draws WHERE id=?", (did,)).fetchone()
            actual_set = set(actual)
            sig = self.signals(as_of_id=did)
            if sig is None:
                continue
            chosen_all = set()
            for key, st in self.strategies().items():
                sets = self.generate(sig, st["weights"], st["profile"], n_sets=1,
                                     exclude=chosen_all, noise=st["noise"])
                nums = sets[0]["numbers"]
                chosen_all.update(nums)
                hit = len(set(nums) & actual_set)
                stats[key]["hits"].append(hit)
                stats[key]["dist"][hit] = stats[key]["dist"].get(hit, 0) + 1
            # ngẫu nhiên thuần
            rnd = set(self.rng.sample(range(1, 56), 6))
            hit = len(rnd & actual_set)
            stats["random"]["hits"].append(hit)
            stats["random"]["dist"][hit] = stats["random"]["dist"].get(hit, 0) + 1
            # ngẫu nhiên có cấu trúc (3:3, tổng 140-200, 4 chục)
            for _ in range(200):
                cand = set(self.rng.sample(range(1, 56), 6))
                odd = sum(1 for n in cand if n % 2)
                if odd == 3 and 140 <= sum(cand) <= 200 and \
                        len({(n - 1) // 10 for n in cand}) >= 4:
                    break
            hit = len(cand & actual_set)
            stats["random_struct"]["hits"].append(hit)
            stats["random_struct"]["dist"][hit] = stats["random_struct"]["dist"].get(hit, 0) + 1

        for k, v in stats.items():
            n = len(v["hits"])
            v["avg"] = round(sum(v["hits"]) / n, 3) if n else 0
            v["pct_2plus"] = round(100 * sum(1 for h in v["hits"] if h >= 2) / n, 1) if n else 0
        return stats

    def true_probabilities(self):
        """Xác suất thật (hypergeometric) cho 1 vé 6/55."""
        return {k: round(hypergeom_pmf(k) * 100, 4) for k in range(0, 7)}


def main():
    p = Predictor()
    latest = p.conn.execute("SELECT MAX(id), MAX(date) FROM draws").fetchone()
    print("=" * 66)
    print(f"DỰ ĐOÁN POWER 6/55 v2 - dữ liệu đến kỳ {latest[0]:05d} ({latest[1]})")
    print("=" * 66)
    pred = p.predict()
    for s in pred["sets"]:
        nums = " ".join(f"{n:02d}" for n in s["numbers"])
        st = s["structure"]
        print(f"\n[{s['label']}]")
        print(f"  Dãy số : {nums}  + Power {s['power']:02d}")
        print(f"  Cấu trúc: lẻ/chẵn {st['odd_even']} | tổng {st['sum']} | "
              f"{st['decades']} chục | {s['desc']}")

    print("\n" + "=" * 66)
    print("BACKTEST 300 kỳ gần nhất (dự đoán chỉ dùng dữ liệu quá khứ)")
    print("=" * 66)
    stats = p.backtest(300)
    labels = {"can_bang": "Cân bằng", "nong_gan": "Nóng+Gan",
              "random": "Ngẫu nhiên", "random_struct": "Ngẫu nhiên + cấu trúc"}
    for k, v in stats.items():
        dist = " ".join(f"{h}:{v['dist'].get(h, 0)}" for h in range(0, 4))
        print(f"  {labels[k]:22s}: TB {v['avg']:.3f} số/kỳ | ≥2 số: {v['pct_2plus']:5.1f}% | "
              f"phân phối (0,1,2,3): {dist}")

    print("\n" + "=" * 66)
    print("XÁC SUẤT THẬT 1 VÉ 6/55 (hypergeometric)")
    print("=" * 66)
    for k, v in p.true_probabilities().items():
        tier = {0: "0 số", 1: "1 số", 2: "2 số", 3: "3 số (Giải Ba)", 4: "4 số (Giải Nhì)",
                5: "5 số (Giải Nhất)", 6: "6 số (Jackpot 1)"}[k]
        odds = 1 / (v / 100) if v > 0 else float("inf")
        odds_str = f"1/{odds:,.0f}" if odds < 1e15 else "1/28,989,675"
        print(f"  {tier:22s}: {v:10.6f}%  ({odds_str})")
    p.conn.close()


if __name__ == "__main__":
    main()