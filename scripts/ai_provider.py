# -*- coding: utf-8 -*-
"""
ai_provider.py - AI Mode: dự đoán 2 dãy số bằng Gemini / OpenAI / Ollama.

- Cấu hình (provider, api_key, base_url, model) lưu tại data/ai_config.json
  (file cục bộ, không commit - chứa API key).
- check_connection(): kiểm tra API có hoạt động không.
- ai_predict(): gửi bối cảnh thống kê + yêu cầu AI chọn 2 dãy số, parse JSON.
"""
import json
import os
import re
import urllib.error
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.normpath(os.path.join(BASE, "..", "data", "ai_config.json"))

DEFAULTS = {
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "model": "gemini-1.5-flash",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
    },
    "ollama": {
        "base_url": "https://ollama.com",  # Ollama Cloud
        "model": "llama3.1",
    },
}

PROVIDER_LABELS = {
    "gemini": "Google Gemini",
    "openai": "OpenAI",
    "ollama": "Ollama (Cloud / local)",
}


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"provider": "ollama", "api_key": "", "base_url": "", "model": ""}


def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return cfg


def effective(cfg):
    """Điền giá trị mặc định cho base_url/model theo provider."""
    provider = cfg.get("provider", "ollama")
    if provider == "ollama-local":  # tương thích lựa chọn "Ollama local" từ UI
        provider = "ollama"
    d = DEFAULTS.get(provider, {})
    out = dict(cfg)
    out["provider"] = provider
    out["base_url"] = (cfg.get("base_url") or d.get("base_url", "")).rstrip("/")
    out["model"] = cfg.get("model") or d.get("model", "")
    return out


def masked_config(cfg):
    """Trả về cấu hình an toàn (che API key) cho frontend."""
    out = dict(cfg)
    key = out.get("api_key", "")
    out["api_key"] = (key[:4] + "••••" + key[-4:]) if len(key) > 8 else ("••••" if key else "")
    out["has_key"] = bool(key)
    return out


def http_json(url, method="GET", payload=None, headers=None, timeout=90):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("User-Agent", "Vietlott-Analytics/1.0")
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def check_connection(cfg):
    """Kiểm tra API có hoạt động không. Trả về (ok: bool, message: str)."""
    cfg = effective(cfg)
    provider = cfg["provider"]
    try:
        if provider == "gemini":
            if not cfg["api_key"]:
                return False, "Thiếu API key Gemini"
            data = http_json(f"{cfg['base_url']}/models?key={cfg['api_key']}")
            models = [m.get("name", "") for m in data.get("models", [])]
            found = any(cfg["model"] in n for n in models)
            msg = f"Kết nối Gemini OK ({len(models)} model khả dụng)"
            if not found:
                msg += f" — lưu ý: model '{cfg['model']}' không thấy trong danh sách"
            return True, msg
        if provider == "openai":
            if not cfg["api_key"]:
                return False, "Thiếu API key OpenAI"
            data = http_json(f"{cfg['base_url']}/models",
                             headers={"Authorization": f"Bearer {cfg['api_key']}"})
            n = len(data.get("data", []))
            return True, f"Kết nối OpenAI OK ({n} model khả dụng)"
        if provider == "ollama":
            headers = {}
            if cfg.get("api_key"):
                headers["Authorization"] = f"Bearer {cfg['api_key']}"
            data = http_json(f"{cfg['base_url']}/api/tags", headers=headers)
            models = [m.get("name", "") for m in data.get("models", [])]
            if not models:
                return True, "Kết nối Ollama OK (chưa có model nào được pull)"
            return True, f"Kết nối Ollama OK ({len(models)} model: {', '.join(models[:4])})"
    except urllib.error.HTTPError as e:
        return False, f"Lỗi HTTP {e.code}: {e.reason}"
    except Exception as e:
        return False, f"Lỗi kết nối: {e}"
    return False, "Provider không được hỗ trợ"


