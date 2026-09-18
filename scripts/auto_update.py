# -*- coding: utf-8 -*-
"""
auto_update.py - Tự cập nhật kết quả kỳ quay mới nhất vào database.

run_update():
  1. Thu thập dữ liệu thô từ 4 nguồn (fetch_data)
  2. Xây dựng lại database (build_db)
  3. So sánh kỳ mới nhất trước/sau -> phát hiện kỳ quay mới
"""
import os
import sqlite3
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
sys.path.insert(0, BASE)

import build_db  # noqa: E402
import fetch_data  # noqa: E402


def get_latest():
    conn = sqlite3.connect(build_db.DB_PATH)
    row = conn.execute("SELECT MAX(id), MAX(date) FROM draws").fetchone()
    conn.close()
    return {"id": row[0], "date": row[1]}


def run_update():
    """Fetch + build DB. Trả về dict kết quả chi tiết."""
    before = get_latest()
    try:
        fetch_data.main()
        build_db.main()
        after = get_latest()
        new_draw = None
        if after["id"] and after["id"] != before["id"]:
            conn = sqlite3.connect(build_db.DB_PATH)
            conn.row_factory = sqlite3.Row
            r = conn.execute(
                "SELECT draw_code, date, n1,n2,n3,n4,n5,n6, power FROM draws "
                "WHERE id=?", (after["id"],)).fetchone()
            conn.close()
            new_draw = {
                "draw_code": r["draw_code"], "date": r["date"],
                "numbers": [r["n1"], r["n2"], r["n3"], r["n4"], r["n5"], r["n6"]],
                "power": r["power"],
            }
        return {
            "ok": True,
            "before": before,
            "after": after,
            "new_draw": new_draw,
            "message": f"Có kỳ mới #{after['id']:05d} ({after['date']})" if new_draw
                       else "Không có kỳ quay mới (dữ liệu đã mới nhất)",
        }
    except Exception as e:
        return {"ok": False, "before": before, "after": get_latest(),
                "new_draw": None, "message": f"Lỗi cập nhật: {e}"}


if __name__ == "__main__":
    import json
    print(json.dumps(run_update(), ensure_ascii=False, indent=2))