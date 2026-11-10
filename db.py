import sqlite3
from flask import g

def get_connection():
    con = sqlite3.connect("database.db")
    con.execute("PRAGMA foreign_keys = ON")
    con.row_factory = sqlite3.Row
    return con

def ensure_songs_schema():
    con = get_connection()
    try:
        con.execute("""
            CREATE TABLE IF NOT EXISTS songs (
                id INTEGER PRIMARY KEY,
                title TEXT,
                artist TEXT,
                tab TEXT,
                user_id INTEGER REFERENCES users(id)
            )
        """)
        columns = {row["name"] for row in con.execute("PRAGMA table_info(songs)")}
        foreign_keys = con.execute("PRAGMA foreign_key_list(songs)").fetchall()
        if "user_id" not in columns or any(row["from"] == "tab" for row in foreign_keys):
            columns_to_copy = ["id", "title", "artist", "tab"]
            if "user_id" in columns:
                columns_to_copy.append("user_id")
            column_list = ", ".join(columns_to_copy)
            con.execute("PRAGMA foreign_keys = OFF")
            try:
                con.execute("BEGIN")
                con.execute("""
                    CREATE TABLE songs_new (
                        id INTEGER PRIMARY KEY,
                        title TEXT,
                        artist TEXT,
                        tab TEXT,
                        user_id INTEGER REFERENCES users(id)
                    )
                """)
                con.execute(
                    f"INSERT INTO songs_new ({column_list}) "
                    f"SELECT {column_list} FROM songs"
                )
                con.execute("DROP TABLE songs")
                con.execute("ALTER TABLE songs_new RENAME TO songs")
                con.commit()
            except sqlite3.Error:
                con.rollback()
                raise
            finally:
                con.execute("PRAGMA foreign_keys = ON")
    finally:
        con.close()

def execute(sql, params=[]):
    con = get_connection()
    try:
        result = con.execute(sql, params)
        con.commit()
        g.last_insert_id = result.lastrowid
    finally:
        con.close()

def last_insert_id():
    return g.last_insert_id    
    
def query(sql, params=[]):
    con = get_connection()
    result = con.execute(sql, params).fetchall()
    con.close()
    return result