def list_models(cfg):
    """Lấy danh sách model khả dụng từ API. Trả về dict kết quả."""
    cfg = effective(cfg)
    provider = cfg["provider"]
    try:
        if provider == "gemini":
            if not cfg["api_key"]:
                return {"ok": False, "message": "Thiếu API key Gemini"}
            data = http_json(f"{cfg['base_url']}/models?key={cfg['api_key']}")
            models = sorted({m.get("name", "").split("/")[-1]
                             for m in data.get("models", []) if m.get("name")})
            return {"ok": True, "models": models}
        if provider == "openai":
            if not cfg["api_key"]:
                return {"ok": False, "message": "Thiếu API key OpenAI"}
            data = http_json(f"{cfg['base_url']}/models",
                             headers={"Authorization": f"Bearer {cfg['api_key']}"})
            models = sorted({m.get("id", "") for m in data.get("data", []) if m.get("id")})
            return {"ok": True, "models": models}
        if provider == "ollama":
            headers = {}
            if cfg.get("api_key"):
                headers["Authorization"] = f"Bearer {cfg['api_key']}"
            data = http_json(f"{cfg['base_url']}/api/tags", headers=headers)
            models = sorted({m.get("name", "") for m in data.get("models", []) if m.get("name")})
            return {"ok": True, "models": models}
    except urllib.error.HTTPError as e:
        return {"ok": False, "message": f"Lỗi HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"ok": False, "message": f"Lỗi kết nối: {e}"}
    return {"ok": False, "message": "Provider không được hỗ trợ"}


# ------------------------------------------------------------- prompt
def build_prompt(context):
    """Tạo prompt cho AI từ bối cảnh thống kê."""
    lines = []
    lines.append("Bạn là chuyên gia phân tích xổ số Vietlott Power 6/55 (quay 6 số từ 01-55 + 1 số Power từ 01-55).")
    lines.append("Dưới đây là dữ liệu thống kê thực tế từ các kỳ quay đã qua.")
    lines.append("")
    lines.append(f"Tổng số kỳ đã quay: {context['total_draws']} (đến {context['last_date']})")
    lines.append("")
    lines.append("10 kỳ quay gần nhất (số chính + Power):")
    for d in context["recent_draws"]:
        nums = " ".join(f"{n:02d}" for n in d["numbers"])
        lines.append(f"  Kỳ {d['draw_code']} ({d['date']}): {nums} + Power {d['power']:02d}")
    lines.append("")
    lines.append("Top 10 số xuất hiện nhiều nhất (toàn bộ lịch sử):")
    lines.append("  " + ", ".join(f"{n:02d}({c})" for n, c in context["top_all"]))
    lines.append("Top 10 số nóng nhất (30 kỳ gần):")
    lines.append("  " + ", ".join(f"{n:02d}({c})" for n, c in context["top_30"]))
    lines.append("Top 10 số gan nhất (lâu chưa về, đơn vị ngày):")
    lines.append("  " + ", ".join(f"{n:02d}({c} ngày)" for n, c in context["top_gan"]))
    lines.append("Top 8 số Power xuất hiện nhiều nhất:")
    lines.append("  " + ", ".join(f"{n:02d}({c})" for n, c in context["top_power"]))
    lines.append("")
    lines.append("Thống kê cấu trúc của các kỳ quay thực tế (300 kỳ gần):")
    lines.append(f"  - Lẻ/chẵn: 3:3 chiếm {context['odd_even']['3:3']:.1f}%, "
                 f"2:4 chiếm {context['odd_even']['2:4']:.1f}%, "
                 f"4:2 chiếm {context['odd_even']['4:2']:.1f}%")
    lines.append(f"  - Tổng 6 số: trung bình {context['sum_avg']}, 90% kỳ nằm trong {context['sum_lo']}-{context['sum_hi']}")
    lines.append(f"  - Số chục khác nhau: ≥4 chục chiếm {context['decade_pct']:.1f}% kỳ")
    lines.append("")
    lines.append("NHIỆM VỤ: Chọn 2 dãy số cho kỳ quay TIẾP THEO.")
    lines.append("Yêu cầu bắt buộc:")
    lines.append("  1. Mỗi dãy gồm 6 số chính (01-55, không trùng nhau) + 1 số Power (01-55).")
    lines.append("  2. Hai dãy KHÔNG được trùng số chính nào với nhau.")
    lines.append("  3. Cấu trúc mỗi dãy phải giống kỳ quay thực tế: lẻ/chẵn 2:4, 3:3 hoặc 4:2;")
    lines.append("     tổng 6 số trong khoảng 106-228; phủ ít nhất 4 chục; tối đa 2 số liên tiếp.")
    lines.append("  4. Cân nhắc kết hợp: số nóng gần đây, số gan lâu ngày, số có tần suất tốt.")
    lines.append("  5. Trả về DUY NHẤT JSON đúng định dạng sau (không thêm chữ ngoài):")
    lines.append('  {"sets":[{"numbers":[a,b,c,d,e,f],"power":p,"reason":"ngắn gọn"},'
                 '{"numbers":[a,b,c,d,e,f],"power":p,"reason":"ngắn gọn"}]}')
    lines.append("  6. Số viết dạng số nguyên KHÔNG có số 0 ở đầu (vd 8 thay vì 08).")
    return "\n".join(lines)


# ------------------------------------------------------------- call AI
def _fix_leading_zeros(text):
    """JSON không cho phép số có số 0 ở đầu (vd 08) — sửa thành 8."""
    return re.sub(r"(?<![.\d])0(\d+)", r"\1", text)


def _extract_json(text):
    """Trích JSON từ phản hồi AI (bọc ```json, thừa chữ, số 0 đầu, list trần)."""
    if not text:
        return None
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if m:
        text = m.group(1)
    candidates = []
    if text[:1] in ("{", "["):
        candidates.append(text)
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start:end + 1])
    for c in candidates:
        for attempt in (c, _fix_leading_zeros(c)):
            try:
                data = json.loads(attempt)
                if isinstance(data, list):  # AI trả list trần [{...},{...}]
                    data = {"sets": data}
                return data
            except Exception:
                continue
    return None


