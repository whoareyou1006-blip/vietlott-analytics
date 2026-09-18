# -*- coding: utf-8 -*-
"""verify_db.py - Xác minh dữ liệu trong database."""
import sqlite3
import os

DB = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "vietlott.db"))
conn = sqlite3.connect(DB)

print("=== Kỳ mới nhất ===")
for r in conn.execute("SELECT draw_code, date, n1,n2,n3,n4,n5,n6, power, jackpot1 FROM draws ORDER BY id DESC LIMIT 3"):
    print(" ", r)

print("\n=== Top 5 số về nhiều (all-time, tính từ dữ liệu kỳ quay) ===")
for r in conn.execute("SELECT number, count FROM frequency WHERE source='derived' AND scope='all_time' ORDER BY count DESC LIMIT 5"):
    print(" ", r)

print("\n=== Top 5 số gan nhất (ngày chưa về) ===")
for r in conn.execute("SELECT number, count FROM frequency WHERE source='derived' AND scope='gan_days' ORDER BY count DESC LIMIT 5"):
    print(" ", r)

print("\n=== Top 5 số về nhiều 30 kỳ gần nhất ===")
for r in conn.execute("SELECT number, count FROM frequency WHERE source='derived' AND scope='last_30' ORDER BY count DESC LIMIT 5"):
    print(" ", r)

print("\n=== Jackpot lớn nhất lịch sử ===")
for r in conn.execute("SELECT rank, jackpot, date FROM jackpot_history ORDER BY rank LIMIT 3"):
    print(" ", r)

print("\n=== Cặp số hay về cùng ===")
for r in conn.execute("SELECT pair, count FROM pairs ORDER BY count DESC LIMIT 5"):
    print(" ", r)

print("\n=== Nguồn dữ liệu ===")
for r in conn.execute("SELECT name, draws_count, notes FROM sources"):
    print(" ", r)

print("\n=== Thống kê tổng ===")
print("  Tổng kỳ:", conn.execute("SELECT COUNT(*) FROM draws").fetchone()[0])
print("  Kỳ có jackpot:", conn.execute("SELECT COUNT(*) FROM draws WHERE jackpot1 IS NOT NULL").fetchone()[0])
print("  Phạm vi:", conn.execute("SELECT MIN(date), MAX(date) FROM draws").fetchone())
conn.close()