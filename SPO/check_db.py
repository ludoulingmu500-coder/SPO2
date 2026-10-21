import sqlite3

conn = sqlite3.connect("database/blacklist.db")
cur = conn.cursor()

print("=== blacklist ===")

try:
    rows = cur.execute("SELECT * FROM blacklist").fetchall()

    if not rows:
        print("データなし")

    for row in rows:
        print(row)

except Exception as e:
    print(e)

print("\n=== whitelist ===")

try:
    rows = cur.execute("SELECT * FROM whitelist").fetchall()

    if not rows:
        print("データなし")

    for row in rows:
        print(row)

except Exception as e:
    print(e)

conn.close()