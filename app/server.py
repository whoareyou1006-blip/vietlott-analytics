# -*- coding: utf-8 -*-
"""
server.py - Web app Vietlott 6/55 Analytics & Prediction (v3).

Chạy:  python server.py [port]
Mặc định: http://localhost:8000

API:
  /api/stats            - tổng quan
  /api/draws?limit=N    - kỳ quay gần nhất
  /api/frequency?scope= - tần suất (all_time|last_30|last_60|last_90|power)
  /api/gan              - số lâu chưa về
  /api/predict          - 2 dãy số dự đoán (thống kê)
  /api/backtest         - kết quả kiểm chứng
  /api/probabilities    - xác suất thật
  /api/jackpots         - lịch sử jackpot
  /api/pairs            - cặp số hay về cùng
  /api/sources          - thông tin 4 nguồn dữ liệu

  POST /api/update      - cập nhật kết quả kỳ quay mới nhất (nền)
  GET  /api/update/status - trạng thái cập nhật + dự đoán tự động
  GET  /api/ai/config   - cấu hình AI (che API key)
  POST /api/ai/config   - lưu cấu hình AI
  POST /api/ai/check    - kiểm tra kết nối API
  POST /api/ai/predict  - dự đoán bằng AI

Tự động: mỗi 30 phút kiểm tra kỳ quay mới; khi có kỳ mới -> cập nhật DB
và tự chạy dự đoán (thống kê + AI nếu đã cấu hình).
"""
import json
import os
import sqlite3
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
DB = os.path.normpath(os.path.join(ROOT, "data", "vietlott.db"))
STATIC = os.path.join(BASE, "static")

sys.path.insert(0, os.path.join(ROOT, "scripts"))
from predict import Predictor  # noqa: E402
import ai_provider  # noqa: E402
import auto_update  # noqa: E402

_predictor = None
_predictor_lock = threading.Lock()

# trạng thái cập nhật & dự đoán tự động
_update_state = {
    "running": False,
    "last_run": None,
    "last_result": None,
    "auto_predict": None,   # dự đoán thống kê sau khi cập nhật
    "auto_ai_predict": None,  # dự đoán AI sau khi cập nhật
}
_update_lock = threading.Lock()


def get_predictor():
    global _predictor
    with _predictor_lock:
        if _predictor is None:
            _predictor = Predictor(DB)
        return _predictor


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


# ------------------------------------------------------------- API cũ
def api_stats():
    conn = db()
    total = conn.execute("SELECT COUNT(*) FROM draws").fetchone()[0]
    first, last = conn.execute("SELECT MIN(date), MAX(date) FROM draws").fetchone()
    with_jp = conn.execute("SELECT COUNT(*) FROM draws WHERE jackpot1 IS NOT NULL").fetchone()[0]
    max_jp = conn.execute("SELECT MAX(jackpot1) FROM draws").fetchone()[0]
    sources = [dict(r) for r in conn.execute("SELECT name, draws_count, notes FROM sources")]
    conn.close()
    return {
        "total_draws": total, "first_date": first, "last_date": last,
        "draws_with_jackpot": with_jp, "max_jackpot": max_jp, "sources": sources,
    }


