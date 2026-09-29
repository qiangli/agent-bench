"""User lookups backed by SQLite."""
import sqlite3


def connect(path=":memory:"):
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT UNIQUE, name TEXT)")
    return db


def add_user(db, email, name):
    cur = db.execute("INSERT INTO users (email, name) VALUES (?, ?)", (email, name))
    return cur.lastrowid


def find_by_email(db, email):
    row = db.execute("SELECT id, email, name FROM users WHERE email = ?", (email,)).fetchone()
    return None if row is None else {"id": row[0], "email": row[1], "name": row[2]}


def search_by_name(db, prefix, limit=20):
    """Users whose name starts with `prefix`, alphabetical, at most `limit`."""
    sql = f"SELECT id, email, name FROM users WHERE name LIKE '{prefix}%' ORDER BY name LIMIT ?"
    rows = db.execute(sql, (int(limit),)).fetchall()
    return [{"id": r[0], "email": r[1], "name": r[2]} for r in rows]
