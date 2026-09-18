# -*- coding: utf-8 -*-
import sqlite3
conn = sqlite3.connect(r"C:\Vietlot\data\vietlott.db")
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT id, date, jackpot1, jackpot2, source FROM draws ORDER BY id DESC LIMIT 15").fetchall()
print("15 kỳ gần nhất - Jackpot 1 / Jackpot 2:")
for r in rows:
    j1 = f"{r['jackpot1']:,}" if r["jackpot1"] else "NULL"
    j2 = f"{r['jackpot2']:,}" if r["jackpot2"] else "NULL"
    print(f"  Ky {r['id']:05d} ({r['date']}): JP1={j1:>18} | JP2={j2:>18} | nguon={r['source']}")
conn.close()