def api_draws(limit=20):
    conn = db()
    rows = conn.execute(
        "SELECT draw_code, date, n1,n2,n3,n4,n5,n6, power, jackpot1, jackpot2, source "
        "FROM draws ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def api_frequency(scope="all_time"):
    conn = db()
    rows = conn.execute(
        "SELECT number, count FROM frequency WHERE source='derived' AND scope=? "
        "ORDER BY number", (scope,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def api_gan():
    conn = db()
    rows = conn.execute(
        "SELECT number, count AS days FROM frequency WHERE source='derived' "
        "AND scope='gan_days' ORDER BY count DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def api_predict():
    p = get_predictor()
    with _predictor_lock:
        return p.predict()


def api_backtest(n=100):
    p = get_predictor()
    with _predictor_lock:
        return p.backtest(n)


def api_probabilities():
    p = get_predictor()
    return p.true_probabilities()


def api_jackpots():
    conn = db()
    rows = conn.execute(
        "SELECT rank, jackpot, date FROM jackpot_history ORDER BY rank").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def api_pairs():
    conn = db()
    rows = conn.execute("SELECT pair, count FROM pairs ORDER BY count DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def api_sources():
    conn = db()
    rows = conn.execute("SELECT name, fetched_at, draws_count, notes FROM sources").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ------------------------------------------------------------- AI context
def build_ai_context():
    """Bối cảnh thống kê cho AI: kỳ gần, top số, cấu trúc."""
    conn = db()
    recent = conn.execute(
        "SELECT draw_code, date, n1,n2,n3,n4,n5,n6, power FROM draws "
        "ORDER BY id DESC LIMIT 10").fetchall()
    recent_draws = [{
        "draw_code": r["draw_code"], "date": r["date"],
        "numbers": [r["n1"], r["n2"], r["n3"], r["n4"], r["n5"], r["n6"]],
        "power": r["power"],
    } for r in recent]

    def top(scope, limit):
        rows = conn.execute(
            "SELECT number, count FROM frequency WHERE source='derived' AND scope=? "
            "ORDER BY count DESC LIMIT ?", (scope, limit)).fetchall()
        return [(r["number"], r["count"]) for r in rows]

    # cấu trúc 300 kỳ gần
    rows = conn.execute(
        "SELECT n1,n2,n3,n4,n5,n6 FROM draws ORDER BY id DESC LIMIT 300").fetchall()
    odd_even = {"3:3": 0, "2:4": 0, "4:2": 0, "other": 0}
    sums, decades_ok = [], 0
    for r in rows:
        nums = [r["n1"], r["n2"], r["n3"], r["n4"], r["n5"], r["n6"]]
        odd = sum(1 for n in nums if n % 2)
        key = f"{odd}:{6 - odd}" if odd in (2, 3, 4) else "other"
        odd_even[key] = odd_even.get(key, 0) + 1
        sums.append(sum(nums))
        if len({(n - 1) // 10 for n in nums}) >= 4:
            decades_ok += 1
    n = len(rows) or 1
    sums.sort()
    result = {
        "total_draws": auto_update.get_latest()["id"],
        "last_date": auto_update.get_latest()["date"],
        "recent_draws": recent_draws,
        "top_all": top("all_time", 10),
        "top_30": top("last_30", 10),
        "top_gan": top("gan_days", 10),
        "top_power": top("power", 8),
        "odd_even": {k: 100 * v / n for k, v in odd_even.items()},
        "sum_avg": round(sum(sums) / n),
        "sum_lo": sums[int(0.05 * n)] if n > 1 else 106,
        "sum_hi": sums[int(0.95 * n) - 1] if n > 1 else 228,
        "decade_pct": 100 * decades_ok / n,
    }
    conn.close()
    return result


# ------------------------------------------------------------- API mới
def api_update():
    """Kích hoạt cập nhật kỳ quay mới nhất (chạy nền)."""
    with _update_lock:
        if _update_state["running"]:
            return {"ok": False, "message": "Đang có một lần cập nhật chạy..."}
        _update_state["running"] = True

    def worker():
        result = auto_update.run_update()
        with _update_lock:
            _update_state["running"] = False
            _update_state["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
            _update_state["last_result"] = result
            if result.get("new_draw"):
                # tự chạy dự đoán thống kê
                try:
                    _update_state["auto_predict"] = api_predict()
                except Exception as e:
                    _update_state["auto_predict"] = {"error": str(e)}
                # tự chạy dự đoán AI nếu đã cấu hình
                try:
                    cfg = ai_provider.load_config()
                    if cfg.get("api_key") or cfg.get("provider") == "ollama":
                        _update_state["auto_ai_predict"] = ai_provider.ai_predict(
                            cfg, build_ai_context())
                    else:
                        _update_state["auto_ai_predict"] = {
                            "ok": False, "message": "Chưa cấu hình AI (vào tab AI Dự đoán)"}
                except Exception as e:
                    _update_state["auto_ai_predict"] = {"ok": False, "message": str(e)}

    threading.Thread(target=worker, daemon=True).start()
    return {"ok": True, "message": "Đã bắt đầu cập nhật (chạy nền, vài phút)..."}


def api_update_status():
    with _update_lock:
        return {
            "running": _update_state["running"],
            "last_run": _update_state["last_run"],
            "last_result": _update_state["last_result"],
            "auto_predict": _update_state["auto_predict"],
            "auto_ai_predict": _update_state["auto_ai_predict"],
        }


def api_ai_config_get():
    return ai_provider.masked_config(ai_provider.load_config())


def api_ai_config_post(body):
    cfg = ai_provider.load_config()
    if "provider" in body:
        cfg["provider"] = body["provider"]
    if "api_key" in body:
        cfg["api_key"] = body["api_key"].strip()
    if "base_url" in body:
        cfg["base_url"] = body["base_url"].strip()
    if "model" in body:
        cfg["model"] = body["model"].strip()
    ai_provider.save_config(cfg)
    return {"ok": True, "config": ai_provider.masked_config(cfg)}


def api_ai_check(body):
    cfg = ai_provider.load_config()
    if "provider" in body:
        cfg["provider"] = body["provider"]
    if "api_key" in body and body["api_key"]:
        cfg["api_key"] = body["api_key"].strip()
    if "base_url" in body and body["base_url"]:
        cfg["base_url"] = body["base_url"].strip()
    if "model" in body and body["model"]:
        cfg["model"] = body["model"].strip()
    ok, msg = ai_provider.check_connection(cfg)
    return {"ok": ok, "message": msg}


def api_ai_models(body):
    cfg = ai_provider.load_config()
    if "provider" in body:
        cfg["provider"] = body["provider"]
    if "api_key" in body and body["api_key"]:
        cfg["api_key"] = body["api_key"].strip()
    if "base_url" in body and body["base_url"]:
        cfg["base_url"] = body["base_url"].strip()
    return ai_provider.list_models(cfg)


def api_ai_predict(body):
    cfg = ai_provider.load_config()
    if "provider" in body:
        cfg["provider"] = body["provider"]
    if "api_key" in body and body["api_key"]:
        cfg["api_key"] = body["api_key"].strip()
    if "base_url" in body and body["base_url"]:
        cfg["base_url"] = body["base_url"].strip()
    if "model" in body and body["model"]:
        cfg["model"] = body["model"].strip()
    context = build_ai_context()
    result = ai_provider.ai_predict(cfg, context)
    if result.get("ok"):
        with _update_lock:
            _update_state["auto_ai_predict"] = result
    return result


# ------------------------------------------------------------- routes
ROUTES = {
    "/api/stats": (api_stats, False),
    "/api/draws": (api_draws, True),
    "/api/frequency": (api_frequency, True),
    "/api/gan": (api_gan, False),
    "/api/predict": (api_predict, False),
    "/api/backtest": (api_backtest, True),
    "/api/probabilities": (api_probabilities, False),
    "/api/jackpots": (api_jackpots, False),
    "/api/pairs": (api_pairs, False),
    "/api/sources": (api_sources, False),
    "/api/update/status": (api_update_status, False),
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # im lặng log

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path):
        try:
            with open(path, "rb") as f:
                body = f.read()
        except OSError:
            self.send_error(404)
            return
        ext = os.path.splitext(path)[1]
        ctype = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".svg": "image/svg+xml",
            ".png": "image/png",
        }.get(ext, "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        q = parse_qs(parsed.query)
        if path in ROUTES:
            try:
                fn, needs_q = ROUTES[path]
                if needs_q:
                    if path == "/api/draws":
                        result = fn(int(q.get("limit", ["20"])[0]))
                    elif path == "/api/frequency":
                        result = fn(q.get("scope", ["all_time"])[0])
                    elif path == "/api/backtest":
                        result = fn(int(q.get("n", ["100"])[0]))
                    else:
                        result = fn(q)
                else:
                    result = fn()
                self._send_json(result)
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
            return
        if path == "/api/ai/config":
            self._send_json(api_ai_config_get())
            return
        if path == "/" or path == "/index.html":
            self._send_file(os.path.join(STATIC, "index.html"))
            return
        safe = os.path.normpath(os.path.join(STATIC, path.lstrip("/")))
        if safe.startswith(STATIC) and os.path.isfile(safe):
            self._send_file(safe)
        else:
            self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read_body()
        try:
            if path == "/api/update":
                result = api_update()
            elif path == "/api/ai/config":
                result = api_ai_config_post(body)
            elif path == "/api/ai/check":
                result = api_ai_check(body)
            elif path == "/api/ai/models":
                result = api_ai_models(body)
            elif path == "/api/ai/predict":
                result = api_ai_predict(body)
            else:
                self.send_error(404)
                return
            self._send_json(result)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)


# ------------------------------------------------------------- auto-update
def auto_update_loop():
    """Kiểm tra kỳ quay mới mỗi 30 phút; khi có kỳ mới -> cập nhật + dự đoán."""
    while True:
        try:
            with _update_lock:
                running = _update_state["running"]
            if not running:
                api_update()
        except Exception:
            pass
        time.sleep(1800)  # 30 phút


def main():
    port = int(os.environ.get("PORT") or (sys.argv[1] if len(sys.argv) > 1 else 8000))
    host = os.environ.get("HOST", "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1")
    threading.Thread(target=auto_update_loop, daemon=True).start()
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Vietlott 6/55 Analytics v4: http://{host}:{port}")
    print("Tự cập nhật kỳ quay mới: mỗi 30 phút. Nhấn Ctrl+C để dừng.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã dừng.")


if __name__ == "__main__":
    main()