def _to_int(v):
    """Chuyển số từ AI về int: chấp nhận int, float nguyên, chuỗi '08'/'8.0'."""
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v) if v.is_integer() else None
    if isinstance(v, str):
        s = v.strip()
        try:
            return int(s)
        except ValueError:
            try:
                f = float(s)
                return int(f) if f.is_integer() else None
            except ValueError:
                return None
    return None


def _validate_sets(data):
    """Kiểm tra & chuẩn hóa 2 dãy số từ AI. Trả về list hoặc None."""
    if not isinstance(data, dict):
        return None
    sets = data.get("sets")
    if not isinstance(sets, list) or len(sets) < 2:
        return None
    out = []
    used = set()
    for s in sets[:2]:
        nums = s.get("numbers")
        power = _to_int(s.get("power"))
        if not isinstance(nums, list) or len(nums) != 6 or power is None:
            return None
        nums = [_to_int(n) for n in nums]
        if any(n is None for n in nums):
            return None
        if any(n < 1 or n > 55 for n in nums) or power < 1 or power > 55:
            return None
        if len(set(nums)) != 6:
            return None
        if set(nums) & used:
            return None
        used.update(nums)
        out.append({"numbers": sorted(nums), "power": power,
                    "reason": str(s.get("reason", ""))[:200]})
    return out


def _parse_sets(text):
    parsed = _extract_json(text)
    return _validate_sets(parsed) if parsed else None


def _call_api(cfg, prompt):
    """Gọi API theo provider, trả về text phản hồi. Raise exception khi lỗi."""
    provider = cfg["provider"]
    if provider == "gemini":
        if not cfg["api_key"]:
            raise ValueError("Thiếu API key Gemini")
        url = f"{cfg['base_url']}/models/{cfg['model']}:generateContent?key={cfg['api_key']}"
        payload = {"contents": [{"parts": [{"text": prompt}]}],
                   "generationConfig": {"temperature": 0.9, "maxOutputTokens": 1024}}
        data = http_json(url, method="POST", payload=payload)
        return data["candidates"][0]["content"]["parts"][0]["text"]
    if provider == "openai":
        if not cfg["api_key"]:
            raise ValueError("Thiếu API key OpenAI")
        url = f"{cfg['base_url']}/chat/completions"
        payload = {"model": cfg["model"],
                   "messages": [{"role": "user", "content": prompt}],
                   "temperature": 0.9, "max_tokens": 1024}
        data = http_json(url, method="POST", payload=payload,
                         headers={"Authorization": f"Bearer {cfg['api_key']}"})
        return data["choices"][0]["message"]["content"]
    if provider == "ollama":
        url = f"{cfg['base_url']}/api/generate"
        payload = {"model": cfg["model"], "prompt": prompt,
                   "stream": False, "options": {"temperature": 0.9}}
        headers = {}
        if cfg.get("api_key"):
            headers["Authorization"] = f"Bearer {cfg['api_key']}"
        data = http_json(url, method="POST", payload=payload, headers=headers)
        return data.get("response", "")
    raise ValueError(f"Provider '{provider}' không hỗ trợ")


def ai_predict(cfg, context):
    """Gọi AI dự đoán 2 dãy số. Trả về dict kết quả."""
    cfg = effective(cfg)
    prompt = build_prompt(context)
    try:
        text = _call_api(cfg, prompt)
        sets = _parse_sets(text)
        if sets:
            return {"ok": True, "sets": sets, "provider": cfg["provider"],
                    "model": cfg["model"], "raw": text[:500]}
        # thử lại 1 lần với prompt nghiêm khắc hơn
        retry_prompt = prompt + ("\n\nQUAN TRỌNG: Phản hồi trước không phải JSON hợp lệ. "
                                 "Trả về DUY NHẤT JSON đúng định dạng yêu cầu, "
                                 "số viết KHÔNG có số 0 ở đầu (vd 8 thay vì 08).")
        text2 = _call_api(cfg, retry_prompt)
        sets = _parse_sets(text2)
        if sets:
            return {"ok": True, "sets": sets, "provider": cfg["provider"],
                    "model": cfg["model"], "raw": text2[:500]}
        return {"ok": False, "message": "AI phản hồi không đúng định dạng JSON",
                "raw": (text + "\n---LẦN 2---\n" + text2)[:800]}
    except urllib.error.HTTPError as e:
        return {"ok": False, "message": f"Lỗi HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"ok": False, "message": f"Lỗi gọi AI: {e}"}