import sqlite3
conn = sqlite3.connect('tamgaflow.db')
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
print('Tables:', tables)
print('Count:', len(tables))
