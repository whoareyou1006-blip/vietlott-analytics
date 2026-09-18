# -*- coding: utf-8 -*-
import sqlite3
conn = sqlite3.connect(r"C:\Vietlot\data\vietlott.db")
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT id, date, n1,n2,n3,n4,n5,n6, power FROM draws ORDER BY id DESC LIMIT 3").fetchall()
for r in rows:
    print(f"Ky {r['id']:05d} ({r['date']}): {r['n1']:02d} {r['n2']:02d} {r['n3']:02d} {r['n4']:02d} {r['n5']:02d} {r['n6']:02d} + Power {r['power']:02d}")
conn.close()