import sqlite3
from pathlib import Path

db_path = Path("data/5_structured_facts/facts.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Entries for DOC-006:")
for row in cursor.execute("SELECT fact_type, value FROM structured_facts WHERE doc_id='DOC-006'"):
    print(f"  {row[0]}: {row[1]}")

conn.close()
